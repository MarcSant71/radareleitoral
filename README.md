# 🗳️ Eleições 2026 — Ciência de Dados & Estatística Eleitoral

[![Versão](https://img.shields.io/badge/versão-v2.4.4-blue.svg)](CHANGELOG.md)
[![Licença](https://img.shields.io/badge/licença-MIT-green.svg)](LICENSE)
[![Base Oficial](https://img.shields.io/badge/dados-TSE%20Oficial-yellow.svg)](https://dadosabertos.tse.jus.br/)

Plataforma pública e independente de ciência de dados, análise estatística e visualização quantitativa dos dados oficiais das urnas eletrônicas do Tribunal Superior Eleitoral (TSE) — cobrindo **152 milhões de eleitores** e **497.895 seções eleitorais** em todas as 27 Unidades Federativas.

O projeto é guiado pelo princípio da **total transparência e reprodutibilidade**: todo o código de extração, decodificação ASN.1 dos Boletins de Urna (BU) e análise cronológica de logs das urnas está aberto para que peritos, universidades, partidos e cidadãos possam auditar e reproduzir as análises de forma independente.

---

## 📌 Funcionalidades Principais

* **🗳️ Auditoria Forense Temporal:** Mapeamento segundo a segundo de cada voto depositado em cada urna do país, identificando votos registrados após as 17:00 (encerramento regulamentar).
* **📉 Suíte Analítica de Abstenção & Comparecimento:** Matriz de 21 KPIs (3x7) e 7 abas analíticas integradas (*Comparar*, *Distribuição*, *Funil de Spiegelhalter com faixas 95% e 99.8%*, *Seções Sinalizadas*, *Horário dos Votos*, *Sem Digital* e *Cruzamento Bivariado*).
* **🖐️ Auditoria Biométrica e Liberação Manual:** Decomposição da habilitação do eleitor (Biometria com Sucesso vs. Liberação Manual com código de mesário) e sua correlação com fechamentos tardios.
* **🔬 Motor Estatístico de Spiegelhalter (2005):** Inferência matemática rigorosa com *Z-scores* ajustados para superdispersão residual ($\tau^2$ via MAD) e baselines municipais calculados via *Leave-One-Out*.
* **⚡ Armazenamento Colunar de Alta Performance:** Cache colunar pré-calculado em formato Parquet com invalidação inteligente por timestamp, permitindo carregamento analítico em **sub-segundo (~0,5s)**.
* **🧭 Experiência Dual de Distribuição:** Alternância dinâmica instantânea entre visualização intuitiva (*Faixas de Risco Forense*) e técnica (*Histograma Contínuo* até 12σ).
* **📥 Exportação Sob Demanda:** Download de relatórios completos em CSV com geração diferida (*deferred execution*), sem onerar a memória ou causar travamentos de rede.
* **⚖️ Central de Governança Pública & LGPD:** Tela dedicada de transparência com termos de uso, conformidade com a LGPD (Lei nº 13.709/2018) e histórico de versões.

---

## 🏗️ Arquitetura do Repositório

O projeto é estruturado com separação estrita entre a camada de apresentação web, o motor de auditoria de dados e os scripts operacionais:

```text
Eleicao2026/
│
├── web/                       # [PRODUÇÃO] Plataforma analítica Streamlit
│   ├── painel.py              # Orquestrador central e roteador de navegação (v2.4.3)
│   ├── painel_auditoria.py    # Auditoria de urnas, horários, biometria e ranking forense
│   ├── painel_abstencao.py    # Suíte analítica de abstenção & comparecimento (21 KPIs + 7 abas)
│   ├── painel_governanca.py   # Governança pública, conformidade LGPD e histórico de versões
│   ├── estatistica.py         # Motores matemáticos de Spiegelhalter (2005) e Bayes empírico
│   └── db.py                  # Camada de conexão e consultas SQLite otimizada com WAL
│
├── pipeline/                  # [MOTOR DE AUDITORIA] Scripts de extração e parsing do TSE
│   ├── baixar_pacote.py       # Download paralelo dos pacotes oficiais da CDN do TSE
│   ├── auditar.py             # Parser forense de eventos de logs das urnas (.jez)
│   ├── consolidar_bu.py       # Decodificador multithread de Boletins de Urna (.dat)
│   ├── bu_parser.py           # Parser da especificação ASN.1 oficial do TSE
│   ├── log_parser.py          # Extrator determinístico de eventos e timestamps de votação
│   ├── downloader.py          # Utilitário HTTP resiliente com suporte a Range requests
│   └── tse_spec.js            # Especificação JavaScript auxiliar do protocolo do TSE
│
├── scripts/                   # [OPERAÇÃO LOCAL & DEPLOY]
│   ├── painel.cmd             # Inicializador local do painel Streamlit com ambiente virtual
│   ├── atualizar_dados.cmd    # Sincronização automatizada da base de dados local
│   └── deploy.ps1             # Pipeline de empacotamento, SCP e deploy remoto na VPS Hetzner
│
├── db/                        # [BASE DE DADOS] (Não rastreado no git / Gerado localmente)
│   ├── eleicoes2026.db        # Banco de dados relacional SQLite WAL
│   └── eleicoes2026.parquet   # Cache colunar analítico de alta performance
│
├── .streamlit/                # Configurações de tema, porta e renderização
├── Caddyfile                  # Configuração de Proxy Reverso HTTPS (Caddy Server com OWASP)
├── Dockerfile                 # Contêiner Docker otimizado para o Streamlit (Python 3.11-slim)
├── docker-compose.yml         # Orquestração do ambiente de produção
├── requirements.txt           # Dependências Python (Streamlit, Pandas, Plotly, PyArrow)
├── CHANGELOG.md               # Histórico detalhado de versões (SemVer 2.0.0)
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

### Execução Direta via Script (Windows)
Basta executar o atalho incluído na pasta `scripts`:
```cmd
.\scripts\painel.cmd
```

### Execução Manual via Terminal
```bash
streamlit run web/painel.py
```
O painel abrirá automaticamente no navegador em `http://localhost:8501`.

---

## 🐳 Executando com Docker em Produção

O projeto conta com deploy em contêineres gerenciado via Docker Compose e Caddy como terminação SSL:

```bash
docker compose up -d --build
```

Para automatizar a promoção para servidores remotos (VPS), utilize o playbook PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -ServerIp "<IP_DO_SERVIDOR>"
```

---

## 🏷️ Histórico de Versões

O histórico completo de versões e entregas de engenharia é documentado no [CHANGELOG.md](CHANGELOG.md) e pode ser visualizado na própria plataforma clicando no ícone **(?)** no canto superior direito da tela.

---

## ⚖️ Isenção de Responsabilidade e Termos de Uso

Este projeto tem caráter estritamente acadêmico, científico e cidadão. Não possui vínculo partidário nem institucional com o Tribunal Superior Eleitoral. As conclusões estatísticas e análises forenses são baseadas unicamente na matemática dos eventos registrados nas urnas e disponibilizados pelo próprio órgão eleitoral para consulta pública (Lei de Acesso à Informação — Lei nº 12.527/2011).
