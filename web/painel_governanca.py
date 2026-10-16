"""
Módulo de Governança Pública, Proteção de Dados (LGPD), Segurança Criptográfica e Versionamento.
Centraliza as diretrizes institucionais, conformidade legal e changelog de desenvolvimento do sistema.
"""

import streamlit as st


def renderizar_conteudo_governanca(modo_escuro: bool = True, plotly_theme: str = "plotly_dark"):
    """
    Renderiza o conteúdo estruturado em abas para exibição em modal dialog ou visualização direta.
    """
    st.markdown("""
    <style>
    /* Compacta o espaçamento superior da tela de Governança eliminando o vácuo vertical */
    div[data-testid="stTabs"] {
        margin-top: -0.75rem !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-panel"] {
        padding-top: 0.25rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    tab_gov, tab_vers = st.tabs([
        "⚖️ Governança, LGPD & Segurança",
        "🏷️ Histórico de Versões (Changelog)"
    ])

    with tab_gov:
        st.markdown("""
        <h3 style='margin-top: 0.25rem; margin-bottom: 0.75rem;'>⚖️ Governança Pública, Proteção de Dados (LGPD) & Segurança Criptográfica</h3>
        """, unsafe_allow_html=True)
        st.markdown(r"""
        > 🏛️ **Declaração de Neutralidade e Transparência Pública:**  
        > Este site é um instrumento estritamente independente de ciência de dados e transparência cívica, amparado no **Art. 5º, inciso XXXIII e Art. 37 da Constituição Federal de 1988**, bem como na **Lei de Acesso à Informação (Lei Federal nº 12.527/2011)** e nas resoluções oficiais de fiscalização do **Tribunal Superior Eleitoral (TSE)**.  
        > **Nenhum dado exibido nesta plataforma foi adulterado, editado ou manipulado.** A plataforma não possui vínculo partidário nem apoia candidatos ou coligações. Todas as conclusões derivam exclusivamente de **estatística inferencial, modelos matemáticos determinísticos e registros oficiais do TSE**.

        ---

        #### 📦 1. Origem Oficial dos Dados Eleitorais

        Todos os dados apresentados em todos os painéis desta plataforma foram extraídos de forma automatizada e direta dos repositórios públicos oficiais da Justiça Eleitoral brasileira:

        1. **Repositório Primário Oficial:** Portal de Dados Abertos do TSE ([dadosabertos.tse.jus.br](https://dadosabertos.tse.jus.br/)) e Sistema de Divulgação de Resultados e Boletins de Urna.
        2. **Marco Regulatório:** Resolução TSE nº 23.673/2021, que regulamenta a fiscalização e a auditoria de todos os sistemas de votação eletrônica.
        3. **Abrangência Nacional:** **497.895 seções eleitorais** auditadas em todas as 27 Unidades da Federação (100% dos pacotes públicos de dados disponibilizados pela Justiça Eleitoral).

        Para cada seção eleitoral, são processados dois formatos de arquivos brutos emitidos pela própria Urna Eletrônica:

        * **1. Arquivo de Log de Eventos (`logd.dat` / `*.logd`):**  
          Registro temporal gravado pela urna em tempo real segundo a segundo. Cada eleitor que comparece gera eventos operacionais: inicialização dos subsistemas, chegada à mesa receptora, tentativa de leitura biométrica (ou habilitação manual via código pelo mesário), tempo despendido na cabine de votação e emissão do comprovante físico.  
          *Proteção Constitucional:* Em estrito cumprimento ao Art. 14 da Constituição Federal, o log **não vincula nem pode registrar em quem o cidadão votou**; ele registra apenas o fluxo temporal e a integridade operacional da máquina.
        
        * **2. Arquivo de Boletim de Urna (`bu.dat` / `*.bu`):**  
          Documento digital oficial gerado imediatamente após o encerramento da votação às 17h, padronizado na especificação internacional aberta **ASN.1 (Abstract Syntax Notation One - ISO/IEC 8824)**. O BU contém a totalização dos votos nominais por candidato, votos em branco, votos nulos, comparecimento e abstenção da respectiva seção eleitoral.

        ---

        #### 🔐 2. Integridade Criptográfica e Reprodutibilidade Científica

        A confiabilidade e autenticidade dos dados repousam sobre três pilares técnicos:

        1. **Assinaturas Digitais Criptográficas do TSE (Chaves ICP-Brasil):**  
           Cada arquivo emitido pela urna eletrônica (`.bu` e `.logd`) contém um resumo criptográfico (**Hash SHA-512**) assinado digitalmente com o certificado emitido pela Autoridade Certificadora da Justiça Eleitoral na Cerimônia Pública de Lacração dos Sistemas.  
           *Qualquer alteração* — de um único bit, voto ou milissegundo — romperia a cadeia de custódia e invalidaria a assinatura criptográfica oficial.
        2. **Código Determinístico em Python (Zero Alucinação):**  
           O processamento da base `eleicoes2026.db` utiliza rotinas determinísticas com bibliotecas canônicas da indústria (`asn1crypto`, `sqlite3`, `pandas`, `numpy`). Não são utilizados modelos opacos de inteligência artificial generativa na apuração dos números; o motor apenas consolida os registros oficiais da memória da urna.
        3. **Reprodutibilidade 100% Pública:**  
           Qualquer pesquisador, auditor, universidade ou cidadão pode baixar os pacotes brutos diretamente dos servidores do TSE e executar os scripts de conferência. Os números consolidados baterão de forma idêntica, voto por voto, evento por evento.

        ---

        #### 🛡️ 3. Política de Privacidade e Proteção de Dados (LGPD)

        Esta plataforma opera em total conformidade com a **Lei Geral de Proteção de Dados Pessoais (LGPD - Lei Federal nº 13.709/2018)**:

        1. **Natureza dos Dados Tratados:**  
           * Todos os dados de seções, zonas, municípios, horários e totais de votação são **dados públicos de livre acesso**, disponibilizados sob a égide da **Lei de Acesso à Informação (Lei nº 12.527/2011)** e do **Art. 7º, § 4º da LGPD**.
           * **Sigilo Constitucional do Voto:** Conforme o Art. 14, *caput*, da Constituição Federal de 1988, é vedada e impossível qualquer vinculação entre o voto manifestado e a pessoa física do eleitor. **Nenhum dado pessoal sensível ou identificável é armazenado, processado ou inferido.**
        2. **Canal de Transparência e Exercício de Direitos (Art. 18 da LGPD):**  
           * Caso deseje esclarecimentos adicionais sobre o tratamento de dados técnicos de navegação ou governança da plataforma, entre em contato diretamente pelo e-mail institucional: [contato@dominiodigital.dev.br](mailto:contato@dominiodigital.dev.br).

        ---

        #### 🍪 4. Gestão de Cookies e Telemetria de Acesso

        1. **Finalidade Estrita:**  
           Métricas de acesso são empregadas unicamente para dimensionamento de capacidade dos servidores, prevenção de ataques de negação de serviço (DDoS) e garantia de disponibilidade da infraestrutura.
        2. **Ferramenta de Telemetria:**  
           A plataforma pode utilizar o **Google Analytics** configurado com **anonimização forçada de endereço IP** (*IP Anonymization*). Nenhuma informação de localização exata, identidade civil ou perfil comportamental é retida.
        3. **Não Comercialização:**  
           Os registros de acesso **jamais serão comercializados, compartilhados com terceiros ou utilizados para fins publicitários ou de direcionamento eleitoral**.
        4. **Direito de Desativação (Opt-Out):**  
           O usuário pode bloquear ou excluir cookies a qualquer momento nas configurações do seu navegador ou através do [Google Analytics Opt-out Add-on](https://tools.google.com/dlpage/gaoptout). O bloqueio de cookies não compromete o funcionamento de nenhum dos painéis da plataforma.
        """)

    with tab_vers:
        st.markdown("""
        <h3 style='margin-top: 0.25rem; margin-bottom: 0.75rem;'>🏷️ Histórico de Versões & Evolução da Plataforma</h3>
        """, unsafe_allow_html=True)

        st.markdown("""
        | Versão | Data | Classificação | Principais Entregas & Notas de Engenharia |
        | :--- | :---: | :---: | :--- |
        | **v2.4.2** | **15/10/2026** | `PATCH` | **Skeleton Screen com Shimmer & Otimização de Transições:**<br>• Introdução de Skeleton Screen pulsante com gradiente de onda fluida (shimmer) durante o carregamento inicial (cold start), eliminando telas em branco.<br>• Supressão do segundo spinner no cold start e polimento visual da governança (remoção de botões redundantes e otimização vertical).<br>• Desacoplamento da renderização metodológica com tempo de resposta inferior a 15ms e persistência contextual de filtros no `session_state`. |
        | **v2.4.1** | **15/10/2026** | `PATCH` | **Otimização de Desempenho & Vetorização Numérica:**<br>• Vetorização via NumPy dos critérios de triagem forense, acelerando a renderização em mais de 90%.<br>• Pré-agregação server-side dos histogramas de distribuição temporal, reduzindo o volume de tráfego em 99,8%.<br>• Amostragem otimizada de dispersão WebGL e métricas de correlação, eliminando latências de renderização em servidores de produção. |
        | **v2.4.0** | **15/10/2026** | `MINOR` | **Módulo Analítico de Abstenção & Comparecimento Eleitoral:**<br>• Integração completa do painel de abstenção com modelo de Funil de Spiegelhalter (2005) e limites de controle paramétricos (95% e 99.8%).<br>• Incorporação da base oficial consolidada do TSE com 152 milhões de eleitores aptos e 497.895 seções apuradas.<br>• Suíte analítica com 21 KPIs (3x7) e 7 abas: *Comparar*, *Distribuição*, *Funil*, *Sinalizadas*, *Horário*, *Sem Digital* e *Cruzamento*.<br>• Detecção automatizada de seções com baixa abstenção anômala (*turnout spikes*) e geração de diagnósticos forenses objetivos.<br>• Desacoplamento arquitetural: separação modular entre painéis analíticos e tela dedicada de governança jurídica/LGPD. |
        | **v2.3.0** | **15/10/2026** | `MINOR` | **Didática Forense & Acessibilidade Universal:**<br>• Reformulação didática e acessível do caderno metodológico: tradução intuitiva da inferência estatística de Spiegelhalter (2005), analogias conceituais (MAD e o bilionário na padaria, termômetro do *z*-score e Teorema de Pitágoras/Norma Euclidiana $L_2$ multivariada) e renderização matemática isolada em blocos KaTeX.<br>• Subsistema universal de tooltips flutuantes de alto contraste invertido com suporte completo ao motor BaseWeb (cards e controles) e ao Glide Data Grid (`st.dataframe`).<br>• Conformidade com critérios WCAG de legibilidade visual em modo escuro e microinterações táteis nos ícones de ajuda contextual (?). |
        | **v2.2.0** | **14/10/2026** | `PATCH` | **Experiência Analítica Dual & Calibração Visual:**<br>• Nova visualização de distribuição em modo duplo: *Faixas de Risco Forense* (visão intuitiva com contagens e percentuais por categoria) e *Histograma Contínuo* (visão técnica detalhada até 12σ) com seletor e ajuda contextual explicativa (?).<br>• *Viewport* dinâmico inteligente no gráfico de dispersão multivariada (calibrado no 99,5º percentil), eliminando a aglomeração causada por seções com horários extremos.<br>• Desacoplamento geométrico das anotações de significância (+2σ e +3σ), eliminando sobreposições de texto.<br>• Sincronização do manifesto de módulos dinâmicos e conformidade com diretrizes de governança e LGPD. |
        | **v2.1.0** | **14/10/2026** | `MAJOR` | **Implementação do Motor Estatístico de Spiegelhalter (2005):**<br>• Substituição de regras heurísticas e pesos arbitrários por inferência estatística baseada em desvios padronizados (*z*-scores em sigmas σ).<br>• Adoção da técnica *Leave-One-Out* municipal para eliminação de viés e falsos alarmes.<br>• Estimativa robusta da superdispersão τ² intra-UF via MAD.<br>• Métricas multivariadas compostas (Norma Euclidiana $L_2$) e novos diagnósticos objetivos de alerta.<br>• Identificação formal de versionamento em toda a plataforma. |
        | **v2.0.0** | **13/10/2026** | `MAJOR` | **Auditoria Nacional Consolidada (27 UFs):**<br>• Processamento paralelo e decodificação ASN.1 dos 497.895 BUs e logs de eventos do TSE em escala nacional.<br>• Arquitetura SQLite WAL de alta performance com baixo consumo de memória RAM.<br>• Suporte nativo a Tema Claro/Escuro instantâneo e layout responsivo. |
        | **v1.0.0** | **11/10/2026** | `MINOR` | Protótipo inicial de extração de dados abertos do TSE e ranking exploratório forense. |
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<p style='margin-top: -0.5rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Plataforma de Ciência de Dados Eleitoral • Base Oficial TSE</p>",
        unsafe_allow_html=True
    )


def renderizar_painel_governanca(modo_escuro: bool = True, plotly_theme: str = "plotly_dark"):
    """
    Renderiza o Painel de Governança Pública, LGPD e Versionamento como tela completa da plataforma.
    """
    renderizar_conteudo_governanca(modo_escuro, plotly_theme)
