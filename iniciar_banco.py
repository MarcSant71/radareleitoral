"""
Orquestrador Mestre de Inicialização e Carga do Banco de Dados — Eleições 2026.
Atalho direto para o pacote modular de dados (equivalente a: python -m pipeline).
"""

import sys
from pathlib import Path

_root_dir = Path(__file__).resolve().parent
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from pipeline.__main__ import main

if __name__ == "__main__":
    main()
