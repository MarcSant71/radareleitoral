"""
Módulo de Carregamento e Processamento de Dados Analíticos — Eleições 2026.
Isola a extração do SQLite, aplicação dos motores estatísticos e persistência
do cache Parquet, sem acoplamento com a interface Streamlit.
"""

import gc
import sqlite3
from pathlib import Path
import pandas as pd
from dados.db import DB_PATH
from motores.estatistica import aplicar_motor_estatistico, aplicar_motor_abstencao

MAPA_REGIOES = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul"
}

PARQUET_CACHE_PATH = DB_PATH.with_suffix(".parquet")
PARQUET_LOCAIS_PATH = DB_PATH.parent / "locais_votacao.parquet"
PARQUET_SECOES_PATH = DB_PATH.parent / "locais_secoes.parquet"


def obter_locais_votacao() -> pd.DataFrame:
    """Carrega o catálogo nacional de locais de votação com geolocalização (~0.08s)."""
    if PARQUET_LOCAIS_PATH.exists():
        try:
            return pd.read_parquet(PARQUET_LOCAIS_PATH)
        except Exception:
            pass

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            df = pd.read_sql_query("SELECT * FROM locais_votacao", conn)
            conn.close()
            return df
        except Exception:
            conn.close()
    return pd.DataFrame()


def obter_secoes_mapeadas() -> pd.DataFrame:
    """Carrega o catálogo de seções mapeadas com seus critérios e apontamento ao local (~0.04s)."""
    if PARQUET_SECOES_PATH.exists():
        try:
            return pd.read_parquet(PARQUET_SECOES_PATH)
        except Exception:
            pass

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            df = pd.read_sql_query("SELECT * FROM locais_secoes", conn)
            conn.close()
            return df
        except Exception:
            conn.close()
    return pd.DataFrame()


def obter_dados_analiticos(forcar_reprocessamento: bool = False) -> pd.DataFrame:
    """
    Carrega o dataset analítico pré-calculado do Parquet (~0.5s)
    ou regera a partir do SQLite caso necessário.
    """
    # 1. Tenta carregar do Cache Colunar Parquet
    if PARQUET_CACHE_PATH.exists() and not forcar_reprocessamento:
        precisa_reprocessar = False
        if DB_PATH.exists() and DB_PATH.stat().st_mtime > PARQUET_CACHE_PATH.stat().st_mtime:
            precisa_reprocessar = True

        if not precisa_reprocessar:
            try:
                df = pd.read_parquet(PARQUET_CACHE_PATH)
                if "uf" in df.columns and df["uf"].dtype.name != "category":
                    df["uf"] = df["uf"].astype("category")
                if "regiao" in df.columns and df["regiao"].dtype.name != "category":
                    df["regiao"] = df["regiao"].astype("category")
                if "pleito" in df.columns and df["pleito"].dtype.name != "category":
                    df["pleito"] = df["pleito"].astype("category")
                return df
            except Exception:
                pass  # Fallback automático para o SQLite em caso de erro

    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    query = """
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
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Aplicação dos Motores Estatísticos Rigorosos (Spiegelhalter 2005)
    df = aplicar_motor_estatistico(df)
    df = aplicar_motor_abstencao(df)

    # Consolida coluna de região e converte categorias
    df["regiao"] = df["uf"].map(MAPA_REGIOES).fillna("Outra").astype("category")
    df["uf"] = df["uf"].astype("category")
    df["pleito"] = df["pleito"].astype("category")

    # Otimização de consumo de memória RAM (downcasting de inteiros/floats e categorias)
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")

    # Salva no cache colunar Parquet
    try:
        df.to_parquet(PARQUET_CACHE_PATH, index=False, engine="pyarrow", compression="snappy")
    except Exception:
        pass

    gc.collect()
    return df
