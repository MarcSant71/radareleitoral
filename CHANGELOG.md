# Changelog — Radar Eleitoral

Todas as alterações notáveis nesta plataforma são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere estritamente ao [Semantic Versioning (SemVer 2.0.0)](https://semver.org/lang/pt-BR/).

---

## [2.8.0] - 2026-10-25

### Adicionado
- **Sincronização Autônoma e Resiliente da CDN Oficial:** Motor de download atômico com validação estrutural de arquivos e detecção instantânea de retotalizações e pacotes republicados pelo TSE.
- **Invalidação Inteligente de Cache:** Reprocessamento automatizado de boletins de urna (BUs) e logs de seções eleitorais cujos pacotes sofreram atualizações oficiais, garantindo convergência com a apuração definitiva.
- **Automação Eficiente de Atualizações:** Fluxo de atualização que dispensa transferências redundantes para a nuvem quando a base local já se encontra 100% íntegra e sincronizada com o TSE.
- **Suporte a Reprocessamento Sob Demanda:** Introdução do parâmetro `--reprocessar` para reavaliação completa de todas as 497.895 seções do país.

### Modificado
- **Experiência Visual de Terminal:** Padronização com limpeza de tela inicial (`cls`) e mensagens operacionais claras em todos os scripts de controle.
- **Governança de Código Legado:** Diretório histórico padronizado para `obsoleto/`, mantido estritamente para consulta fria.

---

## [2.7.2] - 2026-10-17

### Corrigido
- **Dados Oficiais de Abstenção:** Correção no cálculo de eleitores faltosos e comparecimento em todas as 497.895 seções do país, refletindo com exatidão a taxa oficial de abstenção (média de 20,7%) e permitindo análises precisas nos gráficos e no mapa.
- **Estabilidade nos Gráficos e Cálculos:** Eliminação de travamentos ao cruzar horários de votação, biometria e abstenção, garantindo exibição estável mesmo ao filtrar poucas seções.
- **Segurança e Privacidade:** Bloqueio de conexões externas não autorizadas, garantindo que as consultas e filtros do painel funcionem de forma isolada e segura apenas na página oficial.

---

## [2.7.1] - 2026-10-17

### Modificado
- **Otimização Visual do Mapa:** Remoção de banners informativos no mapa para maximizar a área útil de visualização vertical dos colégios e seções eleitorais.
- **Mensagens Institucionais Padronizadas:** Substituição de avisos operacionais por comunicações amigáveis ao usuário final.

---

## [2.7.0] - 2026-10-17

### Adicionado
- **Módulo Geoespacial de Fiscais & Seções:** Mapeamento interativo de 71.118 prédios de votação e 176.946 seções sinalizadas em todo o Brasil para otimização de logística cívica e alocação de fiscais independentes.
- **Gaveta Lateral Flutuante (*In-Map Side Drawer*):** Inspeção rápida de colégios e seções auditadas diretamente no mapa ao clicar em qualquer pino, eliminando a rolagem vertical da página e apresentando diagnósticos, comparecimento e alertas de log com atualização instantânea.
- **Cartografia Aberta e Soberana:** Camadas de mapa 100% livres baseadas em OpenStreetMap (ativada por padrão) e opções em satélite e contraste escuro, sem dependência de serviços externos ou chaves proprietárias.
- **Filtros Granulares de Precisão:** Recorte por Estado (UF), Município, Zona Eleitoral, Nível de Atenção (Alta, Média e Baixa Prioridade) e busca textual por colégio, rua ou CEP.
- **Tabela Analítica & Exportação de Dados:** Listagem estruturada de colégios para auditoria com exportação em formato tabular (CSV) e raio-x detalhado de seções por escola.
- **Metodologia Institucional de Mapeamento:** Documentação didática com critérios de priorização para auxílio a fiscais de votação e conferência cívica.
- **Sincronização Geoespacial de Alta Velocidade:** Otimização no processamento e armazenamento colunar dos locais de votação de todas as 27 Unidades da Federação.

---

## [2.6.0] - 2026-10-17

### Adicionado
- **Identidade Oficial Radar Eleitoral:** Transição da marca para *Radar Eleitoral*, consolidando a plataforma como uma suíte analítica ampla, contínua e multipropósito.
- **Arquitetura Modular Multiferramenta:** Reestruturação da aplicação em módulos analíticos independentes, isolando domínios de auditoria de urnas, análise de abstenção e governança pública.
- **Navegação Semântica por Ferramenta:** Suporte a links diretos para cada ferramenta analítica na URL, facilitando compartilhamento e auditoria colaborativa.
- **Cabeçalho Reativo e Contextual:** Atualização dinâmica de títulos, subtítulos e instruções de acordo com a ferramenta ativa.
- **Padronização de Scripts Operacionais:** Unificação dos comandos de execução local e sincronização da plataforma.

---

## [2.5.0] - 2026-10-16

### Adicionado
- **Motor Modular de Engenharia de Dados:** Reestruturação do pipeline de processamento de dados eleitorais, permitindo execuções modulares, reproduzíveis e resilientes a falhas.
- **Orquestrador Central de Processamento:** Consolidação do fluxo de auditoria em etapas sequenciais padronizadas de download, auditoria de logs, consolidação de BUs e compilação analítica.
- **Detecção Autônoma de Turnos Eleitorais:** Monitoramento contínuo de publicações oficiais para assimilação automática de múltiplos pleitos e turnos eleitorais.
- **Suporte Multiturno no Painel:** Alternância dinâmica de dados por pleito e turno eleitoral, mantendo mensagens informativas durante períodos de apuração.
- **Políticas Estritas de Integridade Operacional:** Implementação de travas de confirmação para prevenir execuções concorrentes ou em ambientes inadequados.

### Modificado
- **Processamento Nacional Completo:** Padronização do processamento em lote cobrindo 100% das 27 Unidades da Federação com verificação incremental de integridade.
- **Comunicação e Feedback de Processamento:** Notificações em tempo real sobre o progresso das etapas de processamento e cálculo dos modelos matemáticos.

---

## [2.4.4] - 2026-10-16

### Adicionado
- **Dimensão Histórica de Pleitos:** Mapeamento determinístico de eleições, pleitos e turnos oficiais, viabilizando análises longitudinais e comparativas.
- **Isolamento de Séries Temporais por Zona:** Segregação e controle de médias zonais por eleição e turno.
- **Controles de Seleção de Pleito:** Interface intuitiva para alternância de ano e turno eleitoral.
- **Unificação de Domínio Institucional:** Consolidação do endereço principal com redirecionamento automático permanente (301) para conexões criptografadas.

---

## [2.4.3] - 2026-10-16

### Adicionado
- **Armazenamento Colunar Analítico:** Introdução de cache colunar de alto desempenho, reduzindo o tempo de carregamento de métricas de 15,7 segundos para sub-segundo (~0,5s).
- **Invalidação Inteligente de Dados:** Atualização automática de índices analíticos somente quando houver novos dados consolidados.

### Modificado
- **Exportação Eficiente Sob Demanda:** Processamento e download de relatórios apenas quando solicitado pelo usuário, preservando largura de banda e memória do navegador.
- **Transições Visuais Aceleradas (*Skeleton Screens*):** Indicadores de carregamento dinâmicos e fluidos que espelham a disposição final de cards e gráficos.
- **Persistência de Navegação:** Retorno instantâneo entre painéis analíticos e documentação sem recarregamentos desnecessários.

---

## [2.4.2] - 2026-10-15

### Adicionado
- **Esqueleto Visual com Animação Acelerada por GPU:** Transições contínuas de interface durante inicialização, prevenindo oscilações de layout.

### Modificado
- **Otimização de Indicadores de Processamento:** Indicadores visuais discretos e contextuais restritos ao módulo em atualização.
- **Refinamento do Painel de Governança:** Otimização vertical de textos e controles na central de transparência.

---

## [2.4.1] - 2026-10-15

### Adicionado
- **Vetorização Numérica Forense:** Aceleração de rotinas matemáticas e regras de triagem estatística, aumentando a velocidade de renderização em mais de 90%.
- **Otimização de Agregação no Servidor:** Pré-agregação de matrizes temporais de votação, reduzindo o tráfego de dados para o cliente em 99,8%.

### Modificado
- **Renderização Gráfica Avançada:** Calibração na amostragem gráfica multivariada para máxima fluidez em computadores e dispositivos móveis.

---

## [2.4.0] - 2026-10-15

### Adicionado
- **Módulo Analítico de Abstenção & Comparecimento:** Implementação completa da suíte de auditoria de abstenção com modelo de Funil de Spiegelhalter (2005) e limites paramétricos de controle a 95% e 99,8%.
- **Matriz de 21 KPIs (3x7):** Métricas consolidadas em nível nacional, regional, estadual e municipal sobre 152 milhões de eleitores aptos e 497.895 seções.
- **7 Abas Analíticas Especializadas:** Módulos de *Comparar*, *Distribuição*, *Funil*, *Sinalizadas*, *Horário dos Votos*, *Sem Digital* e *Cruzamento Bivariado*.
- **Central de Governança Pública & LGPD:** Tela dedicada de transparência com termos da LGPD, criptografia e histórico evolutivo da plataforma.

---

## [2.3.0] - 2026-10-15

### Adicionado
- **Metodologia Científica Acessível:** Reformulação didática dos conceitos matemáticos com explicações intuitivas sobre desvios padrão, superdispersão e baselines.
- **Ajuda Contextual Flutuante:** Tooltips explicativos de alto contraste integrados a controles, gráficos e tabelas.

---

## [2.2.0] - 2026-10-14

### Adicionado
- **Visualização Dual de Distribuição:** Alternância instantânea entre visão intuitiva (*Faixas de Atenção Forense*) e detalhamento técnico (*Histograma Contínuo*).
- **Calibração Visual Multivariada:** Enquadramento calibrado no 99,5º percentil estatístico, prevenindo distorções visuais provocadas por casos atípicos extremos.

---

## [2.1.0] - 2026-10-14

### Adicionado
- **Motor Estatístico de Spiegelhalter (2005):** Inferência matemática rigorosa baseada em desvios padronizados (*Z-scores* multivariados em sigmas σ).
- **Técnica Leave-One-Out Municipal:** Cálculo da média esperada excluindo a própria seção avaliada para eliminação de viés amostral.
- **Ajuste de Superdispersão Residual ($\tau^2$):** Calibração de variância intra-estadual via Median Absolute Deviation (MAD).

---

## [2.0.0] - 2026-10-13

### Adicionado
- **Auditoria Nacional Consolidada:** Processamento unificado dos 497.895 Boletins de Urna (BUs) e logs de eventos do TSE em todas as 27 Unidades Federativas.
- **Armazenamento de Alta Performance:** Estrutura de banco de dados otimizada para consultas simultâneas de alta velocidade com baixo consumo de memória.
- **Modo Escuro / Claro:** Suporte completo à alternância de paletas visuais de alto contraste.

---

## [1.0.0] - 2026-10-11

### Adicionado
- **Versão Inicial:** Protótipo exploratório de consolidação de dados públicos abertos do TSE e triagem preliminar de seções eleitorais.
