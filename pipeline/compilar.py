"""
Módulo de Compilação Analítica e Geração de Parquet — Pipeline Eleições 2026.
Executa a query agregada sobre o SQLite, aplica os modelos estatísticos rigorosos
(Spiegelhalter 2005) e materializa o cache colunar Parquet de alta performance.

Pode ser executado diretamente via CLI:
    python -m pipeline.compilar
    python -m pipeline.compilar --forcar
"""

import os
import sys
import time
import gc
import sqlite3
import argparse
from pathlib import Path
import pandas as pd

# Garante suporte seguro a UTF-8 em consoles Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_pipeline_dir = Path(__file__).resolve().parent
_web_dir = _pipeline_dir.parent / "web"
for _p in (_pipeline_dir, _web_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pipeline.db import DB_PATH, get_connection
from estatistica import aplicar_motor_estatistico, aplicar_motor_abstencao

PARQUET_PATH = DB_PATH.with_suffix(".parquet")

MAPA_REGIOES = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul"
}

QUERY_ANALITICA = """
SELECT 
    s.pleito,
    coalesce(p.ano, 2026) AS ano,
    coalesce(p.turno, 1) AS turno,
    s.uf,
    s.municipio,
    coalesce(s.municipio_nome, s.municipio) AS municipio_nome,
    coalesce(s.municipio_nome, s.municipio) || ' (' || s.municipio || ')' AS municipio_display,
    s.zona,
    s.secao,
    s.total_aptos,
    s.comparecimento_bu,
    s.faltosos_bu,
    ROUND(s.faltosos_bu * 100.0 / NULLIF(s.total_aptos, 0), 2) AS pct_abstencao,
    ROUND(s.comparecimento_bu * 100.0 / NULLIF(s.total_aptos, 0), 2) AS pct_comparecimento,
    a.total_votos_log,
    a.votos_antes_17h,
    a.votos_apos_17h,
    a.pct_apos_17h,
    a.primeiro_voto,
    a.ultimo_voto,
    ROUND(CAST(substr(a.ultimo_voto, 1, 2) AS REAL) + CAST(substr(a.ultimo_voto, 4, 2) AS REAL)/60.0 + CAST(substr(a.ultimo_voto, 7, 2) AS REAL)/3600.0, 2) AS hora_ult_dec,
    a.hora_encerramento,
    a.maior_ociosidade_antes_17h_min,
    a.minutos_sem_voto_antes_17h,
    a.biometria_sucesso_total,
    a.habilitacao_manual_total,
    a.biometria_sucesso_pos17h,
    a.habilitacao_manual_pos17h,
    a.pct_manual_pos17h,
    a.tempo_medio_pos17h_segundos,
    a.votos_ultrarapidos_pos17h,
    a.score_suspeicao,
    a.motivos_alerta,
    r.pres_total_validos,
    r.pres_venc_num,
    r.pres_venc_votos,
    r.pres_venc_pct,
    r.pres_seg_num,
    r.pres_seg_votos,
    r.pres_seg_pct,
    r.votos_cand_13,
    r.votos_cand_22,
    r.gov_venc_num,
    r.gov_venc_votos,
    r.gov_venc_pct,
    z.pct_13_zona,
    z.pct_22_zona,
    ROUND(r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END), 1) AS delta_venc_zona,
    ROUND((r.votos_cand_13 * 100.0 / NULLIF(r.pres_total_validos, 0)) - z.pct_13_zona, 1) AS delta_13_zona,
    ROUND((r.votos_cand_22 * 100.0 / NULLIF(r.pres_total_validos, 0)) - z.pct_22_zona, 1) AS delta_22_zona,
    CASE 
        WHEN r.pres_venc_num = 13 THEN 'Lula (13) (' || printf('%.1f', r.pres_venc_pct) || '%)'
        WHEN r.pres_venc_num = 22 THEN 'Flávio Bolsonaro (22) (' || printf('%.1f', r.pres_venc_pct) || '%)'
        WHEN r.pres_venc_num IS NOT NULL THEN 'Nº ' || r.pres_venc_num || ' (' || printf('%.1f', r.pres_venc_pct) || '%)'
        ELSE '-'
    END AS vencedor_display,
    CASE 
        WHEN (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END)) > 0 
            THEN '+' || printf('%.1f', (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END))) || ' pp'
        WHEN (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END)) IS NOT NULL 
            THEN printf('%.1f', (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END))) || ' pp'
        ELSE '-'
    END AS delta_display
FROM auditoria_horarios a
JOIN secoes s ON s.id = a.secao_id
LEFT JOIN pleitos p ON p.codigo = s.pleito
LEFT JOIN resultados_eleicao r ON r.secao_id = s.id
LEFT JOIN zonas_totais z ON z.pleito = s.pleito AND z.uf = s.uf AND z.zona = s.zona
"""

def compilar_dataset_parquet(forcar: bool = False) -> pd.DataFrame:
    """Extrai do SQLite, processa estatísticas e salva o arquivo Parquet."""
    t0 = time.time()
    if not DB_PATH.exists():
        print(f"[!] Banco SQLite não encontrado em: {DB_PATH}")
        return pd.DataFrame()

    print("[*] Lendo dados analíticos do SQLite...")
    conn = get_connection(DB_PATH)
    df = pd.read_sql_query(QUERY_ANALITICA, conn)
    conn.close()

    print(f"[+] Total de seções carregadas do SQLite: {len(df):,}")
    print("[*] Aplicando motores estatísticos de Spiegelhalter (2005) e abstenção...")
    df = aplicar_motor_estatistico(df)
    df = aplicar_motor_abstencao(df)

    # Classificação por região
    df["regiao"] = df["uf"].map(MAPA_REGIOES).fillna("Outra").astype("category")
    df["uf"] = df["uf"].astype("category")
    df["pleito"] = df["pleito"].astype("category")

    # Downcasting de memória
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")

    print(f"[*] Escrevendo dataset colunar em: {PARQUET_PATH.name}...")
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARQUET_PATH, index=False, engine="pyarrow", compression="snappy")

    t_total = time.time() - t0
    tamanho_mb = round(PARQUET_PATH.stat().st_size / (1024 * 1024), 2)
    print(f"[+] Compilação concluída com sucesso em {round(t_total, 1)}s!")
    print(f"    Arquivo: {PARQUET_PATH} ({tamanho_mb} MB)")
    print(f"    Dimensões: {df.shape[0]:,} linhas x {df.shape[1]} colunas")

    gc.collect()
    return df

def main():
    parser = argparse.ArgumentParser(description="Compilador Parquet Analítico (pipeline.compilar)")
    parser.add_argument("--forcar", action="store_true", help="Força a recompilação mesmo se o Parquet for mais recente que o SQLite")
    args = parser.parse_args()

    compilar_dataset_parquet(forcar=args.forcar)

if __name__ == "__main__":
    main()
