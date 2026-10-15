"""
Script para Download dos Dados Oficiais de Comparecimento e Abstenção do TSE.
Baixa o arquivo compactado de 'Detalhe da Apuração por Seção Eleitoral' (detalhe_votacao_secao).
"""

import os
import sys
import argparse
import urllib.request
from pathlib import Path

TSE_DADOS_ABERTOS_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_secao"

def baixar_detalhe_votacao(ano: int = 2022, destino_dir: Path = Path("dados_brutos")) -> Path:
    destino_dir.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"detalhe_votacao_secao_{ano}.zip"
    url = f"{TSE_DADOS_ABERTOS_URL}/{nome_arquivo}"
    caminho_local = destino_dir / nome_arquivo

    print(f"[*] Conectando ao Portal de Dados Abertos do TSE...")
    print(f"URL: {url}")
    print(f"Destino: {caminho_local}")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp, open(caminho_local, "wb") as f_out:
            tamanho = int(resp.headers.get("Content-Length", 0))
            print(f"[*] Tamanho do pacote: {tamanho / (1024**2):.1f} MB")
            baixados = 0
            while True:
                chunk = resp.read(1024 * 512)
                if not chunk:
                    break
                f_out.write(chunk)
                baixados += len(chunk)
                if tamanho > 0:
                    pct = baixados * 100.0 / tamanho
                    print(f"[*] Download: {baixados / (1024**2):.1f} MB ({pct:.1f}%)...", end="\r")
        print(f"\n[+] Download concluído com sucesso: {caminho_local}")
        return caminho_local
    except Exception as e:
        print(f"[-] Erro ao baixar dados do TSE: {e}", file=sys.stderr)
        print("💡 Dica: Se o download direto falhar, você pode baixar o ZIP manualmente no Portal do TSE e executar:", file=sys.stderr)
        print(f"   python pipeline\\abstencao\\consolidar_abstencao.py --arquivo <caminho_do_zip>", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download de Dados de Abstenção do TSE")
    parser.add_argument("--ano", type=int, default=2022, help="Ano da eleição (padrão: 2022)")
    args = parser.parse_args()

    baixar_detalhe_votacao(args.ano)
