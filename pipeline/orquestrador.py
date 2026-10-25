"""
Orquestrador Mestre do Pipeline de Dados Eleitorais 2026.
Consolida em 5 etapas modulares e sequenciais:
1. Inicialização do schema SQLite (pipeline.db)
2. Download e validação da CDN oficial do TSE (pipeline.baixar)
3. Auditoria temporal de logs de urnas (pipeline.auditar)
4. Decodificação ASN.1 dos BUs e agregação de zonas (pipeline.consolidar)
5. Compilação analítica com modelos estatísticos em Parquet (pipeline.compilar)
"""

import os
import sys
import time
import argparse
import platform
import urllib.request
from pathlib import Path
from typing import List, Optional

# Garante suporte seguro a UTF-8 em consoles Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_root_dir = Path(__file__).resolve().parent.parent
_pipeline_dir = _root_dir / "pipeline"
_web_dir = _root_dir / "web"
for _p in (_root_dir, _pipeline_dir, _web_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pipeline.db import DB_PATH, init_db, get_connection, zerar_db
from pipeline.baixar_pacote import baixar_pacote_uf, UFS_BRASIL, DEFAULT_OUTPUT_DIR
from pipeline.downloader import CDN_BASE_URL
from pipeline.auditar import executar_auditoria_local_zip
from pipeline.consolidar_bu import processar_pacote_uf, atualizar_zonas_totais
from pipeline.compilar import compilar_dataset_parquet, PARQUET_PATH


def verificar_trava_producao() -> None:
    """
    Trava de segurança rigorosa para impedir a execução acidental
    deste pipeline pesado no servidor VPS de produção.
    """
    indicadores_producao = [
        os.path.exists("/opt/eleicao2026"),
        os.path.exists("/opt/radareleitoral"),
        os.environ.get("PRODUCTION") == "1",
        os.environ.get("ENV") == "production",
        "hetzner" in platform.node().lower(),
        "vps" in platform.node().lower(),
    ]
    if any(indicadores_producao):
        print("\n" + "═" * 80, file=sys.stderr)
        print("⛔ ERRO DE SEGURANÇA: AMBIENTE DE PRODUÇÃO DETECTADO!", file=sys.stderr)
        print("═" * 80, file=sys.stderr)
        print("Este pipeline executa download massivo (25GB+) e alto consumo de CPU/I/O.", file=sys.stderr)
        print("Ele NUNCA deve ser executado no servidor público de produção.", file=sys.stderr)
        print("Execute localmente na sua máquina e suba os artefatos via scripts/subirproducao.ps1.", file=sys.stderr)
        print("═" * 80 + "\n", file=sys.stderr)
        sys.exit(1)


def detectar_turnos_disponiveis(ano: int = 2026, dados_dir: Optional[Path] = None) -> List[int]:
    """
    Detecta autonomamente os turnos eleitorais disponíveis para processamento.
    Verifica primeiro no disco local (dados_brutos/) e, se ausente, sonda
    a CDN oficial do TSE via requisição HEAD leve para o arquivo sentinela (AC).
    Retorna lista com os turnos disponíveis, ex: [1], [2], ou [1, 2].
    """
    pasta = dados_dir or DEFAULT_OUTPUT_DIR
    turnos_detectados = []

    for t in (1, 2):
        # 1. Verifica no disco local
        if pasta.exists():
            arquivos_locais = list(pasta.glob(f"*_{ano}_{t}t_*.zip"))
            if not arquivos_locais:
                arquivos_locais = list(pasta.glob(f"*_{t}t_*.zip"))
            if not arquivos_locais and pasta.parent.exists() and pasta.name != "dados_brutos":
                arquivos_locais = list(pasta.parent.glob(f"*_{ano}_{t}t_*.zip"))
            if len(arquivos_locais) > 0:
                turnos_detectados.append(t)
                continue

        # 2. Sonda CDN remota do TSE com timeout curto
        url_sentinela = f"https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/arqurnatot/bu_imgbu_logjez_rdv_vscmr_{ano}_{t}t_AC.zip"
        try:
            req = urllib.request.Request(url_sentinela, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            with urllib.request.urlopen(req, timeout=5) as resp:
                cl = resp.headers.get("Content-Length")
                if resp.status == 200 and cl and int(cl) > 1024 * 1024:
                    turnos_detectados.append(t)
        except Exception:
            pass

    # Fallback seguro caso esteja offline e sem arquivos locais
    if not turnos_detectados:
        turnos_detectados = [1]

    return sorted(turnos_detectados)


def exibir_banner_e_confirmar(turnos: List[int], ano: int, zerar_banco: bool, forcar: bool) -> None:
    """
    Exibe os alertas mandatórios de governança antes de iniciar o processo.
    Abrangência estritamente nacional (todas as 27 UFs).
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(f"Inicialização da Base de Dados Eleitoral ({ano})")
        except Exception:
            pass

    print("═" * 80)
    print(f"      ⚠️   INICIALIZAÇÃO DA BASE DE DADOS ELEITORAL ({ano})   ⚠️")
    print("═" * 80)
    if turnos == [1, 2]:
        desc_turnos = "1º e 2º Turnos"
    elif turnos == [2]:
        desc_turnos = "2º Turno"
    else:
        desc_turnos = " e ".join(f"{t}º Turno" for t in turnos)

    desc_pleito = f"Eleições Gerais {ano} — {desc_turnos}"
    print(f"Pleito: {desc_pleito}")
    print(f"Escopo: Território Nacional Completo ({len(UFS_BRASIL)} UFs)")
    print(f"Diretório de Armazenamento: {DEFAULT_OUTPUT_DIR}")
    print(f"Banco Alvo: {DB_PATH}")
    print("─" * 80)
    print("IMPORTANTE! LEIA COM ATENÇÃO:")
    print("  1. DOWNLOAD DE DADOS:")
    multiplicador_turnos = len(turnos)
    gb_min = 25 * multiplicador_turnos
    gb_max = 30 * multiplicador_turnos
    print(f"     Volume estimado de download: cerca de {gb_min} a {gb_max} GB (497.895 seções por turno).")
    print("     Arquivos já existentes localmente serão verificados e preservados automaticamente.")
    print("  2. RESET DO BANCO DE DADOS:")
    if zerar_banco:
        print("     O banco de dados será inicializado/zerado com a estrutura oficial completa (--zerar ativo).")
    else:
        print("     O banco existente será preservado e atualizado de forma incremental (resume inteligente).")
    print("  3. SEGURANÇA OPERACIONAL:")
    print("     Execute esta rotina exclusivamente no seu ambiente local (Local-First).")
    print("     Não execute em servidores VPS em nuvem sob risco de esgotamento de recursos.")
    print("  4. PROCESSAMENTO INTENSIVO E TEMPO ESTIMADO:")
    tempo_min = 30 * multiplicador_turnos
    tempo_max = 50 * multiplicador_turnos
    print(f"     O tempo total estimado é de aproximadamente {tempo_min} a {tempo_max} minutos.")
    print("     Os tempos estimados dependem da velocidade da internet e da capacidade do computador.")
    print("     Recomenda-se manter o computador ligado e desativar o modo de suspensão/hibernação.")
    print("═" * 80 + "\n")

    if not forcar:
        confirmacao = input("Digite 'SIM' para continuar: ").strip()
        if confirmacao != "SIM":
            print("\n[!] Operação cancelada.")
            sys.exit(0)
        print("\n[+] Confirmação aceita. Iniciando processamento...\n")


def orquestrar_pipeline(
    ano: int = 2026,
    zerar_banco: bool = False,
    pular_download: bool = False,
    threads: int = 24,
    reprocessar: bool = False
) -> None:
    """
    Executa a cadeia modular do pipeline em ordem estrita de integridade.
    Processa obrigatoriamente todas as 27 UFs para todos os turnos detectados.
    """
    ufs = UFS_BRASIL
    turnos = detectar_turnos_disponiveis(ano=ano)
    t_inicio_total = time.time()

    # 1. Inicialização do Banco de Dados
    print("=" * 80)
    print("ETAPA 1/5: INICIALIZAÇÃO DO SCHEMA DO BANCO RELACIONAL (SQLite)")
    print("=" * 80)
    if zerar_banco:
        print(f"[*] Zerando banco de dados para reconstrução limpa: {DB_PATH.name}")
        zerar_db()
    else:
        init_db()

    conn = get_connection(DB_PATH)
    pleitos_oficiais = [
        ("03220", ano, 1, f"Eleições Gerais {ano} - 1º Turno", f"{ano}-10-04"),
        ("03221", ano, 2, f"Eleições Gerais {ano} - 2º Turno", f"{ano}-10-25"),
    ]
    with conn:
        for cod_pleito, a, t, desc_pleito, dt_pleito in pleitos_oficiais:
            conn.execute("""
                INSERT OR IGNORE INTO pleitos (codigo, ano, turno, descricao, data_votacao)
                VALUES (?, ?, ?, ?, ?)
            """, (cod_pleito, a, t, desc_pleito, dt_pleito))
            status_turno = "dados disponíveis para processamento" if t in turnos else "aguardando publicação TSE"
            print(f"[+] Pleito '{cod_pleito}' ({desc_pleito}) registrado no banco ({status_turno}).")
    conn.close()
    print("[+] Schema do SQLite validado e pleitos estruturados (1º e 2º Turnos).\n")

    # Garante o catálogo oficial de municípios do TSE de forma automatizada
    from pipeline.auditar import garantir_municipios_csv
    garantir_municipios_csv()

    total_bus_geral = 0
    total_ufs_atualizadas_geral = set()

    # Processa Etapas 2, 3 e 4 para cada turno disponível
    for idx_t, turno in enumerate(turnos, 1):
        sufixo_turno = f" (TURNO {turno} DE {len(turnos)})" if len(turnos) > 1 else ""

        # 2. Download dos Pacotes Oficiais da CDN do TSE
        print("=" * 80)
        print(f"ETAPA 2/5: VERIFICAÇÃO E DOWNLOAD DOS PACOTES OFICIAIS DO TSE{sufixo_turno}")
        print("=" * 80)
        pacotes_por_uf = {}
        ufs_atualizadas_turno = set()
        for uf in ufs:
            if pular_download:
                nome_esperado = f"bu_imgbu_logjez_rdv_vscmr_{ano}_{turno}t_{uf.upper()}.zip"
                local_zip = DEFAULT_OUTPUT_DIR / nome_esperado
                if not local_zip.exists():
                    candidatos = list(DEFAULT_OUTPUT_DIR.glob(f"*_{ano}_{turno}t_{uf.upper()}.zip"))
                    if not candidatos:
                        candidatos = list(DEFAULT_OUTPUT_DIR.glob(f"*_{turno}t_{uf.upper()}.zip"))
                    if not candidatos and DEFAULT_OUTPUT_DIR.parent.exists() and DEFAULT_OUTPUT_DIR.name != "dados_brutos":
                        candidatos = list(DEFAULT_OUTPUT_DIR.parent.glob(f"*_{ano}_{turno}t_{uf.upper()}.zip"))
                    if candidatos:
                        local_zip = candidatos[0]
                if local_zip.exists():
                    sys.stdout.write(f"\rBaixando {uf} ({turno}ºT): 100.0% - Concluído! (Arquivo já baixado)                          \n")
                    sys.stdout.flush()
                    pacotes_por_uf[uf] = local_zip
                else:
                    zpath, mudou = baixar_pacote_uf(uf, turno=turno)
                    pacotes_por_uf[uf] = zpath
                    if mudou:
                        ufs_atualizadas_turno.add(uf)
            else:
                zpath, mudou = baixar_pacote_uf(uf, turno=turno)
                pacotes_por_uf[uf] = zpath
                if mudou:
                    ufs_atualizadas_turno.add(uf)

        total_ufs_atualizadas_geral.update(ufs_atualizadas_turno)
        print(f"[+] Total de pacotes prontos ({turno}º Turno): {len(pacotes_por_uf)}")
        if ufs_atualizadas_turno:
            print(f"[!] UFs com pacotes atualizados pela CDN ({len(ufs_atualizadas_turno)}): {', '.join(sorted(ufs_atualizadas_turno))}\n")
        else:
            print("[i] Nenhuma alteração de pacote detectada na CDN do TSE para este turno.\n")

        # 3. Processamento e Cronologia dos Logs das Urnas (-log.jez)
        print("=" * 80)
        print(f"ETAPA 3/5: PROCESSAMENTO E CRONOLOGIA DOS LOGS DE URNA (-log.jez){sufixo_turno}")
        print("=" * 80)
        for uf, zpath in pacotes_por_uf.items():
            deve_forcar = (reprocessar or (uf in ufs_atualizadas_turno))
            executar_auditoria_local_zip(zpath, threads=threads, forcar_reprocessamento=deve_forcar)
        print(f"[+] Cronologia e métricas de logs ({turno}º Turno) processadas com sucesso.\n")

        # 4. Consolidação de Boletins de Urna (BUs) & Zonas
        print("=" * 80)
        print(f"ETAPA 4/5: DECODIFICAÇÃO ASN.1 DOS BOLETINS DE URNA (-bu.dat){sufixo_turno}")
        print("=" * 80)
        conn = get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, pleito, uf, municipio, zona, secao FROM secoes")
        secoes_map = {(row[1], row[2], row[3], row[4], row[5]): row[0] for row in cur.fetchall()}
        cur.execute("SELECT secao_id FROM resultados_eleicao")
        processados = {row[0] for row in cur.fetchall()}
        conn.close()

        total_bus_turno = 0
        for uf, zpath in pacotes_por_uf.items():
            deve_forcar = (reprocessar or (uf in ufs_atualizadas_turno))
            total_bus_turno += processar_pacote_uf(
                zpath, secoes_map, processados, num_threads=threads, forcar_reprocessamento=deve_forcar
            )

        total_bus_geral += total_bus_turno
        print(f"[+] Total de BUs processados ({turno}º Turno): {total_bus_turno:,}\n")

    # Consolida zonas_totais abrangendo todos os pleitos processados
    print("[*] Atualizando agregação de zonas eleitorais (zonas_totais)...")
    atualizar_zonas_totais()
    print("[+] Tabela 'zonas_totais' consolidada com chave primária por pleito.\n")

    # 5. Geração do Cache Analítico Colunar de Alta Velocidade (Parquet)
    print("=" * 80)
    print("ETAPA 5/5: MATERIALIZAÇÃO DO CACHE COLUNAR ANALÍTICO (Parquet)")
    print("=" * 80)
    df = compilar_dataset_parquet(forcar=True)

    # 6. Sincronização Geoespacial de Locais de Votação (Mapa de Fiscais & Seções)
    from pipeline.processamento_locais import PARQUET_LOCAIS_PATH, PARQUET_SECOES_PATH, consolidar_locais_nacionais
    conn = get_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='locais_votacao'")
    tem_tabela_locais = (cur.fetchone()[0] > 0)
    conn.close()

    if zerar_banco or not tem_tabela_locais or not PARQUET_LOCAIS_PATH.exists() or not PARQUET_SECOES_PATH.exists():
        print("\n" + "=" * 80)
        print("ETAPA ADICIONAL: SINCRONIZAÇÃO GEOESPACIAL DE LOCAIS DE VOTAÇÃO (MAPA)")
        print("=" * 80)
        try:
            consolidar_locais_nacionais()
        except Exception as e:
            print(f"[!] Aviso: Não foi possível sincronizar locais de votação automaticamente ({e}).")

    t_total = time.time() - t_inicio_total

    # 7. Gravação do Indicador de Alterações Consolidadas
    novos_dados = (len(total_ufs_atualizadas_geral) > 0 or total_bus_geral > 0 or zerar_banco or reprocessar)
    status_file = _root_dir / "db" / ".novos_dados_consolidados"
    if novos_dados:
        try:
            status_file.write_text(
                f"timestamp={int(time.time())}\nbus={total_bus_geral}\nufs={','.join(sorted(total_ufs_atualizadas_geral))}\n",
                encoding="utf-8"
            )
            print(f"[+] Indicador de atualizações gravado: {status_file.name} (Pronto para deploy em produção).")
        except Exception:
            pass
    else:
        try:
            status_file.unlink(missing_ok=True)
        except Exception:
            pass
        print("[i] Nenhuma novidade no TSE e nenhum BU novo processado nesta execução.")

    print("\n" + "═" * 80)
    print("      🎉  INICIALIZAÇÃO DA BASE ELEITORAL CONCLUÍDA COM SUCESSO!  🎉")
    print("═" * 80)
    desc_turnos_fim = " e ".join(f"{t}º" for t in turnos) + (" Turno" if len(turnos) == 1 else " Turnos")
    print(f"Turno(s) Processado(s): {desc_turnos_fim}")
    print(f"Total de Seções Consolidadas no Dataset: {len(df):,}")
    print(f"Colunas estruturadas: {len(df.columns)}")
    print(f"Arquivo SQLite:  {DB_PATH} ({round(DB_PATH.stat().st_size / (1024*1024), 1)} MB)")
    if PARQUET_PATH.exists():
        print(f"Arquivo Parquet: {PARQUET_PATH} ({round(PARQUET_PATH.stat().st_size / (1024*1024), 1)} MB)")
    print(f"Tempo Total de Execução: {round(t_total / 60, 1)} minutos ({round(t_total, 1)}s)")
    print("═" * 80)
    print("Para subir os dados para o servidor de produção, execute:")
    print("   powershell -File scripts/subirproducao.ps1")
    print("═" * 80)


def main():
    verificar_trava_producao()

    _cpu_total = os.cpu_count() or 16
    _default_workers = max(4, min(_cpu_total - 2, 24))

    parser = argparse.ArgumentParser(
        description="Inicializador Oficial da Base de Dados Eleitoral — Abrangência Nacional Mandatória (27 UFs)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--ano", type=int, default=2026, help="Ano da eleição (padrão: 2026)")
    parser.add_argument("--threads", type=int, default=_default_workers, help=f"Número de processos paralelos de CPU (padrão adaptativo: {_default_workers})")
    parser.add_argument("--zerar", action="store_true", help="Zera o banco de dados antes de recriar")
    parser.add_argument("--reprocessar", action="store_true", help="Força reprocessamento de BUs e logs de todas as UFs")
    parser.add_argument("--pular-download", action="store_true", help="Utiliza pacotes ZIP já existentes localmente sem consultar a CDN")
    parser.add_argument("--forcar", action="store_true", help="Pula confirmação interativa (para automações e scripts)")

    args = parser.parse_args()

    turnos_alvo = detectar_turnos_disponiveis(ano=args.ano)

    exibir_banner_e_confirmar(turnos_alvo, args.ano, args.zerar, args.forcar)
    orquestrar_pipeline(
        ano=args.ano,
        zerar_banco=args.zerar,
        pular_download=args.pular_download,
        threads=args.threads,
        reprocessar=args.reprocessar
    )


if __name__ == "__main__":
    main()
