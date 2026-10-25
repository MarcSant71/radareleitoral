"""
Pipeline de Geração e Otimização de Geometrias GeoJSON (Local-First).
Baixa as malhas vetoriais oficiais com simplificação web do IBGE (qualidade mínima),
armazena os dados brutos em dados_brutos/geodata/ e compila versões ultraleves
e enriquecidas com códigos TSE em db/geodata/.
"""

import os
import sys
import json
import gzip
import time
import unicodedata
import urllib.request
from pathlib import Path
from typing import Dict, Tuple, Optional
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_GEODATA_DIR = ROOT_DIR / "dados_brutos" / "geodata"
RAW_UFS_DIR = RAW_GEODATA_DIR / "raw_ufs"
DB_GEODATA_DIR = ROOT_DIR / "db" / "geodata"
DB_UFS_DIR = DB_GEODATA_DIR / "ufs"
PARQUET_PATH = ROOT_DIR / "db" / "eleicoes.parquet"

# Mapeamento oficial de Códigos IBGE (2 dígitos) para UFs
IBGE_UF = {
    '11': ('RO', 'Rondônia'),
    '12': ('AC', 'Acre'),
    '13': ('AM', 'Amazonas'),
    '14': ('RR', 'Roraima'),
    '15': ('PA', 'Pará'),
    '16': ('AP', 'Amapá'),
    '17': ('TO', 'Tocantins'),
    '21': ('MA', 'Maranhão'),
    '22': ('PI', 'Piauí'),
    '23': ('CE', 'Ceará'),
    '24': ('RN', 'Rio Grande do Norte'),
    '25': ('PB', 'Paraíba'),
    '26': ('PE', 'Pernambuco'),
    '27': ('AL', 'Alagoas'),
    '28': ('SE', 'Sergipe'),
    '29': ('BA', 'Bahia'),
    '31': ('MG', 'Minas Gerais'),
    '32': ('ES', 'Espírito Santo'),
    '33': ('RJ', 'Rio de Janeiro'),
    '35': ('SP', 'São Paulo'),
    '41': ('PR', 'Paraná'),
    '42': ('SC', 'Santa Catarina'),
    '43': ('RS', 'Rio Grande do Sul'),
    '50': ('MS', 'Mato Grosso do Sul'),
    '51': ('MT', 'Mato Grosso'),
    '52': ('GO', 'Goiás'),
    '53': ('DF', 'Distrito Federal')
}

# Aliases de compatibilização ortográfica entre grafia TSE e IBGE
ALIASES_TSE_IBGE = {
    ('GO', 'BOMJESUS'): 'BOMJESUSDEGOIAS',
    ('MG', 'BARAODEMONTEALTO'): 'BARAODOMONTEALTO',
    ('MG', 'DONAEUSEBIA'): 'DONAEUZEBIA',
    ('MG', 'SAOTHOMEDASLETRAS'): 'SAOTOMEDASLETRAS',
    ('MT', 'SANTOANTONIODOLERVERGER'): 'SANTOANTONIODELEVERGER',
    ('MT', 'SANTOANTONIODOLEVERGER'): 'SANTOANTONIODELEVERGER',
    ('PA', 'ELDORADODOSCARAJAS'): 'ELDORADODOCARAJAS',
    ('PR', 'MUNHOZDEMELLO'): 'MUNHOZDEMELO',
    ('RN', 'BOASAUDE'): 'JANUARIOCICCO',
    ('RO', 'ESPIGAODOOESTE'): 'ESPIGAODOESTE',
    ('RO', 'ALVORADADOOESTE'): 'ALVORADADOESTE',
    ('RR', 'SAOLUIZ'): 'SAOLUIZDOANAUA',
    ('SE', 'AMPARODESAOFRANCISCO'): 'AMPARODOSAOFRANCISCO',
    ('SP', 'SAOLUISDOPARAITINGA'): 'SAOLUIZDOPARAITINGA'
}

def normalizar_texto(txt: str) -> str:
    """Remove acentos, espaços e caracteres especiais para casamento de nomes."""
    if not txt:
        return ""
    n = unicodedata.normalize("NFKD", str(txt)).encode("ASCII", "ignore").decode("utf-8")
    return "".join(c for c in n.upper() if c.isalnum())

def fetch_json(url: str, timeout: int = 15) -> dict:
    """Executa requisição HTTP com suporte a descompressão GZIP transparente."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RadarEleitoral/2.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        return json.loads(raw.decode("utf-8"))

def gerar_estados():
    """Gera db/geodata/br_estados.json a partir do IBGE."""
    print("-> Baixando malha dos estados do Brasil (IBGE qualidade mínima)...")
    url = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF"
    data = fetch_json(url)

    raw_path = RAW_GEODATA_DIR / "raw_estados.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    for feat in data.get("features", []):
        code = feat.get("properties", {}).get("codarea")
        if code in IBGE_UF:
            sigla, nome = IBGE_UF[code]
            feat["id"] = sigla
            feat["properties"]["sigla"] = sigla
            feat["properties"]["nome"] = nome

    dest_path = DB_GEODATA_DIR / "br_estados.json"
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)

    size_kb = dest_path.stat().st_size / 1024
    print(f"   [OK] Estados gerados com sucesso: {dest_path.name} ({size_kb:.1f} KB)")

def carregar_municipios_tse() -> pd.DataFrame:
    """Lê os municípios e códigos TSE diretamente da base parquet compilada."""
    if not PARQUET_PATH.exists():
        raise FileNotFoundError(f"Base de eleições não encontrada em {PARQUET_PATH}")
    df = pd.read_parquet(PARQUET_PATH, columns=["uf", "municipio", "municipio_nome"])
    muns = df.groupby(["uf", "municipio", "municipio_nome"], observed=True).size().reset_index()
    muns = muns[muns["uf"] != "ZZ"] # Desconsidera exterior
    return muns

def gerar_municipios():
    """Gera arquivos GeoJSON municipais por UF em db/geodata/ufs/{UF}.json."""
    print("-> Carregando cadastro oficial de municípios do IBGE...")
    url_muns = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    ibge_muns = fetch_json(url_muns)

    raw_muns_path = RAW_GEODATA_DIR / "raw_municipios.json"
    with open(raw_muns_path, "w", encoding="utf-8") as f:
        json.dump(ibge_muns, f, ensure_ascii=False)

    # Mapeia (UF, norm_nome) -> ibge_id e nome_oficial
    ibge_to_info = {} # ibge_id -> (uf, nome_oficial)
    nome_to_ibge = {} # (uf, norm_nome) -> ibge_id
    for m in ibge_muns:
        ibge_id = str(m["id"])
        uf_cod = ibge_id[:2]
        if uf_cod in IBGE_UF:
            uf_sigla = IBGE_UF[uf_cod][0]
            nome = m["nome"]
            ibge_to_info[ibge_id] = (uf_sigla, nome)
            nome_to_ibge[(uf_sigla, normalizar_texto(nome))] = ibge_id

    # Lê municípios do TSE
    df_tse = carregar_municipios_tse()
    # Mapeia ibge_id -> (cod_tse, nome_tse)
    ibge_to_tse = {}
    for _, r in df_tse.iterrows():
        uf = str(r["uf"])
        cod_tse = str(r["municipio"])
        nome_tse = str(r["municipio_nome"])
        norm_tse = normalizar_texto(nome_tse)
        
        # Checa alias se necessário
        if (uf, norm_tse) in ALIASES_TSE_IBGE:
            norm_tse = ALIASES_TSE_IBGE[(uf, norm_tse)]

        ibge_id = nome_to_ibge.get((uf, norm_tse))
        if ibge_id:
            ibge_to_tse[ibge_id] = (cod_tse, nome_tse)

    print(f"   [OK] {len(ibge_to_tse)} municípios TSE vinculados ao IBGE com sucesso.")

    # Baixa e processa a malha de cada UF
    ufs_ordenadas = sorted([v[0] for v in IBGE_UF.values()])
    t0_all = time.time()
    
    for uf in ufs_ordenadas:
        url_uf = f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
        try:
            geo_uf = fetch_json(url_uf)
        except Exception as e:
            print(f"   [ERRO] Falha ao baixar malha da UF {uf}: {e}")
            continue

        raw_uf_path = RAW_UFS_DIR / f"{uf}.json"
        with open(raw_uf_path, "w", encoding="utf-8") as f:
            json.dump(geo_uf, f, ensure_ascii=False)

        # Enriquece cada polígono municipal com o código TSE
        for feat in geo_uf.get("features", []):
            ibge_id = feat.get("properties", {}).get("codarea")
            if ibge_id in ibge_to_tse:
                cod_tse, nome_tse = ibge_to_tse[ibge_id]
                feat["id"] = cod_tse
                feat["properties"]["cod_tse"] = cod_tse
                feat["properties"]["nome"] = nome_tse
                feat["properties"]["uf"] = uf
                feat["properties"]["ibge_id"] = ibge_id
            else:
                # Fallback caso não mapeado
                feat["id"] = ibge_id
                feat["properties"]["cod_tse"] = ibge_id
                feat["properties"]["uf"] = uf

        dest_uf_path = DB_UFS_DIR / f"{uf}.json"
        with open(dest_uf_path, "w", encoding="utf-8") as f:
            json.dump(geo_uf, f, separators=(",", ":"), ensure_ascii=False)

        size_kb = dest_uf_path.stat().st_size / 1024
        print(f"   UF {uf:2s}: {len(geo_uf.get('features', [])):3d} municípios -> {dest_uf_path.name} ({size_kb:.1f} KB)")

    print(f"\n[SUCESSO] Processamento geoespacial concluído em {time.time()-t0_all:.1f}s.")

def main():
    RAW_GEODATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_UFS_DIR.mkdir(parents=True, exist_ok=True)
    DB_GEODATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_UFS_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("GERAÇÃO DE DADOS GEOESPACIAIS LOCAL-FIRST (IBGE)")
    print("==================================================")
    gerar_estados()
    gerar_municipios()
    print("==================================================")

if __name__ == "__main__":
    main()
