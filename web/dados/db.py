"""
Módulo de Banco de Dados SQLite para Auditoria das Eleições 2026.
Projetado para suportar consultas rápidas de anomalias e fácil exportação para MySQL/Postgres.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List

def get_db_path() -> Path:
    """
    Localiza o banco SQLite de forma estrita e determinística.
    Prioridade:
    1. Variável de ambiente DATABASE_PATH (se informada)
    2. Pasta db/ relativa à raiz do projeto (db/eleicoes2026.db)
    """
    env_path = os.environ.get("DATABASE_PATH")
    if env_path:
        return Path(env_path).resolve()

    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "db").exists() or (parent / "README.md").exists():
            return (parent / "db" / "eleicoes2026.db").resolve()

    return (p.parents[2] / "db" / "eleicoes2026.db").resolve()

DB_PATH = get_db_path()

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    # Ativa WAL mode e timeout de contenção para performance máxima e zero locks
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS pleitos (
            codigo TEXT PRIMARY KEY,
            ano INTEGER NOT NULL,
            turno INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            data_votacao TEXT
        );

        INSERT OR IGNORE INTO pleitos (codigo, ano, turno, descricao, data_votacao)
        VALUES ('03220', 2026, 1, 'Eleições Gerais 2026 - 1º Turno', '2026-10-04');

        CREATE TABLE IF NOT EXISTS secoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pleito TEXT NOT NULL DEFAULT '03220',
            uf TEXT NOT NULL,
            municipio TEXT NOT NULL,
            municipio_nome TEXT,
            zona TEXT NOT NULL,
            secao TEXT NOT NULL,
            local TEXT,
            total_aptos INTEGER DEFAULT 0,
            comparecimento_bu INTEGER DEFAULT 0,
            faltosos_bu INTEGER DEFAULT 0,
            hash_urna TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pleito, uf, municipio, zona, secao),
            FOREIGN KEY(pleito) REFERENCES pleitos(codigo)
        );

        CREATE TABLE IF NOT EXISTS auditoria_horarios (
            secao_id INTEGER PRIMARY KEY,
            total_votos_log INTEGER NOT NULL,
            primeiro_voto TEXT,
            ultimo_voto TEXT,
            hora_encerramento TEXT,
            
            -- Métricas de votos pós-17h
            votos_antes_17h INTEGER DEFAULT 0,
            votos_apos_17h INTEGER DEFAULT 0,
            pct_apos_17h REAL DEFAULT 0.0,
            
            -- Ociosidade (em minutos) antes das 17h
            maior_ociosidade_antes_17h_min REAL DEFAULT 0.0,
            minutos_sem_voto_antes_17h REAL DEFAULT 0.0,
            
            -- Biometria geral e pós-17h
            biometria_sucesso_total INTEGER DEFAULT 0,
            habilitacao_manual_total INTEGER DEFAULT 0,
            biometria_sucesso_pos17h INTEGER DEFAULT 0,
            habilitacao_manual_pos17h INTEGER DEFAULT 0,
            pct_manual_pos17h REAL DEFAULT 0.0,
            
            -- Velocidade e cadência
            tempo_medio_voto_segundos REAL DEFAULT 0.0,
            tempo_medio_pos17h_segundos REAL DEFAULT 0.0,
            votos_ultrarapidos_pos17h INTEGER DEFAULT 0, -- < 45s por voto
            
            -- Indicador Composto de Suspeição (Score 0 a 100)
            score_suspeicao REAL DEFAULT 0.0,
            motivos_alerta TEXT,
            
            FOREIGN KEY(secao_id) REFERENCES secoes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS eventos_votos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secao_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            hora TEXT NOT NULL,
            apos_17h INTEGER NOT NULL, -- 1 ou 0
            tipo_habilitacao TEXT,     -- 'BIOMETRIA', 'MANUAL', 'DESCONHECIDO'
            duracao_voto_segundos INTEGER,
            FOREIGN KEY(secao_id) REFERENCES secoes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS resultados_eleicao (
            secao_id INTEGER PRIMARY KEY,
            pres_total_validos INTEGER DEFAULT 0,
            pres_brancos INTEGER DEFAULT 0,
            pres_nulos INTEGER DEFAULT 0,
            pres_venc_num INTEGER,
            pres_venc_votos INTEGER DEFAULT 0,
            pres_venc_pct REAL DEFAULT 0.0,
            pres_seg_num INTEGER,
            pres_seg_votos INTEGER DEFAULT 0,
            pres_seg_pct REAL DEFAULT 0.0,
            votos_cand_13 INTEGER DEFAULT 0,
            votos_cand_22 INTEGER DEFAULT 0,
            gov_venc_num INTEGER,
            gov_venc_votos INTEGER DEFAULT 0,
            gov_venc_pct REAL DEFAULT 0.0,
            FOREIGN KEY(secao_id) REFERENCES secoes(id) ON DELETE CASCADE
        );

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
            PRIMARY KEY (pleito, uf, zona),
            FOREIGN KEY(pleito) REFERENCES pleitos(codigo)
        );

        CREATE INDEX IF NOT EXISTS idx_secoes_loc ON secoes(uf, municipio, zona, secao);
        CREATE INDEX IF NOT EXISTS idx_secoes_uf_zona ON secoes(uf, zona);
        CREATE INDEX IF NOT EXISTS idx_secoes_pleito ON secoes(pleito);
        CREATE INDEX IF NOT EXISTS idx_auditoria_score ON auditoria_horarios(score_suspeicao DESC);
        CREATE INDEX IF NOT EXISTS idx_auditoria_pos17h ON auditoria_horarios(votos_apos_17h DESC);
        CREATE INDEX IF NOT EXISTS idx_eventos_secao_hora ON eventos_votos(secao_id, apos_17h);
        CREATE INDEX IF NOT EXISTS idx_resultados_pres_venc ON resultados_eleicao(pres_venc_num);
        """)
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Banco de dados inicializado com sucesso em: {DB_PATH}")
