"""
Consolidador de Resultados de Boletins de Urna (BU) - Eleições 2026.
Lê os arquivos oficiais -bu.dat dos pacotes ZIP de dados brutos do TSE,
extrai a votação por candidato/partido e popula a tabela resultados_eleicao no SQLite.
"""

import os
import sys
import re
import time
import zipfile
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
_root_dir = Path(__file__).resolve().parent.parent
_pipeline_dir = _root_dir / "pipeline"
for _p in (_root_dir, _pipeline_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pipeline.db import get_connection, init_db
from pipeline.bu_parser import UrnaBuParser

BU_NAME_REGEX = re.compile(r"^o(\d{5})([a-z]{2})(\d{5})(\d{4})(\d{4})-bu\.dat$")

def extrair_meta_bu(filename: str) -> Optional[Dict[str, str]]:
    m = BU_NAME_REGEX.match(filename)
    if not m:
        return None
    return {
        "pleito": m.group(1),
        "uf": m.group(2).upper(),
        "municipio": m.group(3),
        "zona": m.group(4),
        "secao": m.group(5)
    }

def processar_pacote_uf(zip_path: Path, secoes_map: Dict[Tuple[str, str, str, str, str], int], processados: set, num_threads: int = 16):
    uf = zip_path.stem.split("_")[-1]
    t0 = time.time()
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        all_bu_files = [n for n in z.namelist() if n.endswith('-bu.dat')]
        total_bu = len(all_bu_files)
        
        # Filtra apenas seções pendentes
        arquivos_pendentes = []
        for f in all_bu_files:
            meta = extrair_meta_bu(f)
            if not meta:
                continue
            chave = (meta["pleito"], meta["uf"], meta["municipio"], meta["zona"], meta["secao"])
            secao_id = secoes_map.get(chave)
            if secao_id and secao_id not in processados:
                arquivos_pendentes.append((f, secao_id))
                
        if not arquivos_pendentes:
            sys.stdout.write(f"\rConsolidando {uf}: 100.0% - Concluído! (Arquivo já processado)                          \n")
            sys.stdout.flush()
            return 0
            
        sys.stdout.write(f"\rConsolidando {uf}:   0.0% | 0 BUs/s...                 ")
        sys.stdout.flush()

        # Processamento em lotes sequenciais de leitura (I/O) + paralelismo de parse (CPU)
        TAMANHO_LOTE = 2000
        lote_buffer = []
        processados_count = 0
        
        conn = get_connection()
        cur = conn.cursor()
        
        for i in range(0, len(arquivos_pendentes), TAMANHO_LOTE):
            chunk = arquivos_pendentes[i:i + TAMANHO_LOTE]
            
            # Leitura sequencial ultrarrápida do ZIP
            read_items = []
            for fname, s_id in chunk:
                try:
                    raw = z.read(fname)
                    read_items.append((s_id, raw))
                except Exception:
                    pass
                    
            # Parse paralelo em memória
            def _parse_worker(item):
                s_id, raw = item
                res = UrnaBuParser.parse(raw)
                return (s_id, res)
                
            resultados_chunk = []
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                for s_id, res in executor.map(_parse_worker, read_items):
                    p = res.get("presidente") or {}
                    g = res.get("governador") or {}
                    votos_cand = p.get("votos") or {}
                    
                    resultados_chunk.append((
                        s_id,
                        p.get("total_validos", 0),
                        p.get("brancos", 0),
                        p.get("nulos", 0),
                        p.get("vencedor_num"),
                        p.get("vencedor_votos", 0),
                        p.get("vencedor_pct", 0.0),
                        p.get("segundo_num"),
                        p.get("segundo_votos", 0),
                        p.get("segundo_pct", 0.0),
                        votos_cand.get(13, 0),
                        votos_cand.get(22, 0),
                        g.get("vencedor_num"),
                        g.get("vencedor_votos", 0),
                        g.get("vencedor_pct", 0.0)
                    ))
                    
            # Gravação em lote atômica no SQLite WAL
            with conn:
                cur.executemany("""
                    INSERT OR REPLACE INTO resultados_eleicao (
                        secao_id, pres_total_validos, pres_brancos, pres_nulos,
                        pres_venc_num, pres_venc_votos, pres_venc_pct,
                        pres_seg_num, pres_seg_votos, pres_seg_pct,
                        votos_cand_13, votos_cand_22,
                        gov_venc_num, gov_venc_votos, gov_venc_pct
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, resultados_chunk)
                
            processados_count += len(resultados_chunk)
            taxa = processados_count / max(0.1, time.time() - t0)
            pct = (processados_count / len(arquivos_pendentes)) * 100.0
            sys.stdout.write(f"\rConsolidando {uf}: {pct:5.1f}% | {taxa:.0f} BUs/s...                 ")
            sys.stdout.flush()
            
        conn.close()
        sys.stdout.write(f"\rConsolidando {uf}: 100.0% - Concluído! ({total_bu:,} BUs)                                   \n")
        sys.stdout.flush()
        return processados_count

def main():
    parser = argparse.ArgumentParser(description="Consolidador de Boletins de Urna (BU) - Eleições 2026")
    parser.add_argument("--uf", default=None, help="Processa apenas uma UF específica (ex: BA, AC, SP)")
    parser.add_argument("--threads", type=int, default=16, help="Número de threads simultâneas de parsing")
    default_dir = os.environ.get("DADOS_DIR", "dados_brutos")
    parser.add_argument("--dir", default=default_dir, help=f"Pasta com os pacotes ZIP brutos (padrão: {default_dir})")
    args = parser.parse_args()
    
    init_db()
    
    dados_dir = Path(args.dir)
    if not dados_dir.exists():
        print(f"ERRO: Diretório '{dados_dir}' não encontrado!", file=sys.stderr)
        print("Dica: Especifique o caminho dos pacotes ZIP com --dir <caminho> ou configure a variável DADOS_DIR.", file=sys.stderr)
        sys.exit(1)
        
    print("=" * 80)
    print("       CONSOLIDADOR NACIONAL DE BOLETINS DE URNA (BU) - ELEIÇÕES 2026")
    print("=" * 80)
    print(f"Diretório de pacotes: {dados_dir}")
    print("Carregando mapa de seções do banco SQLite...")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, pleito, uf, municipio, zona, secao FROM secoes")
    secoes_map = {}
    for row in cur.fetchall():
        s_id, pleito, uf, mu, zn, se = row
        secoes_map[(pleito, uf, mu, zn, se)] = s_id
    print(f"Seções cadastradas no banco: {len(secoes_map):,}")
    
    cur.execute("SELECT secao_id FROM resultados_eleicao")
    processados = {row[0] for row in cur.fetchall()}
    print(f"Seções já com resultados consolidados: {len(processados):,}")
    conn.close()
    
    # Lista arquivos ZIP
    if args.uf:
        zip_files = list(dados_dir.glob(f"*_{args.uf.upper()}.zip"))
    else:
        zip_files = sorted(list(dados_dir.glob("*.zip")))
        
    if not zip_files:
        print(f"Nenhum arquivo ZIP encontrado em {dados_dir}")
        sys.exit(1)
        
    print(f"Total de pacotes para auditar: {len(zip_files)}")
    print("=" * 80)
    
    total_geral = 0
    t_inicio = time.time()
    
    for zpath in zip_files:
        n = processar_pacote_uf(zpath, secoes_map, processados, num_threads=args.threads)
        total_geral += n
        
    duracao = time.time() - t_inicio
    print("\n" + "=" * 80)
    print(f"CONSOLIDAÇÃO DE RESULTADOS CONCLUÍDA!")
    print(f"Total de seções processadas nesta execução: {total_geral:,}")
    print(f"Tempo total: {duracao/60:.1f} minutos ({duracao:.1f}s)")
    print("Atualizando tabela agregada de zonas eleitorais (zonas_totais)...")
    atualizar_zonas_totais()
    print("=" * 80)

def atualizar_zonas_totais(conn=None):
    close_at_end = False
    if conn is None:
        conn = get_connection()
        close_at_end = True
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zonas_totais (
            pleito TEXT NOT NULL DEFAULT '03220',
            uf TEXT NOT NULL,
            zona TEXT NOT NULL,
            tot_validos INTEGER DEFAULT 0,
            tot_13 INTEGER DEFAULT 0,
            tot_22 INTEGER DEFAULT 0,
            tot_brancos INTEGER DEFAULT 0,
            tot_nulos INTEGER DEFAULT 0,
            pct_13_zona REAL DEFAULT 0.0,
            pct_22_zona REAL DEFAULT 0.0,
            pct_brancos_zona REAL DEFAULT 0.0,
            pct_nulos_zona REAL DEFAULT 0.0,
            PRIMARY KEY (pleito, uf, zona)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_secoes_uf_zona ON secoes(uf, zona)")
    cur.execute("""
        INSERT OR REPLACE INTO zonas_totais
        SELECT 
            s.pleito,
            s.uf,
            s.zona,
            SUM(r.pres_total_validos) AS tot_validos,
            SUM(r.votos_cand_13) AS tot_13,
            SUM(r.votos_cand_22) AS tot_22,
            SUM(r.pres_brancos) AS tot_brancos,
            SUM(r.pres_nulos) AS tot_nulos,
            ROUND(SUM(r.votos_cand_13) * 100.0 / NULLIF(SUM(r.pres_total_validos), 0), 2) AS pct_13_zona,
            ROUND(SUM(r.votos_cand_22) * 100.0 / NULLIF(SUM(r.pres_total_validos), 0), 2) AS pct_22_zona,
            ROUND(SUM(r.pres_brancos) * 100.0 / NULLIF(SUM(r.pres_total_validos) + SUM(r.pres_brancos) + SUM(r.pres_nulos), 0), 2) AS pct_brancos_zona,
            ROUND(SUM(r.pres_nulos) * 100.0 / NULLIF(SUM(r.pres_total_validos) + SUM(r.pres_brancos) + SUM(r.pres_nulos), 0), 2) AS pct_nulos_zona
        FROM secoes s
        JOIN resultados_eleicao r ON r.secao_id = s.id
        GROUP BY s.pleito, s.uf, s.zona
    """)
    conn.commit()
    print("Tabela 'zonas_totais' atualizada com sucesso!")
    if close_at_end:
        conn.close()

if __name__ == "__main__":
    main()
