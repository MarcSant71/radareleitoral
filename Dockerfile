FROM python:3.11-slim

WORKDIR /app

# Otimizações de runtime em contêiner
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8501

# Dependências mínimas de SO
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala pacotes Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import streamlit, pathlib; p = pathlib.Path(streamlit.__file__).parent / 'static' / 'index.html'; content = p.read_text(encoding='utf-8'); gtag = '''<head>\n    <!-- Google tag (gtag.js) -->\n    <script async src=\"https://www.googletagmanager.com/gtag/js?id=G-E9VZG8RQ81\"></script>\n    <script>\n      window.dataLayer = window.dataLayer || [];\n      function gtag(){dataLayer.push(arguments);}\n      gtag(\x27js\x27, new Date());\n\n      gtag(\x27config\x27, \x27G-E9VZG8RQ81\x27, { \x27anonymize_ip\x27: true });\n    </script>'''; og = '''<title>Radar Eleitoral - Inteligência Analítica e Auditoria de Urnas</title><meta property=\"og:image\" content=\"https://eleicao.dominiodigital.dev.br/og_preview.png\"><meta property=\"og:image:width\" content=\"1200\"><meta property=\"og:image:height\" content=\"630\"><meta name=\"description\" content=\"Radar Eleitoral - Plataforma independente de inteligência analítica, ciência de dados e auditoria forense das urnas eletrônicas oficiais do TSE.\"><meta property=\"og:title\" content=\"Radar Eleitoral - Inteligência Analítica e Auditoria de Urnas\"><meta property=\"og:description\" content=\"Radar Eleitoral - Plataforma independente de inteligência analítica, ciência de dados e auditoria forense das urnas eletrônicas oficiais do TSE.\"><meta property=\"og:type\" content=\"website\"><meta property=\"og:url\" content=\"https://eleicao.dominiodigital.dev.br/\"><meta property=\"og:site_name\" content=\"Radar Eleitoral\">'''; content = content.replace('<head>', gtag, 1).replace('<title>Streamlit</title>', og); p.write_text(content, encoding='utf-8')"

# Copia estrutura da aplicação
COPY web/ web/
COPY db/ db/
COPY .streamlit/ .streamlit/
COPY CHANGELOG.md .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
