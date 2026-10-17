"""
Módulo de Governança Pública, Proteção de Dados (LGPD), Segurança Criptográfica e Versionamento.
Centraliza as diretrizes institucionais, conformidade legal e changelog de desenvolvimento do sistema.
"""

import re
from pathlib import Path
import streamlit as st


def _sanitizar_texto_opsec(txt: str) -> str:
    """Higieniza notas públicas removendo caminhos de código e detalhes de infraestrutura interna."""
    # Remove caminhos de arquivos (.py, .ps1, .cmd, .parquet, .db, .json, .sh, etc.)
    txt = re.sub(r"`?[a-zA-Z0-9_\-\.\/]+\.(?:py|ps1|cmd|sh|parquet|db|json|toml|yml|yaml|sql)`?", "", txt)
    # Remove referências diretas a diretórios internos de código
    txt = re.sub(r"`?(?:web|pipeline|scripts|db|dados|motores|modulos)\/`?", "", txt)
    # Remove menções a comandos internos de terminal
    txt = re.sub(r"`?python\s+-[m\w\s\.-]+`?", "", txt)
    # Remove parênteses que ficaram vazios após a remoção de caminhos: ( ) ou ()
    txt = re.sub(r"\(\s*\)", "", txt)
    # Limpa espaços duplos residuais
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return txt


def obter_tabela_changelog_markdown() -> str:
    """
    Lê o CHANGELOG.md e constrói dinamicamente a tabela Markdown com o histórico
    oficial de entregas e melhorias da plataforma, aplicando filtros estritos de OpSec.
    """
    web_dir = Path(__file__).resolve().parent.parent
    root_dir = web_dir.parent

    content = ""
    for p in [root_dir / "CHANGELOG.md", web_dir / "CHANGELOG.md", Path("CHANGELOG.md")]:
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
                break
            except Exception:
                pass

    if not content:
        return """
| Versão | Data | Classificação | Principais Entregas & Melhorias da Plataforma |
| :--- | :---: | :---: | :--- |
| **v2.7.0** | **17/10/2026** | `MINOR` | Módulo Geoespacial de Fiscais & Seções e Camadas OpenStreetMap. |
"""

    pattern = r"^##\s*\[(\d+\.\d+\.\d+)\]\s*-\s*([0-9-]+)"
    matches = list(re.finditer(pattern, content, re.MULTILINE))

    linhas_tabela = [
        "| Versão | Data | Classificação | Principais Entregas & Melhorias da Plataforma |",
        "| :--- | :---: | :---: | :--- |"
    ]

    for i, m in enumerate(matches):
        versao = m.group(1)
        data_iso = m.group(2)
        d_pts = data_iso.split("-")
        data_br = f"{d_pts[2]}/{d_pts[1]}/{d_pts[0]}" if len(d_pts) == 3 else data_iso

        v_nums = [int(x) for x in versao.split(".")]
        if i < len(matches) - 1:
            prev_nums = [int(x) for x in matches[i + 1].group(1).split(".")]
            if v_nums[0] > prev_nums[0]:
                semver_type = "MAJOR"
            elif v_nums[1] > prev_nums[1]:
                semver_type = "MINOR"
            else:
                semver_type = "PATCH"
        else:
            semver_type = "MINOR"

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        bloco = content[start:end].strip().strip("---").strip()

        itens = []
        for l in bloco.split("\n"):
            l_str = _sanitizar_texto_opsec(l.strip())
            if not l_str or l_str.startswith("### "):
                continue
            if l_str.startswith("- ") or l_str.startswith("* "):
                itens.append("• " + l_str[2:].strip())
            elif l_str.startswith("• "):
                itens.append(l_str)
            else:
                itens.append(l_str)

        descricao = "<br>".join(itens)
        descricao = descricao.replace("|", "\\|")
        linhas_tabela.append(f"| **v{versao}** | **{data_br}** | `{semver_type}` | {descricao} |")

    return "\n".join(linhas_tabela)


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
        2. **Código Determinístico e Auditável (Zero Alucinação):**  
           O processamento analítico dos dados utiliza rotinas matemáticas e determinísticas em estrito alinhamento às especificações oficiais abertas do TSE (ISO/IEC 8824 e ASN.1). Não são utilizados modelos opacos de inteligência artificial generativa na apuração dos números; o motor apenas consolida e sumariza os registros oficiais emitidos pelas urnas.
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

        st.markdown(obter_tabela_changelog_markdown(), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<p style='margin-top: -0.5rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Plataforma de Ciência de Dados Eleitoral • Base Oficial TSE</p>",
        unsafe_allow_html=True
    )


def renderizar_governanca(modo_escuro: bool = True, plotly_theme: str = "plotly_dark"):
    """
    Renderiza o Módulo de Governança Pública, LGPD e Versionamento como tela completa da plataforma.
    """
    renderizar_conteudo_governanca(modo_escuro, plotly_theme)
