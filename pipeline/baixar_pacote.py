"""
Script para Download Resiliente dos Pacotes Oficiais da CDN do TSE.
Suporta detecção autônoma de atualizações oficiais, substituição atômica via .part,
verificação de integridade de arquivos ZIP e retomada automática (resume) segura.
"""

import os
import sys
import time
import zipfile
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
    """
    Baixa ou atualiza o pacote de dados oficiais da urna para a UF e turno informados.
    Se o arquivo local for íntegro e idêntico à CDN do TSE, pula o download.
    Se o TSE publicou nova versão oficial (tamanho diferente), baixa via .part temporário
    e substitui com segurança atômica sem corromper arquivos prévios.
    """
    uf = uf.upper()
    destino_dir = destino_dir or DEFAULT_OUTPUT_DIR
    destino_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"bu_imgbu_logjez_rdv_vscmr_2026_{turno}t_{uf}.zip"
    url = f"{CDN_BASE_URL}/{nome_arquivo}"
    caminho_local = destino_dir / nome_arquivo
    caminho_part = destino_dir / f"{nome_arquivo}.part"

    sys.stdout.write(f"\rVerificando {uf} ({turno}ºT): conectando à CDN do TSE...                 ")
    sys.stdout.flush()

    # 1. Obtém o tamanho total do arquivo remoto de forma confiável via HEAD
    total_remoto = 0
    try:
        req_head = urllib.request.Request(url, method="HEAD")
        req_head.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        with urllib.request.urlopen(req_head, timeout=15) as resp:
            cl = resp.headers.get("Content-Length")
            if cl and int(cl) > 1024 * 1024:
                total_remoto = int(cl)
    except Exception:
        pass

    # 2. Se o arquivo já existe localmente
    if caminho_local.exists():
        tamanho_existente = caminho_local.stat().st_size
        if total_remoto > 0 and tamanho_existente == total_remoto:
            # Validação rápida de cabeçalho zip para garantir que não está corrompido
            try:
                with zipfile.ZipFile(caminho_local) as z:
                    names = z.namelist()
                    if names:
                        z.read(names[-1])
                # Arquivo oficial 100% íntegro e idêntico ao TSE!
                sys.stdout.write(f"\rBaixando {uf} ({turno}ºT): 100.0% - Concluído! (Arquivo oficial íntegro)                          \n")
                sys.stdout.flush()
                caminho_part.unlink(missing_ok=True)
                return caminho_local
            except Exception:
                # Arquivo corrompido -> precisa ser rebaixado limpo
                sys.stdout.write(f"\rBaixando {uf} ({turno}ºT): Arquivo local corrompido detectado. Baixando versão oficial limpa...\n")
                sys.stdout.flush()
                caminho_local.unlink(missing_ok=True)
        elif total_remoto > 0 and tamanho_existente != total_remoto:
            # Tamanho diferente -> TSE publicou nova versão oficial!
            rem_mb = round(total_remoto / (1024 * 1024), 1)
            loc_mb = round(tamanho_existente / (1024 * 1024), 1)
            sys.stdout.write(f"\rBaixando {uf} ({turno}ºT): Nova versão na CDN ({rem_mb} MB vs {loc_mb} MB local). Atualizando...\n")
            sys.stdout.flush()

    # 3. Gerenciamento do arquivo temporário de download (.part)
    tamanho_part = caminho_part.stat().st_size if caminho_part.exists() else 0
    if tamanho_part >= total_remoto and total_remoto > 0:
        caminho_part.unlink(missing_ok=True)
        tamanho_part = 0

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    modo_abertura = "wb"
    baixado = 0

    if tamanho_part > 0 and total_remoto > 0 and tamanho_part < total_remoto:
        headers["Range"] = f"bytes={tamanho_part}-"
        modo_abertura = "ab"
        baixado = tamanho_part
    else:
        tamanho_part = 0

    req_get = urllib.request.Request(url, headers=headers)
    bloco_size = 1024 * 1024  # 1 MB por bloco
    start_time = time.time()
    last_print = 0

    try:
        with urllib.request.urlopen(req_get, timeout=30) as resp:
            status = getattr(resp, "status", 200)

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
                    total_remoto = tamanho_part + cl

            # Se o servidor respondeu 200 (ignorou Range), recomeça do zero
            if status == 200 and modo_abertura == "ab":
                modo_abertura = "wb"
                baixado = 0
                tamanho_part = 0

            with open(caminho_part, modo_abertura) as f_out:
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
                        speed = ((baixado - tamanho_part) / elapsed / (1024 * 1024)) if elapsed > 0 else 0
                        pct = min(99.9, (baixado / total_remoto * 100.0)) if total_remoto > 0 else 0.0
                        sys.stdout.write(f"\rBaixando {uf} ({turno}ºT): {pct:5.1f}% | {speed:.1f} MB/s...                 ")
                        sys.stdout.flush()

    except urllib.error.HTTPError as he:
        if he.code == 416:
            # 416 Range Not Satisfiable: .part já completo
            pass
        else:
            print(f"\nErro HTTP {he.code} ao baixar {uf}: {he.reason}", file=sys.stderr)
            raise

    # 4. Conclusão e substituição atômica
    if total_remoto > 0 and caminho_part.exists() and caminho_part.stat().st_size == total_remoto:
        # Validação do zip antes de promover
        try:
            with zipfile.ZipFile(caminho_part) as z:
                _ = z.namelist()
        except Exception as e:
            caminho_part.unlink(missing_ok=True)
            raise RuntimeError(f"Arquivo baixado para {uf} corrompido: {e}")

        # Substitui com segurança atômica
        if caminho_local.exists():
            caminho_local.unlink(missing_ok=True)
        caminho_part.rename(caminho_local)
        sys.stdout.write(f"\rBaixando {uf} ({turno}ºT): 100.0% - Concluído! (Base oficial atualizada com sucesso)             \n")
        sys.stdout.flush()
        return caminho_local
    elif caminho_local.exists() and caminho_local.stat().st_size == total_remoto:
        return caminho_local
    else:
        raise RuntimeError(f"Tamanho baixado ({caminho_part.stat().st_size if caminho_part.exists() else 0}) não confere com remoto ({total_remoto}) para {uf}")


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

    print(f"Total de estados a baixar (Território Nacional Completo): {len(lista_ufs)} ({', '.join(lista_ufs)})")
    for i, estado in enumerate(lista_ufs, 1):
        print(f"\n[{i}/{len(lista_ufs)}] Iniciando processamento de {estado}...")
        try:
            baixar_pacote_uf(estado, destino_dir=dest, turno=args.turno)
        except Exception as e:
            print(f"Falha ao baixar {estado}: {e}", file=sys.stderr)
