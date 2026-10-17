"""
Script Principal de Auditoria Eleitoral 2026.
Permite auditar uma UF inteira ou municípios/zonas específicas com processamento paralelo,
armazenando os resultados no SQLite e exibindo o ranking das seções mais suspeitas.
"""

import sys
import argparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional

_root_dir = Path(__file__).resolve().parent.parent
_pipeline_dir = _root_dir / "pipeline"
for _p in (_root_dir, _pipeline_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pipeline.db import init_db, get_connection
from pipeline.downloader import RemoteZipRangeReader, CDN_BASE_URL
from pipeline.log_parser import UrnaLogParser

# Expressão regular para decodificar nome do arquivo de log do TSE:
# Ex: o03220ba3911000460366-log.jez -> pleito: 03220, uf: ba, mu: 39110, zn: 0046, se: 0366
LOG_NAME_REGEX = re.compile(r"^o(\d{5})([a-z]{2})(\d{5})(\d{4})(\d{4})-log\.jez$")

def extrair_metadados_nome(filename: str) -> Optional[Dict[str, str]]:
    m = LOG_NAME_REGEX.match(filename)
    if not m:
        return None
    return {
        "pleito": m.group(1),
        "uf": m.group(2).upper(),
        "municipio": m.group(3),
        "zona": m.group(4),
        "secao": m.group(5)
    }

def processar_log_remoto(reader: RemoteZipRangeReader, filename: str, parser: UrnaLogParser) -> Optional[Dict[str, Any]]:
    try:
        raw_bytes = reader.read_file(filename)
        metricas = parser.parse_from_jez(raw_bytes)
        meta = extrair_metadados_nome(filename)
        if not meta:
            return None
        return {
            "meta": meta,
            "metricas": metricas
        }
    except Exception as e:
        # print(f"Erro ao processar {filename}: {e}", file=sys.stderr)
        return None

# Carrega catálogo oficial de nomes de municípios do TSE
MAPA_MUNICIPIOS = {}
project_root = Path(__file__).resolve().parent.parent
csv_candidatos = [
    project_root / "dados_brutos" / "municipios" / "municipio_tse_ibge.csv",
    project_root / "municipios" / "municipio_tse_ibge.csv",
    Path(__file__).resolve().parent / "municipios" / "municipio_tse_ibge.csv",
    Path("dados_brutos/municipios/municipio_tse_ibge.csv"),
    Path("municipios/municipio_tse_ibge.csv")
]
csv_mun = next((p for p in csv_candidatos if p.exists()), None)
if csv_mun:
    try:
        import csv
        with open(csv_mun, mode='r', encoding='latin1') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                cd = str(row.get('CD_MUNICIPIO_TSE', '')).zfill(5)
                nm = str(row.get('NM_MUNICIPIO_TSE', '')).strip().title()
                if cd and nm:
                    MAPA_MUNICIPIOS[cd] = nm
    except Exception:
        pass

def salvar_em_lote(resultados: List[Dict[str, Any]]) -> None:
    if not resultados:
        return
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        for res in resultados:
            meta = res["meta"]
            met = res["metricas"]
            mu_nome = MAPA_MUNICIPIOS.get(meta["municipio"], None)
            
            # 1. Registra ou atualiza seção com nome real do município
            cur.execute("""
                INSERT INTO secoes (pleito, uf, municipio, municipio_nome, zona, secao)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(pleito, uf, municipio, zona, secao) DO UPDATE SET 
                    municipio_nome = coalesce(excluded.municipio_nome, secoes.municipio_nome)
                RETURNING id;
            """, (meta["pleito"], meta["uf"], meta["municipio"], mu_nome, meta["zona"], meta["secao"]))
            secao_id = cur.fetchone()[0]

            # 2. Registra auditoria
            cur.execute("""
                INSERT OR REPLACE INTO auditoria_horarios (
                    secao_id, total_votos_log, primeiro_voto, ultimo_voto, hora_encerramento,
                    votos_antes_17h, votos_apos_17h, pct_apos_17h,
                    maior_ociosidade_antes_17h_min, minutos_sem_voto_antes_17h,
                    biometria_sucesso_total, habilitacao_manual_total,
                    biometria_sucesso_pos17h, habilitacao_manual_pos17h, pct_manual_pos17h,
                    tempo_medio_pos17h_segundos, votos_ultrarapidos_pos17h,
                    score_suspeicao, motivos_alerta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                secao_id,
                met.get("total_votos", 0),
                met.get("primeiro_voto"),
                met.get("ultimo_voto"),
                met.get("hora_encerramento"),
                met.get("votos_antes_17h", 0),
                met.get("votos_apos_17h", 0),
                met.get("pct_apos_17h", 0.0),
                met.get("maior_gap_antes_17h_min", 0.0),
                met.get("minutos_sem_voto_ate_17h", 0.0),
                met.get("biometria_sucesso_total", 0),
                met.get("habilitacao_manual_total", 0),
                met.get("biometria_sucesso_pos17h", 0),
                met.get("habilitacao_manual_pos17h", 0),
                met.get("pct_manual_pos17h", 0.0),
                met.get("tempo_medio_pos17h_segundos", 0.0),
                met.get("votos_ultrarapidos_pos17h", 0),
                met.get("score_suspeicao", 0.0),
                met.get("motivos_alerta", "Padrão normal")
            ))
    conn.close()

def salvar_no_banco(resultado: Dict[str, Any]) -> None:
    salvar_em_lote([resultado])

def exibir_ranking(limit: int = 15, uf: Optional[str] = None) -> None:
    conn = get_connection()
    cur = conn.cursor()
    
    query = """
    SELECT 
        s.uf, coalesce(s.municipio_nome, s.municipio) AS municipio_nome, s.zona, s.secao,
        a.total_votos_log, a.votos_apos_17h, a.pct_apos_17h,
        a.primeiro_voto, a.ultimo_voto, a.hora_encerramento,
        a.pct_manual_pos17h, a.score_suspeicao, a.motivos_alerta
    FROM auditoria_horarios a
    JOIN secoes s ON s.id = a.secao_id
    """
    params = []
    if uf:
        query += " WHERE s.uf = ? "
        params.append(uf.upper())
    
    query += " ORDER BY a.score_suspeicao DESC, a.votos_apos_17h DESC LIMIT ?;"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("\nNenhuma seção auditada encontrada no banco de dados.")
        return

    print("="*120)
    print(f"RANKING DAS SEÇÕES MAIS SUSPEITAS (TOP {len(rows)})")
    print("="*120)
    print(f"{'UF':<3} {'MUNICÍPIO':<22} {'ZONA':<5} {'SEÇÃO':<6} {'VOTOS':<6} {'PÓS-17H':<8} {'% PÓS':<7} {'ÚLTIMO VOTO':<12} {'% MANUAL':<9} {'SCORE':<6} {'MOTIVOS'}")
    print("-"*120)
    for r in rows:
        mun_str = (r['municipio_nome'][:20] + '..') if len(r['municipio_nome']) > 22 else r['municipio_nome']
        print(f"{r['uf']:<3} {mun_str:<22} {r['zona']:<5} {r['secao']:<6} {r['total_votos_log']:<6} "
              f"{r['votos_apos_17h']:<8} {r['pct_apos_17h']:<6.1f}% {r['ultimo_voto']:<12} "
              f"{r['pct_manual_pos17h']:<8.1f}% {r['score_suspeicao']:<6.1f} {r['motivos_alerta']}")
    print("="*120)

def executar_auditoria(uf: str = "BA", municipio: Optional[str] = None, limite: int = 50, threads: int = 8) -> None:
    init_db()
    zip_url = f"{CDN_BASE_URL}/bu_imgbu_logjez_rdv_vscmr_2026_1t_{uf.upper()}.zip"
    print(f"\n[1/3] Conectando ao pacote da CDN para {uf.upper()}...")
    reader = RemoteZipRangeReader(zip_url)
    reader.connect()

    todos_logs = [f for f in reader.entries.keys() if f.endswith("-log.jez")]
    print(f"[2/3] Total de logs encontrados no índice da UF {uf.upper()}: {len(todos_logs)}")

    # Filtra por município se especificado
    if municipio:
        mu_pad = str(municipio).zfill(5)
        todos_logs = [f for f in todos_logs if f"m{mu_pad}" in f or f"{mu_pad}" in f]
        print(f" -> Filtrado para o município {municipio}: {len(todos_logs)} seções")

    alvo_logs = todos_logs[:limite]
    print(f"[3/3] Iniciando auditoria em {len(alvo_logs)} seções usando {threads} threads paralelas...")

    parser = UrnaLogParser()
    processados = 0

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(processar_log_remoto, reader, log_f, parser): log_f for log_f in alvo_logs}
        for fut in as_completed(futures):
            res = fut.result()
            processados += 1
            if res:
                salvar_no_banco(res)
            pct = (processados / len(alvo_logs)) * 100.0
            sys.stdout.write(f"\rAuditando {uf}: {pct:5.1f}% ({processados:,}/{len(alvo_logs):,} seções)...                 ")
            sys.stdout.flush()

    sys.stdout.write(f"\rAuditando {uf}: 100.0% - Concluído! ({len(alvo_logs):,} seções)                                   \n")
    sys.stdout.flush()
    exibir_ranking(limit=15, uf=uf)

def executar_auditoria_local_zip(caminho_zip: Path, municipio: Optional[str] = None, limite: Optional[int] = None, threads: int = 8, exibir_ranking_final: bool = False) -> None:
    import zipfile
    init_db()
    caminho = Path(caminho_zip)
    if not caminho.exists():
        print(f"Erro: Arquivo local {caminho} não encontrado.", file=sys.stderr)
        return

    z = zipfile.ZipFile(caminho, 'r')
    todos_logs = [f for f in z.namelist() if f.endswith("-log.jez")]

    if municipio:
        mu_pad = str(municipio).zfill(5)
        todos_logs = [f for f in todos_logs if f"m{mu_pad}" in f or f"{mu_pad}" in f]

    alvo_logs = todos_logs[:limite] if limite else todos_logs

    # Detecção de seções já auditadas para evitar reprocessamento (resume inteligente)
    uf_m = re.search(r"_([A-Z]{2})\.zip$", caminho.name)
    uf_zip = uf_m.group(1) if uf_m else "UF"
    if uf_zip:
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT municipio, zona, secao FROM secoes JOIN auditoria_horarios ON secoes.id = auditoria_horarios.secao_id WHERE uf = ?", (uf_zip,))
            secoes_ja_auditadas = { (r[0], r[1], r[2]) for r in cur.fetchall() }
            conn.close()

            if secoes_ja_auditadas:
                logs_pendentes = []
                for log_f in alvo_logs:
                    meta = extrair_metadados_nome(log_f)
                    if meta and (meta["municipio"], meta["zona"], meta["secao"]) in secoes_ja_auditadas:
                        continue
                    logs_pendentes.append(log_f)
                alvo_logs = logs_pendentes
        except Exception:
            pass

    if not alvo_logs:
        sys.stdout.write(f"\rAuditando {uf_zip}: 100.0% - Concluído! (Arquivo já processado)                          \n")
        sys.stdout.flush()
        z.close()
        return


    # Parser com fuso horário da UF atual
    parser = UrnaLogParser(uf=uf_zip)

    def processar_mem_item(item):
        nome_log, raw_bytes = item
        try:
            meta = extrair_metadados_nome(nome_log)
            if not meta:
                return None
            metricas = parser.parse_from_jez(raw_bytes)
            return {"meta": meta, "metricas": metricas}
        except Exception:
            return None

    processados = 0
    CHUNK_SIZE = 1000

    import time
    t_inicio = time.time()
    sys.stdout.write(f"\rAuditando {uf_zip}:   0.0% | 0 seções/s...                 ")
    sys.stdout.flush()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for chunk_start in range(0, len(alvo_logs), CHUNK_SIZE):
            chunk_names = alvo_logs[chunk_start:chunk_start + CHUNK_SIZE]
            
            # 1. Leitura ultrarrápida sequencial sem disputa de lock de arquivo
            items = []
            for name in chunk_names:
                try:
                    items.append((name, z.read(name)))
                except Exception:
                    pass

            # 2. Parse paralelo das seções na memória com as threads configuradas
            resultados = list(executor.map(processar_mem_item, items))

            # 3. Gravação em lote atômica no SQLite WAL
            validos = [res for res in resultados if res]
            if validos:
                salvar_em_lote(validos)

            processados += len(chunk_names)
            tempo_decorrido = max(0.1, time.time() - t_inicio)
            taxa = processados / tempo_decorrido
            pct = (processados / len(alvo_logs)) * 100.0
            sys.stdout.write(f"\rAuditando {uf_zip}: {pct:5.1f}% | {taxa:.0f} seções/s...                 ")
            sys.stdout.flush()

    z.close()
    sys.stdout.write(f"\rAuditando {uf_zip}: 100.0% - Concluído! ({len(todos_logs):,} seções)                                   \n")
    sys.stdout.flush()
    if exibir_ranking_final:
        exibir_ranking(limit=25)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditor de Urnas Eleitorais 2026")
    parser.add_argument("--uf", default="BA", help="Estado (UF) para auditar via CDN, ex: BA, SP, RJ")
    parser.add_argument("--zip", default=None, help="Caminho de um arquivo ZIP já baixado localmente no storage")
    parser.add_argument("--municipio", default=None, help="Código do município específico (opcional)")
    parser.add_argument("--dir", default=None, help="Diretório contendo múltiplos arquivos ZIP de diferentes estados")
    parser.add_argument("--limite", type=int, default=None, help="Quantidade de seções por estado (ou None para todas)")
    parser.add_argument("--threads", type=int, default=8, help="Número de threads simultâneas")
    parser.add_argument("--ranking", action="store_true", help="Exibe apenas o ranking atual do banco SQLite")

    args = parser.parse_args()

    def obter_diretorio_dados_local() -> Optional[Path]:
        import os
        env_dir = os.environ.get("DADOS_DIR")
        if env_dir and Path(env_dir).exists():
            return Path(env_dir).resolve()
        project_root = Path(__file__).resolve().parent.parent
        candidatos = [
            project_root / "dados_brutos" / "arquivos_urna",
            project_root / "dados_brutos",
            Path("dados_brutos/arquivos_urna"),
            Path("dados_brutos"),
            Path("./dados")
        ]
        for c in candidatos:
            if c.exists() and list(c.glob("*.zip")):
                return c.resolve()
        return None

    dir_alvo = args.dir or (obter_diretorio_dados_local() if not args.zip and not args.ranking else None)

    if args.ranking:
        exibir_ranking(limit=30, uf=args.uf if not (args.zip or dir_alvo) else None)
    elif dir_alvo:
        diretorio = Path(dir_alvo)
        zips = sorted(list(diretorio.glob("*.zip")))
        if not zips:
            print(f"Nenhum arquivo .zip encontrado em: {diretorio}", file=sys.stderr)
            sys.exit(1)
        print(f"Encontrados {len(zips)} pacotes de estado em: {diretorio}")
        for i, z_path in enumerate(zips, 1):
            print(f"\n==================== [{i}/{len(zips)}] {z_path.name} ====================")
            executar_auditoria_local_zip(z_path, municipio=args.municipio, limite=args.limite, threads=args.threads)
    elif args.zip:
        executar_auditoria_local_zip(Path(args.zip), municipio=args.municipio, limite=args.limite, threads=args.threads, exibir_ranking_final=True)
    else:
        executar_auditoria(uf=args.uf, municipio=args.municipio, limite=args.limite or 50, threads=args.threads)


