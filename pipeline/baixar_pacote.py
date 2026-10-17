"""
Script para Download Resiliente dos Pacotes Oficiais da CDN do TSE.
Suporta retomada automática (resume) em caso de queda de conexão,
verificação de tamanho e salvamento em disco local.
"""

import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

_pipeline_dir = Path(__file__).resolve().parent
if str(_pipeline_dir) not in sys.path:
    sys.path.insert(0, str(_pipeline_dir))

from downloader import CDN_BASE_URL

project_root = Path(__file__).resolve().parent.parent
env_dir = os.environ.get("DADOS_DIR")
if env_dir and Path(env_dir).exists():
    DEFAULT_OUTPUT_DIR = Path(env_dir).resolve()
else:
    DEFAULT_OUTPUT_DIR = project_root / "dados_brutos" / "arquivos_urna"

def baixar_pacote_uf(uf: str, destino_dir: Optional[Path] = None, turno: int = 1) -> Path:
    uf = uf.upper()
    destino_dir = destino_dir or DEFAULT_OUTPUT_DIR
    destino_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"bu_imgbu_logjez_rdv_vscmr_2026_{turno}t_{uf}.zip"
    url = f"{CDN_BASE_URL}/{nome_arquivo}"
    caminho_local = destino_dir / nome_arquivo
    tamanho_existente = caminho_local.stat().st_size if caminho_local.exists() else 0
    sys.stdout.write(f"\rBaixando {uf}:   0.0% conectando ao TSE...                 ")
    sys.stdout.flush()

    # 1. Obtém o tamanho total do arquivo remoto de forma confiável via HEAD
    total_remoto = 0
    try:
        req_head = urllib.request.Request(url, method="HEAD")
        req_head.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req_head, timeout=15) as resp:
            cl = resp.headers.get("Content-Length")
            # Um pacote de urna tem pelo menos vários megabytes (evita respostas truncadas/WAF)
            if cl and int(cl) > 1024 * 1024:
                total_remoto = int(cl)
    except Exception:
        pass

    # Se o arquivo já existe localmente e confere com o tamanho remoto
    if total_remoto > 0 and tamanho_existente == total_remoto:
        sys.stdout.write(f"\rBaixando {uf}: 100.0% - Concluído! (Arquivo já baixado)                          \n")
        sys.stdout.flush()
        return caminho_local

    headers = {"User-Agent": "Mozilla/5.0"}
    modo_abertura = "wb"
    baixado = 0

    if tamanho_existente > 0:
        if total_remoto > 0 and tamanho_existente < total_remoto:
            headers["Range"] = f"bytes={tamanho_existente}-"
            modo_abertura = "ab"
            baixado = tamanho_existente
        elif total_remoto == 0:
            headers["Range"] = f"bytes={tamanho_existente}-"
            modo_abertura = "ab"
            baixado = tamanho_existente
        else:
            tamanho_existente = 0
            modo_abertura = "wb"
            baixado = 0

    req_get = urllib.request.Request(url, headers=headers)
    bloco_size = 1024 * 1024  # 1 MB por bloco
    start_time = time.time()
    last_print = 0

    try:
        with urllib.request.urlopen(req_get, timeout=30) as resp:
            status = getattr(resp, "status", 200)

            # Extrai o tamanho total definitivo a partir da resposta do GET
            content_range = resp.headers.get("Content-Range")
            if content_range and "/" in content_range:
                try:
                    total_remoto = int(content_range.split("/")[-1])
                except (ValueError, TypeError):
                    pass
            elif resp.headers.get("Content-Length"):
                cl = int(resp.headers.get("Content-Length", 0))
                if status == 200:
                    total_remoto = cl
                elif status == 206 and total_remoto == 0:
                    total_remoto = tamanho_existente + cl

            # Se o servidor respondeu 200 (ignorou Range), recomeça gravação limpa
            if status == 200 and modo_abertura == "ab":
                modo_abertura = "wb"
                baixado = 0
                tamanho_existente = 0

            # Caso especial: já estava completo
            if total_remoto > 0 and tamanho_existente == total_remoto:
                sys.stdout.write(f"\rBaixando {uf}: 100.0% - Concluído!                                   \n")
                sys.stdout.flush()
                return caminho_local

            with open(caminho_local, modo_abertura) as f_out:
                while True:
                    bloco = resp.read(bloco_size)
                    if not bloco:
                        break
                    f_out.write(bloco)
                    baixado += len(bloco)
                    now = time.time()
                    if now - last_print >= 0.25:
                        last_print = now
                        elapsed = now - start_time
                        speed = ((baixado - tamanho_existente) / elapsed / (1024 * 1024)) if elapsed > 0 else 0
                        pct = min(99.9, (baixado / total_remoto * 100.0)) if total_remoto > 0 else 0.0
                        sys.stdout.write(f"\rBaixando {uf}: {pct:5.1f}% | {speed:.1f} MB/s...                 ")
                        sys.stdout.flush()

    except urllib.error.HTTPError as he:
        if he.code == 416:
            # 416 Range Not Satisfiable: arquivo já está totalmente baixado
            sys.stdout.write(f"\rBaixando {uf}: 100.0% - Concluído!                                   \n")
            sys.stdout.flush()
            return caminho_local
        else:
            print(f"Erro HTTP {he.code} ao baixar {uf}: {he.reason}", file=sys.stderr)
            raise

    sys.stdout.write(f"\rBaixando {uf}: 100.0% - Concluído!                                   \n")
    sys.stdout.flush()
    return caminho_local


UFS_BRASIL = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloader Oficial dos Pacotes de Urna do TSE — Território Nacional Completo (27 UFs)")
    parser.add_argument("--destino", default=None, help="Diretório de destino no storage (opcional)")
    parser.add_argument("--turno", type=int, default=1, help="Turno da eleição (padrão: 1)")

    args = parser.parse_args()
    dest = Path(args.destino) if args.destino else None
    lista_ufs = UFS_BRASIL

    print(f"Total de estados a baixar (Território Nacional Mandatório): {len(lista_ufs)} ({', '.join(lista_ufs)})")
    for i, estado in enumerate(lista_ufs, 1):
        print(f"\n[{i}/{len(lista_ufs)}] Iniciando processamento de {estado}...")
        try:
            baixar_pacote_uf(estado, destino_dir=dest, turno=args.turno)
        except Exception as e:
            print(f"Falha ao baixar {estado}: {e}", file=sys.stderr)

