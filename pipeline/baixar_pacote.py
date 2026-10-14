"""
Script para Download Resiliente dos Pacotes Oficiais da CDN do TSE.
Suporta retomada automática (resume) em caso de queda de conexão,
verificação de tamanho e salvamento em disco local.
"""

import os
import sys
import argparse
import urllib.request
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
    DEFAULT_OUTPUT_DIR = project_root / "dados_brutos"

def baixar_pacote_uf(uf: str, destino_dir: Optional[Path] = None, turno: int = 1) -> Path:
    uf = uf.upper()
    destino_dir = destino_dir or DEFAULT_OUTPUT_DIR
    destino_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"bu_imgbu_logjez_rdv_vscmr_2026_{turno}t_{uf}.zip"
    url = f"{CDN_BASE_URL}/{nome_arquivo}"
    caminho_local = destino_dir / nome_arquivo

    print(f"\n[DOWNLOAD] Conectando ao TSE para baixar pacote da UF: {uf}")
    print(f"URL: {url}")
    print(f"Destino local: {caminho_local}")

    # Obtém o tamanho total do arquivo remoto via HEAD
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req) as resp:
            total_remoto = int(resp.headers.get("Content-Length", 0))
    except Exception as e:
        print(f"Erro ao verificar arquivo remoto: {e}", file=sys.stderr)
        sys.exit(1)

    tamanho_existente = caminho_local.stat().st_size if caminho_local.exists() else 0

    if total_remoto > 0 and tamanho_existente == total_remoto:
        print(f"Arquivo já totalmente baixado e verificado: {tamanho_existente / (1024**3):.2f} GB.")
        return caminho_local

    headers = {"User-Agent": "Mozilla/5.0"}
    modo_abertura = "wb"
    if tamanho_existente > 0:
        if tamanho_existente < total_remoto:
            print(f"Retomando download a partir de {tamanho_existente / (1024**2):.1f} MB (Total: {total_remoto / (1024**3):.2f} GB)...")
            headers["Range"] = f"bytes={tamanho_existente}-"
            modo_abertura = "ab"
        else:
            print("Arquivo local maior que o remoto. Reiniciando download...")
            tamanho_existente = 0

    req_get = urllib.request.Request(url, headers=headers)
    bloco_size = 1024 * 1024 # 1 MB por bloco
    baixado = tamanho_existente

    import time
    start_time = time.time()
    last_print = 0

    with urllib.request.urlopen(req_get) as resp, open(caminho_local, modo_abertura) as f_out:
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
                pct = (baixado / total_remoto * 100.0) if total_remoto > 0 else 0.0
                mb_baixado = baixado / (1024 * 1024)
                mb_total = total_remoto / (1024 * 1024)
                sys.stdout.write(f"\rBaixando {uf}: {mb_baixado:.1f}/{mb_total:.1f} MB ({pct:.1f}%) a {speed:.1f} MB/s...  ")
                sys.stdout.flush()

    pct_final = (baixado / total_remoto * 100.0) if total_remoto > 0 else 100.0
    sys.stdout.write(f"\rBaixando {uf}: {baixado/(1024*1024):.1f}/{total_remoto/(1024*1024):.1f} MB ({pct_final:.1f}%) - Concluido!\n")
    sys.stdout.flush()
    print(f"Arquivo salvo com sucesso em: {caminho_local}\n", flush=True)
    return caminho_local

UFS_BRASIL = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloader Resiliente de Pacotes de Urna do TSE (Brasil Inteiro)")
    parser.add_argument("--uf", default=None, help="Sigla de um estado individual (ex: BA, SP, RJ)")
    parser.add_argument("--ufs", nargs="+", default=None, help="Lista de estados (ex: --ufs SP RJ MG BA)")
    parser.add_argument("--todas", action="store_true", help="Baixa os pacotes de TODAS as 27 UFs do Brasil sequencialmente")
    parser.add_argument("--destino", default=None, help="Diretório de destino no storage (opcional)")
    parser.add_argument("--turno", type=int, default=1, help="Turno da eleição (padrão: 1)")

    args = parser.parse_args()
    dest = Path(args.destino) if args.destino else None

    if args.todas:
        lista_ufs = UFS_BRASIL
    elif args.ufs:
        lista_ufs = [u.upper() for u in args.ufs]
    elif args.uf:
        lista_ufs = [args.uf.upper()]
    else:
        print("Erro: Especifique --uf, --ufs ou --todas.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    print(f"Total de estados a baixar: {len(lista_ufs)} ({', '.join(lista_ufs)})")
    for i, estado in enumerate(lista_ufs, 1):
        print(f"\n[{i}/{len(lista_ufs)}] Iniciando processamento de {estado}...")
        try:
            baixar_pacote_uf(estado, destino_dir=dest, turno=args.turno)
        except Exception as e:
            print(f"Falha ao baixar {estado}: {e}", file=sys.stderr)

