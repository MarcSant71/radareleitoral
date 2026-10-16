# Changelog — Eleições 2026

Todas as alterações notáveis nesta plataforma são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere estritamente ao [Semantic Versioning (SemVer 2.0.0)](https://semver.org/lang/pt-BR/).

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
