# 🗳️ Auditoria Eleições 2026 — Plataforma de Análise Forense e Estatística

Plataforma pública e independente de auditoria, análise estatística e visualização forense dos dados oficiais das urnas eletrônicas do Tribunal Superior Eleitoral (TSE).

O projeto é guiado pelo princípio da **total transparência e reprodutibilidade**: todo o código de extração, decodificação ASN.1 dos Boletins de Urna (BU) e análise cronológica de logs das urnas está aberto para que peritos, universidades, partidos e cidadãos possam auditar e reproduzir as análises de forma independente.

---

## 📌 Funcionalidades Principais

* **Análise Forense Temporal:** Mapeamento segundo a segundo de cada voto depositado em cada urna do país, identificando votos registrados após as 17:00 (encerramento regulamentar).
* **Auditoria de Habilitação do Eleitor:** Métricas de biometria com sucesso vs. liberação manual pelo mesário (código de habilitação manual) e sua correlação com horários estendidos.
* **Indicador de Ociosidade e Cadência:** Cálculo da taxa de fluxo (segundos por eleitor) e detecção de ociosidades anômalas antes das 17:00 seguidas de picos atípicos.
* **Motor Estatístico de Spiegelhalter (2005):** Inferência matemática rigorosa com Z-scores ajustados para superdispersão residual (tau² via MAD) e baselines municipais calculados via Leave-One-Out.
* **Mapa Interativo e Filtros Dinâmicos:** Navegação geográfica por Região, Estado (UF), Município, Zona e Seção eleitoral.
* **Exportação Completa:** Download dos dados filtrados em CSV ou visualização detalhada de cada urna com links diretos de auditoria.

---

## 🏗️ Arquitetura do Repositório

O projeto é estruturado com clara separação entre a plataforma de visualização em produção e o motor de auditoria de dados:

```text
Eleicao2026/
│
├── web/                       # [PRODUÇÃO] Aplicação web servida ao público
│   ├── painel.py              # Interface analítica completa em Streamlit (v2.2.0)
│   ├── estatistica.py         # Motor de inferência estatística de Spiegelhalter (2005)
│   └── db.py                  # Camada de conexão e consultas SQLite otimizada com WAL
│
├── pipeline/                  # [MOTOR DE AUDITORIA] Scripts de extração do TSE
│   ├── baixar_pacote.py       # Download paralelo dos pacotes oficiais da CDN do TSE
│   ├── auditar.py             # Parser forense de eventos de logs das urnas (.jez)
│   ├── consolidar_bu.py       # Decodificador multithread de Boletins de Urna (.dat)
│   ├── bu_parser.py           # Parser da especificação ASN.1 oficial do TSE
│   ├── log_parser.py          # Extrator determinístico de eventos e timestamps
│   ├── downloader.py          # Utilitário HTTP resiliente com suporte a Range requests
│   ├── tse_spec.js            # Especificação JavaScript auxiliar do protocolo TSE
│   └── municipios/            # Base de dados de correlação de municípios (TSE x IBGE)
│
├── .streamlit/                # Configurações de tema, porta e renderização
├── Caddyfile                  # Configuração de Proxy Reverso HTTPS (Caddy Server)
├── Dockerfile                 # Contêiner Docker otimizado para o Streamlit
├── docker-compose.yml         # Orquestração do ambiente de produção
├── requirements.txt           # Dependências Python do ecossistema
└── README.md                  # Este documento
```

---

## 🔬 Metodologia e Reprodutibilidade

Todo o banco de dados consumido pela aplicação web é gerado de forma 100% determinística a partir dos dados abertos disponibilizados pelo TSE.

### Fontes Oficiais
Os pacotes de dados brutos são obtidos diretamente dos endpoints da CDN de Dados Abertos do TSE:
`https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/`

### Como Auditar e Gerar a Base Localmente

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/MarcSant71/eleicoes2026.git
   cd eleicoes2026
   ```

2. **Crie um ambiente virtual e instale as dependências:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Baixe os pacotes oficiais de uma ou todas as UFs:**
   ```bash
   # Exemplo para a Bahia (BA) ou use --todas
   python pipeline/baixar_pacote.py --uf BA
   ```

4. **Audite os logs de eventos e horários:**
   ```bash
   python pipeline/auditar.py --threads 16
   ```

5. **Consolide os Boletins de Urna (BUs):**
   ```bash
   python pipeline/consolidar_bu.py --threads 16
   ```

Os scripts processam os arquivos brutos e criam automaticamente o banco local indexado `db/eleicoes2026.db`.

---

## 🚀 Como Rodar o Painel Web

Após ter o banco de dados gerado (ou fornecido):

```bash
streamlit run web/painel.py
```

O painel será aberto automaticamente no navegador em `http://localhost:8501`.

---

## 🐳 Executando com Docker em Produção

O projeto conta com deploy em contêineres gerenciado via Docker Compose e Caddy como terminação SSL:

```bash
docker compose up -d --build
```

---

## ⚖️ Isenção de Responsabilidade e Termos de Uso

Este projeto tem caráter estritamente acadêmico, científico e cidadão. Não possui vínculo partidário nem institucional com o Tribunal Superior Eleitoral. As conclusões estatísticas e análises forenses são baseadas unicamente na matemática dos eventos registrados nas urnas e disponibilizados pelo próprio órgão eleitoral para consulta pública (Lei de Acesso à Informação — Lei nº 12.527/2011).
