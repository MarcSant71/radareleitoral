"""
Módulo de Consolidação de Boletins de Urna (BUs) & Zonas — Pipeline Eleições 2026.
Decodifica arquivos ASN.1 (-bu.dat) e consolida totais por seção e zonas eleitorais.

Pode ser executado diretamente via CLI:
    python -m pipeline.consolidar --uf AC
    python -m pipeline.consolidar --todas
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

from pipeline.consolidar_bu import (
    processar_pacote_uf,
    atualizar_zonas_totais,
    main as consolidar_main
)

def main():
    consolidar_main()

if __name__ == "__main__":
    main()
