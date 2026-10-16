"""
Ponto de Entrada Mestre do Pacote Pipeline — Eleições 2026.
Permite executar: python -m pipeline [opções]
"""

import sys
from pathlib import Path

_root_dir = Path(__file__).resolve().parent.parent
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from pipeline.orquestrador import main

if __name__ == "__main__":
    main()
