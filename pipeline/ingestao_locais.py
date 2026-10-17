"""
Módulo de Ingestão e Processamento dos Locais de Votação e Seções Mapeadas.
Baixa o catálogo nacional georreferenciado e consolida no SQLite e cache Parquet.
"""

import sys
import json
import time
import sqlite3
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "db" / "eleicoes2026.db"
PARQUET_LOCAIS_PATH = PROJECT_DIR / "db" / "locais_votacao.parquet"
PARQUET_SECOES_PATH = PROJECT_DIR / "db" / "locais_secoes.parquet"
INDICE_CACHE_PATH = PROJECT_DIR / "db" / "locais_indice.json"

BASE_URL = "https://brasil.arvor.co/assets/fiscais_mapa/"


def baixar_indice() -> dict:
    """Baixa o manifesto geral de metadados e critérios."""
    url = f"{BASE_URL}indice.json"
    req = urllib.request.Request(url, headers={"User-Agent": "RadarEleitoral/2.6.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    # Salva cache local do índice
    with open(INDICE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return data


def baixar_uf(uf: str) -> tuple[str, dict]:
    """Baixa o arquivo JSON de locais e seções de uma UF específica."""
    url = f"{BASE_URL}uf/{uf}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "RadarEleitoral/2.6.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return uf, data


def consolidar_locais_nacionais(max_workers: int = 8) -> tuple[int, int]:
    """
    Coordena o download paralelo dos 28 estados, normaliza as tabelas
    e grava no SQLite (eleicoes2026.db) e nos arquivos Parquet.
    """
    print("[*] 1/4 - Obtendo catálogo geral (indice.json)...")
    indice = baixar_indice()
    partes = indice.get("partes", {})
    ufs = list(partes.keys())
    print(f"    -> Encontradas {len(ufs)} Unidades da Federação no catálogo.")

    print(f"[*] 2/4 - Baixando dados das {len(ufs)} UFs em paralelo ({max_workers} threads)...")
    dados_ufs = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {executor.submit(baixar_uf, uf): uf for uf in ufs}
        for fut in as_completed(futuros):
            uf = futuros[fut]
            try:
                uf_code, uf_data = fut.result()
                dados_ufs[uf_code] = uf_data
                print(f"    [+] {uf_code}: {len(uf_data.get('locais', []))} locais, {len(uf_data.get('secoes', []))} seções.")
            except Exception as e:
                print(f"    [!] Erro ao baixar {uf}: {e}")

    print(f"    -> Concluído download de todas as UFs em {round(time.time() - t0, 2)}s.")

    print("[*] 3/4 - Normalizando dataframes relacionais...")
    colunas_locais = indice.get("colunas_locais", [
        "id", "uf", "mun", "municipio", "zona", "local", "endereco", "bairro",
        "cep", "lat", "lon", "coord_fonte", "risco", "risco_motivos", "secoes_total", "aptos_total"
    ])
    colunas_secoes = indice.get("colunas_secoes", [
        "li", "secao", "nivel", "pontuacao", "criterios", "explicacao", "aptos",
        "comparecimento", "flavio_pct", "lula_pct", "logs", "atencao", "tempo_voto",
        "processo_mediana", "cadencia_mediana"
    ])

    lista_locais = []
    lista_secoes = []

    for uf in ufs:
        uf_data = dados_ufs.get(uf)
        if not uf_data:
            continue
        
        locais_uf = uf_data.get("locais", [])
        secoes_uf = uf_data.get("secoes", [])

        # Processa locais da UF
        for loc in locais_uf:
            d_loc = dict(zip(colunas_locais, loc))
            # Serializa listas de motivos para armazenamento em banco/parquet
            if isinstance(d_loc.get("risco_motivos"), list):
                d_loc["risco_motivos"] = ", ".join(d_loc["risco_motivos"])
            lista_locais.append(d_loc)

        # Processa seções da UF associando ao ID do local pelo índice li
        for sec in secoes_uf:
            d_sec = dict(zip(colunas_secoes, sec))
            li = d_sec.pop("li", None)
            if li is not None and 0 <= li < len(locais_uf):
                local_ref = locais_uf[li]
                d_sec["local_id"] = local_ref[0]
                d_sec["uf"] = local_ref[1]
                d_sec["municipio_cod"] = local_ref[2]
                d_sec["municipio_nome"] = local_ref[3]
                d_sec["zona"] = local_ref[4]
            else:
                d_sec["local_id"] = None
                d_sec["uf"] = uf
                d_sec["municipio_cod"] = None
                d_sec["municipio_nome"] = None
                d_sec["zona"] = None

            if isinstance(d_sec.get("logs"), list):
                d_sec["logs"] = ", ".join(d_sec["logs"])
            lista_secoes.append(d_sec)

    df_locais = pd.DataFrame(lista_locais)
    df_secoes = pd.DataFrame(lista_secoes)

    # Tipagem e otimização de memória
    for c in ["uf", "risco"]:
        if c in df_locais.columns:
            df_locais[c] = df_locais[c].astype("category")

    for c in ["uf", "nivel"]:
        if c in df_secoes.columns:
            df_secoes[c] = df_secoes[c].astype("category")

    print(f"    -> Total consolidado: {len(df_locais):,} locais e {len(df_secoes):,} seções mapeadas.")

    print("[*] 4/4 - Gravando no SQLite e gerando arquivos Parquet...")
    # 1. Salva Parquet
    df_locais.to_parquet(PARQUET_LOCAIS_PATH, index=False, engine="pyarrow", compression="snappy")
    df_secoes.to_parquet(PARQUET_SECOES_PATH, index=False, engine="pyarrow", compression="snappy")
    print(f"    [+] Parquet Locais: {round(PARQUET_LOCAIS_PATH.stat().st_size / 1024 / 1024, 2)} MB")
    print(f"    [+] Parquet Seções: {round(PARQUET_SECOES_PATH.stat().st_size / 1024 / 1024, 2)} MB")

    # 2. Salva SQLite com índices analíticos
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS locais_votacao;")
    cur.execute("DROP TABLE IF EXISTS locais_secoes;")

    df_locais.to_sql("locais_votacao", conn, if_exists="replace", index=False)
    df_secoes.to_sql("locais_secoes", conn, if_exists="replace", index=False)

    # Criação de índices para pesquisas ultrarrápidas
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locais_uf ON locais_votacao(uf);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locais_mun ON locais_votacao(municipio);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locais_zona ON locais_votacao(zona);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locais_id ON locais_votacao(id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locais_secoes_local ON locais_secoes(local_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_locais_secoes_busca ON locais_secoes(uf, zona, secao);")

    conn.commit()
    conn.close()

    print("[+] Sincronização concluída com sucesso!")
    return len(df_locais), len(df_secoes)


if __name__ == "__main__":
    consolidar_locais_nacionais()
