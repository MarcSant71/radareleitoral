"""
Módulo de Banco de Dados SQLite do Pipeline Eleitoral 2026.
Responsável pelo Schema DDL, inicialização de tabelas, índices e conexões com WAL mode.
Pode ser executado diretamente via CLI:
    python -m pipeline.db --init
    python -m pipeline.db --zerar
    python -m pipeline.db --status
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# Garante suporte seguro a UTF-8 em consoles Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def get_db_path() -> Path:
    """
    Localiza o banco SQLite de forma estrita e determinística.
    Prioridade:
    1. Variável de ambiente DATABASE_PATH (se informada)
    2. Pasta db/ relativa à raiz do projeto (db/eleicoes.db)
       Fallback automático para db/eleicoes2026.db caso o novo ainda não exista.
    """
    env_path = os.environ.get("DATABASE_PATH")
    if env_path:
        return Path(env_path).resolve()

    project_root = Path(__file__).resolve().parent.parent
    caminho_novo = (project_root / "db" / "eleicoes.db").resolve()
    caminho_legado = (project_root / "db" / "eleicoes2026.db").resolve()

    if not caminho_novo.exists() and caminho_legado.exists():
        return caminho_legado

    return caminho_novo

DB_PATH = get_db_path()

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Retorna uma conexão SQLite otimizada com WAL, timeout e row_factory."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    """Inicializa todas as tabelas, chaves primárias e índices do schema oficial."""
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
        VALUES 
            ('03220', 2026, 1, 'Eleições Gerais 2026 - 1º Turno', '2026-10-04'),
            ('03221', 2026, 2, 'Eleições Gerais 2026 - 2º Turno', '2026-10-25');

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
            votos_ultrarapidos_pos17h INTEGER DEFAULT 0,
            
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
            apos_17h INTEGER NOT NULL,
            tipo_habilitacao TEXT,
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

def zerar_db(db_path: Optional[Path] = None) -> None:
    """Exclui o arquivo físico do SQLite e reconstrói o schema limpo."""
    path = db_path or DB_PATH
    if path.exists():
        path.unlink()
        wal = path.with_suffix(".db-wal")
        shm = path.with_suffix(".db-shm")
        if wal.exists(): wal.unlink()
        if shm.exists(): shm.unlink()
    init_db(path)

def obter_status_db(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retorna métricas de volumetria e status das tabelas do banco."""
    path = db_path or DB_PATH
    if not path.exists():
        return {"existe": False, "caminho": str(path), "tamanho_mb": 0.0, "tabelas": {}}

    tamanho_mb = round(path.stat().st_size / (1024 * 1024), 2)
    tabelas_alvo = ["pleitos", "secoes", "auditoria_horarios", "resultados_eleicao", "zonas_totais", "eventos_votos"]
    contagens = {}

    conn = get_connection(path)
    cur = conn.cursor()
    for tab in tabelas_alvo:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tab}")
            contagens[tab] = cur.fetchone()[0]
        except Exception:
            contagens[tab] = 0
    conn.close()

    return {
        "existe": True,
        "caminho": str(path),
        "tamanho_mb": tamanho_mb,
        "tabelas": contagens
    }

def main():
    parser = argparse.ArgumentParser(description="Gerenciador de Schema e Banco de Dados (pipeline.db)")
    parser.add_argument("--init", action="store_true", help="Cria tabelas e índices se não existirem")
    parser.add_argument("--zerar", action="store_true", help="Remove banco existente e recria schema limpo")
    parser.add_argument("--status", action="store_true", help="Exibe contagens e métricas do banco de dados")

    args = parser.parse_args()

    if args.zerar:
        print(f"[*] Zerando e recriando schema limpo em: {DB_PATH}")
        zerar_db()
        print("[+] Banco de dados recriado com sucesso.")
    elif args.init:
        print(f"[*] Inicializando schema em: {DB_PATH}")
        init_db()
        print("[+] Schema inicializado com sucesso.")
    
    # Se nenhum argumento for passado ou após a operação, exibe o status
    st = obter_status_db()
    print("\n" + "═" * 60)
    print("STATUS DO BANCO DE DADOS (SQLite):")
    print("═" * 60)
    print(f"Caminho: {st['caminho']}")
    print(f"Existe: {'SIM' if st['existe'] else 'NÃO'} ({st['tamanho_mb']} MB)")
    if st['existe']:
        print("─" * 60)
        for tab, count in st['tabelas'].items():
            print(f"  • {tab:<22}: {count:>10,} registros")
    print("═" * 60 + "\n")

if __name__ == "__main__":
    main()
