# Changelog — Radar Eleitoral

Todas as alterações notáveis nesta plataforma são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere estritamente ao [Semantic Versioning (SemVer 2.0.0)](https://semver.org/lang/pt-BR/).

---

## [2.7.0] - 2026-10-17

### Adicionado
- **Módulo Geoespacial de Fiscais & Seções (`web/modulos/mapa.py`):**
  - Mapeamento interativo de **71.118 prédios de votação** e **176.946 seções sinalizadas** em todo o Brasil.
  - Renderização geoespacial com Leaflet 1.9.4 e MarkerCluster via `st.iframe` sem dependências pesadas de backend.
  - **Gaveta Lateral Flutuante (*In-Map Side Drawer*):** Inspeção ágil de colégios e seções auditadas diretamente sobre o mapa ao clicar em qualquer pino (experiência idêntica ao `brasil.arvor.co`), eliminando rolagem vertical e exibindo diagnósticos, métricas de comparecimento, percentuais e alertas de log sem latência de backend.
  - Camadas de mapa 100% livres com OpenStreetMap ativado por padrão e seletor com suporte a Esri Dark Canvas e Satélite (zero dependência de Google ou chaves de API).
  - Filtros granulares por UF, Município, Zona Eleitoral, Nível de Prioridade (Alta, Média, Baixa) e Busca Textual por Colégio, Rua, Bairro ou CEP.
  - Tabela analítica com exportação em CSV sob demanda (`UTF-8 com BOM`) e visualizador com raio-x detalhado de seções e alertas de log por prédio escolar.
  - Documentação didática com Metodologia e Critérios de Mapeamento Georreferenciado para orientação de fiscais de urna.
- **Pipeline de Ingestão e Cache Geoespacial (`pipeline/ingestao_locais.py`):**
  - Download paralelo dos dados de locais das 28 UFs e geração de cache colunar Parquet (`locais_votacao.parquet` e `locais_secoes.parquet`).
  - Integração no `scripts/subirproducao.ps1` para sincronização ultrarrápida com a VPS.

---

## [2.6.0] - 2026-10-17

### Adicionado
- **Identidade Oficial Radar Eleitoral:** Transição da marca para *Radar Eleitoral*, desacoplando a ferramenta de um ano fixo e preparando a plataforma como uma suíte analítica ampla e multipropósito.
- **Arquitetura Modular e Desacoplada (`web/`):**
  - **Orquestrador Central (`web/app.py`):** Ponto de entrada canônico da aplicação Streamlit.
  - **Módulos Analíticos (`web/modulos/`):** Ferramentas isoladas por domínio (`auditoria.py`, `abstencao.py`, `governanca.py`).
  - **Motores Matemáticos (`web/motores/`):** Modelos de inferência de Spiegelhalter (2005) e superdispersão residual (`estatistica.py`).
  - **Camada de Dados e Cache (`web/dados/`):** Conexão SQLite WAL com pooling e carregamento analítico colunar Parquet (`db.py`, `carregador.py`).
- **Roteamento Semântico por Ferramenta na URL:** Substituição da chave legada por `?ferramenta=abstencao`, `?ferramenta=auditoria` e `?ferramenta=governanca`.
- **Cabeçalho Reativo e Dinâmico:** Sincronização em tempo real do título e subtítulo da página de acordo com a ferramenta ativa na barra lateral.
- **Scripts Operacionais Intuitivos:** Renomeação de scripts na pasta `scripts/` para `subirproducao.ps1` e `rodarlocal.cmd`.

---

## [2.5.0] - 2026-10-16

### Adicionado
- **Pacote Modular de Engenharia de Dados (`pipeline/`):** Transformação da pasta `pipeline/` em pacote Python canônico (`__init__.py`, `__main__.py`), resolvendo a inversão de dependência histórica e permitindo execução modular via CLI (`python -m pipeline.db`, `python -m pipeline.baixar`, `python -m pipeline.consolidar`, `python -m pipeline.compilar`).
- **Orquestrador Mestre Unificado (`iniciar_banco.py` e `python -m pipeline`):** Consolidação de todo o pipeline de dados em 5 etapas sequenciais e reproduzíveis (`--uf`, `--turno`, `--ano`, `--threads`, `--zerar`, `--pular-download`).
- **Detecção Autônoma de Turnos Eleitorais:** O orquestrador agora sonda dinamicamente os pacotes locais e a CDN oficial do TSE via HTTP HEAD sentinela. Quando o TSE publicar os pacotes do 2º Turno, o pipeline ingere ambos os pleitos de forma autônoma sem requerer alterações de código.
- **Suporte Multiturno Dinâmico no Painel Web (`web/painel.py`):** O seletor de turno agora chaveia dinamicamente para os dados do 2º Turno assim que presentes no dataset compilado, mantendo a mensagem institucional de apuração caso ainda não publicados.
- **Travas de Segurança Operacional & Anti-Produção:** Banner de governança com quatro alertas mandatórios (download massivo de 25-30 GB por turno, reset relacional, trava estrita contra execução em VPS de produção e estimativa realista de tempo de processamento de 30 a 50 minutos).

### Modificado
- **Confirmação Estrita de Governança (`SIM`):** Exigência estrita da string `"SIM"` em maiúsculo no prompt interativo, rejeitando variações (`sim`, `s`, `yes`) para evitar disparos acidentais.
- **Governança "Tudo ou Nada":** Remoção do menu interativo de seleção de UF única. Para assegurar integridade estatística nacional, o padrão do pipeline executa as 27 UFs com checagem incremental instantânea (`Arquivo já processado`), reservando a flag `--uf <SIGLA>` exclusivamente para depuração técnica via CLI.
- **Identidade Visual Unificada & UX de Terminal no Pipeline:** Limpeza do banner inicial (remoção da linha redundante "Alvo:", exibindo o Pleito consolidado) e padronização do feedback em tempo real (`\r`) em todas as etapas (`Baixando`, `Auditando`, `Consolidando`), com supressão de heurísticas arbitrárias no terminal e cálculo estatístico formal exclusivo de Spiegelhalter (2005) na geração do Parquet.

---

## [2.4.4] - 2026-10-16

### Adicionado
- **Tabela Dimensão de Pleitos (`pleitos`):** Criação da tabela relacional no SQLite para mapeamento determinístico de código oficial do TSE (`03220`), ano (`2026`) e turno (`1`), desacoplando o código de constantes estáticas e preparando a base para múltiplos pleitos.
- **Normalização de Zonas Eleitorais:** Reestruturação da chave primária de `zonas_totais` para `(pleito, uf, zona)`, isolando estatísticas entre turnos e eleições.
- **Seletor de Eleição & Turno:** Controles de navegação na barra lateral para chaveamento de ano e turno com mensagem informativa para apurações futuras.
- **Unificação de Domínio:** Configuração do domínio principal `eleicao.dominiodigital.dev.br` com suporte a redirecionamento permanente (301) do domínio legado no Caddy.

---

## [2.4.3] - 2026-10-16

### Adicionado
- **Armazenamento Colunar Parquet (`eleicoes2026.parquet`):** Cache analítico de alta performance integrado ao `carregar_dados()`, reduzindo o tempo de carga analítica de 15,7s para sub-segundo (~0,5s) no cold start.
- **Invalidação Inteligente de Cache:** Verificação automática de integridade por timestamp (`mtime`), regenerando o cache colunar apenas quando o banco relacional SQLite sofrer modificações.
- **Dependência Explícita do PyArrow:** Inclusão de `pyarrow>=14.0.0` no `requirements.txt`.

### Modificado
- **Geração Sob Demanda de CSV:** Exportação de dados via *deferred callable* no `st.download_button`, eliminando o processamento antecipado de 82MB e o bloqueio de tráfego WebSocket na montagem da tela.
- **Sincronização do Skeleton Screen:** Reordenação geométrica do esqueleto de carga (*Ghost*) com efeito *shimmer*, espelhando a disposição real de abas superiores, cards de KPI e gráficos.
- **Navegação Persistente:** Otimização do fluxo de retorno entre a metodologia e o painel analítico com reutilização de estado em memória sem disparo de spinners repetidos.

---

## [2.4.2] - 2026-10-15

### Adicionado
- **Skeleton Screen com Animação Shimmer (GPU Accelerated):** Gradiente pulsante via pseudo-elemento `::after` e aceleração por hardware (`transform: translateX`), eliminando telas brancas e mantendo animação contínua no carregamento inicial.

### Modificado
- **Supressão de Indicadores Redundantes:** Desacoplamento de spinners globais no orquestrador `painel.py`, delegando indicadores de processamento exclusivamente para o nível de cada painel.
- **Polimento da Central de Governança:** Otimização vertical de layouts e eliminação de controles redundantes no modal de conformidade.

---

## [2.4.1] - 2026-10-15

### Adicionado
- **Vetorização Numérica Forense:** Vetorização de rotinas de triagem e regras de corte estatístico via NumPy, acelerando a renderização em mais de 90%.
- **Agregação Server-Side:** Pré-agregação de matrizes temporais de votação no servidor, reduzindo o tráfego do payload em 99,8%.

### Modificado
- **Amostragem Otimizada de Dispersão:** Otimização na amostragem e renderização WebGL do gráfico bivariado multivariado para resposta instantânea em servidores de produção.

---

## [2.4.0] - 2026-10-15

### Adicionado
- **Módulo Analítico de Abstenção & Comparecimento:** Implementação completa da suíte de auditoria de abstenção com modelo de Funil de Spiegelhalter (2005) e limites paramétricos de controle a 95% e 99,8%.
- **Matriz de 21 KPIs (3x7):** Métricas consolidadas em nível nacional, regional, estadual e municipal sobre 152 milhões de eleitores aptos e 497.895 seções.
- **7 Abas Analíticas Especializadas:** Módulos de *Comparar* (Forest Plot), *Distribuição*, *Funil*, *Sinalizadas* (Matriz Forense), *Horário dos Votos*, *Sem Digital* e *Cruzamento* bivariado.
- **Central Dedicada de Governança Pública:** Tela autônoma com termos da LGPD, criptografia, fontes de dados e histórico evolutivo de versões.

---

## [2.3.0] - 2026-10-15

### Adicionado
- **Didática Forense e Metodologia Acessível:** Reformulação da metodologia científica com analogias conceituais acessíveis (MAD, termômetro do *Z-score*, Teorema de Pitágoras e Norma Euclidiana $L_2$ multivariada).
- **Tooltips Flutuantes BaseWeb:** Subsistema de ajuda contextual flutuante de alto contraste com suporte universal para cards, controles e tabelas (`st.dataframe`).

---

## [2.2.0] - 2026-10-14

### Adicionado
- **Visualização Dual de Distribuição:** Seletor dinâmico entre visualização intuitiva (*Faixas de Risco Forense*) e detalhamento técnico (*Histograma Contínuo* até 12σ).
- **Calibração de Viewport Multivariado:** Enquadramento dinâmico calibrado no 99,5º percentil estatístico, evitando dispersão visual de casos extremos.

---

## [2.1.0] - 2026-10-14

### Adicionado
- **Motor Estatístico de Spiegelhalter (2005):** Inferência matemática rigorosa baseada em desvios padronizados (*Z-scores* multivariados em sigmas σ).
- **Técnica Leave-One-Out Municipal:** Cálculo da média esperada excluindo a própria seção avaliada para eliminação de viés amostral.
- **Estimativa de Superdispersão Residual ($\tau^2$):** Ajuste de dispersão intra-UF via Median Absolute Deviation (MAD).

---

## [2.0.0] - 2026-10-13

### Adicionado
- **Auditoria Nacional Consolidada:** Processamento paralelo e decodificação ASN.1 dos 497.895 Boletins de Urna (BUs) e logs de eventos do TSE em todas as 27 Unidades Federativas.
- **Arquitetura SQLite WAL:** Suporte a consultas concorrentes de alta velocidade com baixo consumo de memória.
- **Modo Escuro / Claro Nativo:** Suporte completo à alternância de paletas científicas de alto contraste.

---

## [1.0.0] - 2026-10-11

### Adicionado
- **Versão Inicial:** Protótipo exploratório de extração de dados abertos do TSE e ranking forense preliminar.
