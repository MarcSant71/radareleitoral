"""
Módulo de Informações de Versão e Build da Plataforma.
Fonte Única da Verdade (SSOT): resolve dinamicamente a versão e commit
a partir de CHANGELOG.md, version.json e Git.
"""

import re
import json
import subprocess
from pathlib import Path


def _obter_info_versao():
    web_dir = Path(__file__).resolve().parent
    root_dir = web_dir.parent
    version_json = web_dir / "version.json"

    versao = ""
    commit = ""
    data_str = ""

    # 1. Fonte Primária: CHANGELOG.md (SSOT oficial de versionamento)
    for base in (root_dir, web_dir):
        changelog_path = base / "CHANGELOG.md"
        if changelog_path.exists():
            try:
                conteudo = changelog_path.read_text(encoding="utf-8")
                m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]\s*-\s*([0-9-]+)", conteudo, re.MULTILINE)
                if m:
                    versao = m.group(1).strip()
                    data_str = m.group(2).strip()
                    break
            except Exception:
                pass

    # 2. Metadados de Build em Produção: version.json gerado no pipeline
    if version_json.exists():
        try:
            with open(version_json, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if not versao:
                    versao = data.get("versao", "").strip()
                if not data_str:
                    data_str = data.get("data", "").strip()
                commit = data.get("commit", "").strip()
        except Exception:
            pass

    # 3. Resolução do Hash Git (em ambiente local)
    if not commit:
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(root_dir),
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except Exception:
            commit = ""

    if not versao:
        versao = "2.6.0"

    return versao, commit, data_str


VERSAO_APP, COMMIT_APP, DATA_APP = _obter_info_versao()

# Rótulo público limpo para a interface do usuário
VERSAO_DISPLAY = f"Versão {VERSAO_APP}"

# Identificador técnico completo (para logs ou auditoria interna)
VERSAO_BUILD = f"v{VERSAO_APP} ({COMMIT_APP})" if COMMIT_APP else f"v{VERSAO_APP}"
