"""
Módulo de Informações de Versão e Build da Plataforma.
Fonte Única da Verdade (SSOT): resolve dinamicamente a versão e commit
a partir de version.json (produção), CHANGELOG.md e Git local.
"""

import re
import json
import subprocess
from pathlib import Path

def _obter_info_versao():
    web_dir = Path(__file__).resolve().parent
    root_dir = web_dir.parent
    version_json = web_dir / "version.json"
    
    # 1. Prioridade em Produção (Docker): version.json gerado no pipeline de deploy
    if version_json.exists():
        try:
            with open(version_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                v = data.get("versao", "").strip()
                c = data.get("commit", "").strip()
                d = data.get("data", "").strip()
                if v:
                    return v, c, d
        except Exception:
            pass

    # 2. Resolução Dinâmica Local: lê a versão mais recente diretamente do CHANGELOG.md
    versao = "2.4.4"
    data_str = ""
    changelog_path = root_dir / "CHANGELOG.md"
    if changelog_path.exists():
        try:
            conteudo = changelog_path.read_text(encoding="utf-8")
            m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]\s*-\s*([0-9-]+)", conteudo, re.MULTILINE)
            if m:
                versao = m.group(1).strip()
                data_str = m.group(2).strip()
        except Exception:
            pass

    # 3. Resolução Dinâmica do Commit via Git
    commit = ""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root_dir),
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        commit = ""

    return versao, commit, data_str

VERSAO_APP, COMMIT_APP, DATA_APP = _obter_info_versao()

# Rótulo público limpo para a interface do usuário
VERSAO_DISPLAY = f"Versão {VERSAO_APP}"

# Identificador técnico completo (para logs ou auditoria interna)
VERSAO_BUILD = f"v{VERSAO_APP} ({COMMIT_APP})" if COMMIT_APP else f"v{VERSAO_APP}"
