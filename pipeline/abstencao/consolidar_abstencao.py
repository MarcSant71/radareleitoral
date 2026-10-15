"""
Módulo de Consolidação de Comparecimento e Abstenção - Eleições 2026.
Lê os arquivos oficiais de 'Detalhe da Apuração por Seção' do TSE (detalhe_votacao_secao),
extrai QT_APTOS, QT_COMPARECIMENTO e QT_ABSTENCAO para o cargo Presidente (para evitar duplicação),
e atualiza em lote as colunas total_aptos, comparecimento_bu e faltosos_bu na tabela secoes do SQLite.
"""

import os
import sys
import csv
import zipfile
import argparse
from pathlib import Path
from typing import Optional, Dict, Tuple

_pipeline_dir = Path(__file__).resolve().parent.parent
_web_dir = _pipeline_dir.parent / "web"
for _p in (_pipeline_dir, _web_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from db import get_connection

def consolidar_csv_detalhe(caminho_csv_ou_zip: Path, encoding: str = "latin1", batch_size: int = 10000) -> int:
    """
    Processa um arquivo CSV ou ZIP de detalhe_votacao_secao do TSE.
    Filtra por DS_CARGO == 'Presidente' (ou CD_CARGO == 1) e atualiza a tabela secoes.
    """
    print(f"\n[*] Abrindo base de detalhe do TSE: {caminho_csv_ou_zip.name}")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.execute("PRAGMA cache_size = -64000;")
    
    total_atualizados = 0
    buffer_lote = []

    def _executar_lote():
        nonlocal buffer_lote, total_atualizados
        if not buffer_lote:
            return
        with conn:
            cur.executemany("""
                UPDATE secoes 
                SET total_aptos = ?,
                    comparecimento_bu = ?,
                    faltosos_bu = ?
                WHERE uf = ? AND municipio = ? AND zona = ? AND secao = ?
            """, buffer_lote)
        total_atualizados += len(buffer_lote)
        buffer_lote = []

    def _processar_arquivo(leitor_linhas):
        reader = csv.DictReader(leitor_linhas, delimiter=";")
        for row in reader:
            # Filtra apenas 1º Turno (para não duplicar contagens do 2º turno)
            nr_turno = str(row.get("NR_TURNO", "")).strip()
            if nr_turno and nr_turno != "1":
                continue

            # Filtra apenas Presidente para não duplicar contagens por cargo
            cd_cargo = str(row.get("CD_CARGO", "")).strip()
            ds_cargo = str(row.get("DS_CARGO", "")).upper()
            if cd_cargo != "1" and "PRESIDENTE" not in ds_cargo:
                continue

            uf = str(row.get("SG_UF", "")).strip().upper()
            mun = str(row.get("CD_MUNICIPIO", "")).strip().zfill(5)
            zona = str(row.get("NR_ZONA", "")).strip().zfill(4)
            secao = str(row.get("NR_SECAO", "")).strip().zfill(4)

            try:
                aptos = int(row.get("QT_APTOS", 0))
                comp = int(row.get("QT_COMPARECIMENTO", 0))
                # O TSE utiliza QT_ABSTENCOES nos arquivos oficiais
                falt_val = row.get("QT_ABSTENCOES") if "QT_ABSTENCOES" in row else row.get("QT_ABSTENCAO", 0)
                falt = int(falt_val)
            except (ValueError, TypeError):
                continue

            buffer_lote.append((aptos, comp, falt, uf, mun, zona, secao))
            if len(buffer_lote) >= batch_size:
                _executar_lote()
                print(f"[*] Progresso: {total_atualizados:,} seções atualizadas...", end="\r")

    if caminho_csv_ou_zip.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho_csv_ou_zip, "r") as z:
            brasil_csv = next((n for n in z.namelist() if n.endswith("BRASIL.csv")), None)
            if brasil_csv:
                print(f"[*] Base nacional localizada no pacote: {brasil_csv}")
                with z.open(brasil_csv) as f:
                    import io
                    leitor_txt = io.TextIOWrapper(f, encoding=encoding, errors="replace")
                    _processar_arquivo(leitor_txt)
            else:
                membros = [
                    n for n in z.namelist() 
                    if (n.endswith(".csv") or n.endswith(".txt")) and not n.endswith("_BR.csv")
                ]
                for nome_membro in membros:
                    print(f"[*] Processando arquivo estadual: {nome_membro}")
                    with z.open(nome_membro) as f:
                        import io
                        leitor_txt = io.TextIOWrapper(f, encoding=encoding, errors="replace")
                        _processar_arquivo(leitor_txt)
    else:
        with open(caminho_csv_ou_zip, "r", encoding=encoding, errors="replace") as f:
            _processar_arquivo(f)

    _executar_lote()
    conn.close()

    print(f"\n[+] Sucesso! {total_atualizados:,} seções tiveram aptos, comparecimento e abstenção consolidados.")
    return total_atualizados

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidador de Abstenção e Comparecimento (TSE) - Eleições 2026")
    parser.add_argument("--arquivo", required=True, help="Caminho para o arquivo CSV ou ZIP de detalhe_votacao_secao")
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.exists():
        print(f"ERRO: Arquivo '{caminho}' não encontrado!", file=sys.stderr)
        sys.exit(1)

    consolidar_csv_detalhe(caminho)
