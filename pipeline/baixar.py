"""
Módulo de Download dos Pacotes Oficiais do TSE — Pipeline Eleições 2026.
Pode ser executado diretamente via CLI:
    python -m pipeline.baixar --uf SP
    python -m pipeline.baixar --todas
"""

import sys
import argparse
from pathlib import Path

# Garante suporte seguro a UTF-8 em consoles Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_pipeline_dir = Path(__file__).resolve().parent
if str(_pipeline_dir) not in sys.path:
    sys.path.insert(0, str(_pipeline_dir))

from pipeline.baixar_pacote import baixar_pacote_uf, UFS_BRASIL, DEFAULT_OUTPUT_DIR

def main():
    parser = argparse.ArgumentParser(description="Download de Pacotes de Dados Brutos do TSE (pipeline.baixar)")
    parser.add_argument("--uf", default=None, help="Sigla da UF (ex: BA, SP, RJ)")
    parser.add_argument("--todas", action="store_true", help="Baixa todas as 27 UFs do Brasil")
    parser.add_argument("--turno", type=int, default=1, choices=[1, 2], help="Turno da eleição (padrão: 1)")

    args = parser.parse_args()

    if args.todas:
        ufs = UFS_BRASIL
    elif args.uf:
        ufs = [args.uf.upper()]
    else:
        print("[!] Especifique --uf <SIGLA> ou --todas para baixar.")
        sys.exit(1)

    print(f"[*] Iniciando download para {len(ufs)} UF(s) no diretório: {DEFAULT_OUTPUT_DIR}")
    for i, uf in enumerate(ufs, 1):
        print(f"[{i}/{len(ufs)}] UF: {uf}")
        baixar_pacote_uf(uf, turno=args.turno)

if __name__ == "__main__":
    main()
