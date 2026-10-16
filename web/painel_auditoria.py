"""
Módulo de Auditoria Forense de Urnas e Logs - Eleições 2026.
Isola a visualização de horários de votação, fechamento e biometria manual.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

def renderizar_metodologia_auditoria():
    """Renderiza a documentação científica e guia operacional do painel de auditoria de urnas."""
    st.markdown(r"""
    ## 🗳️ Metodologia Científica & Funcionamento: Painel de Auditoria de Urnas

    > 🔬 **Escopo Técnico Deste Painel:**  
    > Este módulo é dedicado à auditoria estatística e temporal de **497.895 seções eleitorais**, analisando os arquivos oficiais de **Log de Eventos (`logd.dat`)** e **Boletins de Urna (`bu.dat`)** emitidos pelas urnas eletrônicas brasileiras sob a égide do TSE.  
    > O objetivo é identificar **comportamentos operacionais atípicos** (votos após às 17h, liberações manuais por mesário e ociosidade) através de modelos determinísticos e inferência científica.

    ---

    ### 📦 1. De Onde Vêm os Dados e o que é Analisado?

    Para cada seção eleitoral, dois tipos de arquivos públicos oficiais emitidos pela própria Urna Eletrônica são lidos e processados:

    * **1. Arquivo de Log de Eventos (`logd.dat` / `*.logd`):**  
      Registro cronológico gravado segundo a segundo. Cada eleitor que comparece gera registros operacionais no log: a inicialização dos sistemas, o teste de hardware, a chegada do eleitor à mesa receptora, a tentativa de leitura biométrica (ou dispensa manual com código pelo mesário), o tempo despendido na cabine e a emissão do comprovante.  
      *Nota Constitucional:* O log de eventos protege estritamente o sigilo constitucional do voto (Art. 14, caput, da CF/88). O log **não** registra e nem pode registrar em quem o eleitor votou; ele registra apenas o fluxo operacional e temporal da urna.
    
    * **2. Arquivo de Boletim de Urna (`bu.dat` / `*.bu`):**  
      Documento digital oficial gerado pela urna ao encerrar a votação, formatado na especificação internacional aberta **ASN.1 (Abstract Syntax Notation One - ISO/IEC 8824)**. O BU contém a totalização estática dos votos nominais por candidato, votos em branco, votos nulos, comparecimento e abstenção daquela seção específica.

    ---

    ### 📐 2. Metodologia Estatística e Rigor Científico (Modelo de Spiegelhalter, 2005)

    A plataforma aplica o **Modelo de Efeitos Aleatórios e Controle Estatístico de Processos de David Spiegelhalter (2005)** — padrão acadêmico internacional utilizado em auditorias populacionais, epidemiológicas e de controle de qualidade hospitalar (*"Funnel plots for comparing institutional performance"*, *Statistics in Medicine*).

    ---

    #### 💡 Intuição Prática: O que é o "Sigma" ($\sigma$) e o $Z$-Score?

    Em vez de comparar percentuais brutos isolados — o que geraria distorções entre cidades de portes diferentes —, o painel mede **a quantos desvios-padrão (sigmas $\sigma$) uma seção eleitoral se afastou do comportamento esperado do seu município**:

    * **A Analogia da Altura:** Imagine a altura dos homens adultos no Brasil. A média é de 1,75 m, com uma variação comum de 7 cm (1 sigma):
      * Um homem de 1,82 m (+1$\sigma$) é alto, mas perfeitamente comum no dia a dia.
      * Um homem de 1,89 m (+2$\sigma$) já é uma exceção notável (presente em apenas ~2,3% da população).
      * Um homem de 2,05 m (+4,3$\sigma$) é uma raridade extrema (como um jogador de basquete profissional).

    Na auditoria eleitoral, a lógica é idêntica: se na cidade a média foi de 2% de votos pós-17h, uma seção registrar 3% (+0,8$\sigma$) é uma oscilação natural de fila. Porém, uma seção da mesma cidade registrar 25% de votos tardios (+4,5$\sigma$) equivale estatisticamente a encontrar alguém de 2,15 m de altura na rua — um evento estatisticamente raro que justifica a conferência da ata física do cartório.

    ---

    #### A. Comparação Justa via Técnica *Leave-One-Out* (Exclusão da Própria Seção)

    Cada seção é avaliada estritamente em relação à realidade do seu **próprio município**. Seções ribeirinhas ou rurais não são comparadas a capitais cosmopolitas.

    * **Eliminação de Viés:** Se uma seção atípica de grande porte apresentasse um volume extremo de votos tardios, incluí-la na média municipal puxaria a régua toda para cima, "mascarando" a sua própria anomalia.
    * A técnica *Leave-One-Out* ("deixar-um-de-fora") calcula a média de referência da cidade **excluindo temporariamente a própria seção em avaliação**, garantindo que a régua nunca seja contaminada pelo objeto da auditoria.

    **Fórmula da Taxa Esperada Municipal:**

    $$
    p_{\text{mun}} = \frac{\sum_{i \in \text{mun}} \text{Votos}_{i} - \text{Votos}_{\text{secao}}}{\sum_{i \in \text{mun}} \text{Total}_{i} - \text{Total}_{\text{secao}}}
    $$

    ---

    #### B. $Z$-Score Ajustado com Superdispersão Residual ($\tau^2$ de Spiegelhalter)

    Modelos estatísticos simplistas tratam eleitores como moedas matemáticas perfeitamente idênticas. No mundo real, existem fatores operacionais legítimos: chuvas torrenciais em um bairro, lentidão de transporte ou oscilação de energia em zonas rurais.

    * **O que é o parâmetro $\tau^2$ (tau ao quadrado)?**  
      Ele quantifica e absorve a "variação natural legítima" que existe entre diferentes bairros e cidades do estado. Isso evita que pequenas seções de 80 eleitores no interior disparem falsos alarmes por mero efeito do acaso amostral.

    * **O que é o MAD (Desvio Absoluto da Mediana) e por que ele é usado?**  
      Na estatística comum, a média e o desvio padrão tradicional são facilmente enganados por um único número absurdo (por exemplo: se um bilionário entrar em uma padaria, a "renda média" de todos os clientes vira milhões de reais em um segundo).  
      O **MAD** funciona como uma **régua blindada contra distorções**: em vez de calcular médias que podem ser puxadas por valores extremos, ele mede a dispersão típica olhando apenas para o valor central (a mediana). Dessa forma, se uma única urna na capital tiver um problema bizarro que a faça fechar às 23h, esse caso isolado **não contamina nem distorce a régua de medição** de todas as outras urnas do estado.

    * **Resultado (O que significa o $Z$?):**  
      O **$Z$** (chamado na ciência de *$Z$-score* ou escore padronizado) funciona como um **termômetro de atipicidade**: ele é a nota final que indica quantos passos (sigmas $\sigma$) a urna se afastou do comportamento esperado.
      * **$Z = 0$:** A seção operou exatamente na média da sua cidade (temperatura normal de 36,5 °C).
      * **$Z < 2{,}0\sigma$:** Variação comum do dia a dia, dentro da normalidade.
      * **$Z \ge 3{,}0\sigma$:** O termômetro entra em zona crítica: a seção funcionou de maneira totalmente atípica em relação a todas as outras urnas da mesma cidade, com menos de 0,13% de chance de ocorrer por mero acaso sob condições normais.

    **Fórmula do $Z$-Score Ajustado de Spiegelhalter:**

    $$
    z_{\text{ajustado}} = \frac{\text{Taxa Observada} - p_{\text{mun}}}{\sqrt{\frac{p_{\text{mun}}(1 - p_{\text{mun}})}{N} + \tau^2}}
    $$

    **Fórmula da Superdispersão Residual ($\tau^2$ Robusto via MAD):**

    $$
    \tau^2 = \max\left(\left(1{,}4826 \cdot \text{MAD}\right)^2 - \text{Mediana}(\text{Variancia Acaso}),\, 0\right)
    $$

    ---

    #### C. Desvio Multivariado Composto (Norma Euclidiana $L_2$)

    Em vez de avaliar os indicadores de forma fragmentada, o sistema aplica uma distância geométrica no espaço de desvios:
    * Se uma urna teve apenas um leve atraso pós-17h (+1,2$\sigma$), ela permanece dentro do raio de normalidade.
    * Se teve apenas uma leve elevação de biometria manual (+1,2$\sigma$), também segue no padrão aceitável.
    * Porém, se a mesma urna combinou atraso severo (+3$\sigma$) **e** biometria manual muito acima da média (+3$\sigma$), o afastamento conjunto pela hipotenusa dispara para $\sqrt{3^2 + 3^2} = 4{,}24\sigma$!  
    A **Norma $L_2$** calcula a distância em linha reta do ponto onde a urna operou até o centro da normalidade da eleição.

    **Fórmula da Norma Euclidiana $L_2$:**

    $$
    Z_{\text{composto}} = \sqrt{\max(z_{\text{pos17}}, 0)^2 + \max(z_{\text{manual}}, 0)^2 + \max(z_{\text{horario}}, 0)^2}
    $$

    ---

    #### D. Régua Padronizada de Significância Estatística
    * **Padrão Normal ($Z < 2{,}0\sigma$):** Seção perfeitamente compreendida dentro do intervalo de confiança de 95% do seu município.
    * **🟡 Atenção ($2{,}0\sigma \le Z < 3{,}0\sigma$):** Desvio moderado em relação à linha de base local (percentil $\approx 97{,}7\%$).
    * **🟠 Alta Atipicidade ($3{,}0\sigma \le Z < 4{,}5\sigma$):** Desvio severo em relação ao comportamento padrão do município (percentil $\approx 99{,}87\%$).
    * **🔴 Atipicidade Extrema ($Z \ge 4{,}5\sigma$):** Confluência crítica de desvios simultâneos de horário, fluxo e habilitação.

    ---

    ### 🎯 3. Como Interpretar os Gráficos?

    1. **Gráfico de Dispersão Multivariada ($Z$ Pós-17h vs $Z$ Manual):**
       * **Concentração Inferior Esquerda:** Reúne mais de 95% das seções brasileiras. São os círculos que operaram rigorosamente dentro do padrão esperado para suas cidades.
       * **Linhas de Demarcação (+2$\sigma$ amarela e +3$\sigma$ vermelha):** Indicam os limites de significância estatística. Círculos posicionados além da linha vermelha (seja para a direita ou para cima) operaram com taxas significativamente superiores ao restante do município.
       * **Canto Superior Direito:** Representa a confluência mais crítica da fiscalização — urnas que acumularam fechamento tardio com alta taxa de habilitação sem biometria.

    2. **Gráfico de Distribuição (Modo Faixas de Risco):**
       * **Barra Azul (Normal, < 2$\sigma$):** Confirma a estabilidade e regularidade da imensa maioria das urnas auditadas no país.
       * **Barra Amarela (Atenção, 2 a 3$\sigma$):** Seções com atipicidades operacionais moderadas (geralmente explicadas por dinâmica local de filas).
       * **Barras Laranja e Vermelha ($\ge 3\sigma$):** O foco prioritário da auditoria. Evidencia com clareza o volume exato e a proporção de urnas que demandam verificação cruzada com a Ata da Mesa Receptora e o Boletim de Urna (BU).

    ---

    ### 🔍 4. Como Interpretar os Alertas e Próximos Passos Forenses?

    Um desvio estatístico padronizado ($Z \ge 3{,}0\sigma$) **não constitui prova de fraude**. Ele constitui uma **sinalização objetiva de atipicidade operacional e matemática**.  
    Explicações legítimas comuns incluem:
    * Fila física no encerramento decorrente de chuvas severas ou falta pontual de energia na região.
    * Urna eletrônica com leitor biométrico desgastado ou seção com concentração atípica de eleitores idosos (com perda de relevo papilar).
    * Comunidades de acesso complexo (seções em áreas ribeirinhas, indígenas ou rurais).

    **O passo forense correto:** Peritos, auditores e cidadãos devem confrontar o número da seção com a **Ata da Mesa Receptora** arquivada no Cartório Eleitoral e com o espelho do Boletim de Urna (BU) para checar as justificativas anotadas pelos mesários.

    ---
    <p style='margin-top: 0.6rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Painel de Auditoria de Urnas • Versão 2.4.2</p>
    """, unsafe_allow_html=True)


def renderizar_painel_auditoria(
    df: pd.DataFrame,
    modo_escuro: bool,
    plotly_theme: str,
    fmt_int_br,
    fmt_float_br
):
    OPCOES_NAV = [
        "📊 Painel de Auditoria & Ranking Forense",
        "ℹ️ Metodologia & Funcionamento (Auditoria de Urnas)"
    ]
    
    if "aba" in st.query_params:
        if st.query_params["aba"].lower() in ["sobre", "metodologia", "aviso"]:
            st.session_state["aba_ativa"] = OPCOES_NAV[1]
        else:
            st.session_state["aba_ativa"] = OPCOES_NAV[0]
    elif "aba_ativa" not in st.session_state:
        st.session_state["aba_ativa"] = OPCOES_NAV[0]
    
    aba_selecionada = st.segmented_control(
        "Navegação",
        options=OPCOES_NAV,
        key="aba_ativa",
        selection_mode="single",
        required=True,
        label_visibility="collapsed",
        width="stretch"
    )
    if not aba_selecionada:
        aba_selecionada = OPCOES_NAV[0]
    
    # Se estiver na Metodologia, renderiza imediatamente SEM tocar na barra lateral nem filtrar dados
    if aba_selecionada == OPCOES_NAV[1]:
        renderizar_metodologia_auditoria()
        return
    
    def ir_para_resultados():
        st.session_state["aba_ativa"] = OPCOES_NAV[0]
    
    # ==========================================
    # FILTROS LATERAIS (SIDEBAR)
    # ==========================================
    st.sidebar.header("🔍 Filtros")
    
    col_reg, col_uf = st.sidebar.columns([3, 2])
    regioes_disponiveis = ["Todas", "Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]
    reg_salva = st.session_state.get("audit_regiao_salva", "Todas")
    reg_idx = regioes_disponiveis.index(reg_salva) if reg_salva in regioes_disponiveis else 0
    regiao_selecionada = col_reg.selectbox("Região:", regioes_disponiveis, index=reg_idx, on_change=ir_para_resultados, key="audit_regiao")
    st.session_state["audit_regiao_salva"] = regiao_selecionada
    
    df_filtrado = df.copy()
    if regiao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["regiao"] == regiao_selecionada]
    
    # Filtro Estado (UF) em cascata da região
    ufs_disponiveis = ["Todas"] + sorted(df_filtrado["uf"].unique().tolist())
    uf_salva = st.session_state.get("audit_uf_salva", "Todas")
    uf_idx = ufs_disponiveis.index(uf_salva) if uf_salva in ufs_disponiveis else 0
    uf_selecionada = col_uf.selectbox("UF:", ufs_disponiveis, index=uf_idx, on_change=ir_para_resultados, key="audit_uf")
    st.session_state["audit_uf_salva"] = uf_selecionada
    if uf_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["uf"] == uf_selecionada]
    
    # Filtro Município com Nome Real
    municipios_disponiveis = ["Todos"] + sorted(df_filtrado["municipio_display"].unique().tolist())
    mun_salvo = st.session_state.get("audit_mun_salvo", "Todos")
    mun_idx = municipios_disponiveis.index(mun_salvo) if mun_salvo in municipios_disponiveis else 0
    municipio_selecionado = st.sidebar.selectbox("Município:", municipios_disponiveis, index=mun_idx, on_change=ir_para_resultados, key="audit_municipio")
    st.session_state["audit_mun_salvo"] = municipio_selecionado
    if municipio_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["municipio_display"] == municipio_selecionado]
    
    # Filtro Zona e Seção lado a lado
    col_zona, col_secao = st.sidebar.columns(2)
    zonas_disponiveis = ["Todas"] + sorted(df_filtrado["zona"].unique().tolist())
    zona_salva = st.session_state.get("audit_zona_salva", "Todas")
    zona_idx = zonas_disponiveis.index(zona_salva) if zona_salva in zonas_disponiveis else 0
    zona_selecionada = col_zona.selectbox("Zona:", zonas_disponiveis, index=zona_idx, on_change=ir_para_resultados, key="audit_zona")
    st.session_state["audit_zona_salva"] = zona_selecionada
    if zona_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["zona"] == zona_selecionada]
    
    secoes_disponiveis = ["Todas"] + sorted(df_filtrado["secao"].unique().tolist())
    sec_salva = st.session_state.get("audit_secao_salva", "Todas")
    sec_idx = secoes_disponiveis.index(sec_salva) if sec_salva in secoes_disponiveis else 0
    secao_selecionada = col_secao.selectbox("Seção:", secoes_disponiveis, index=sec_idx, on_change=ir_para_resultados, key="audit_secao")
    st.session_state["audit_secao_salva"] = secao_selecionada
    if secao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["secao"] == secao_selecionada]
    
    
    # Filtros Estatísticos de Atipicidade (Spiegelhalter 2005)
    OPCOES_ATIPICIDADE = {
        "Todas as Seções (Visão Geral)": 0.0,
        "🟡 Atenção: Desvio Moderado (≥ 2.0σ)": 2.0,
        "🟠 Atipicidade Alta: Desvio Severo (≥ 3.0σ)": 3.0,
        "🔴 Atipicidade Extrema: Desvio Crítico (≥ 4.5σ)": 4.5
    }
    atipicidade_selecionada = st.sidebar.selectbox(
        "Nível de Atipicidade Estatística:",
        list(OPCOES_ATIPICIDADE.keys()),
        on_change=ir_para_resultados,
        help="Filtra as seções de acordo com a magnitude do desvio padronizado em relação ao município/UF (Modelo Spiegelhalter 2005): Normal (< 2σ), Atenção (2σ-3σ), Alta (3σ-4.5σ) e Extrema (≥ 4.5σ)."
    )
    z_min = OPCOES_ATIPICIDADE[atipicidade_selecionada]
    
    OPCOES_POS17 = {
        "Qualquer horário": 0.0,
        "Acima de 10% dos votos após as 17h": 10.0,
        "Acima de 25% dos votos após as 17h (Filas longas)": 25.0,
        "Acima de 50% dos votos após as 17h (Votação prolongada)": 50.0
    }
    pos17_selecionado = st.sidebar.selectbox(
        "Volume de Votos Pós-17h:",
        list(OPCOES_POS17.keys()),
        on_change=ir_para_resultados,
        help="Filtra a proporção de eleitores que votaram após o horário regular de fechamento (17h)."
    )
    pct_pos17_min = OPCOES_POS17[pos17_selecionado]
    
    with st.sidebar.expander("⚙️ Ajuste Fino Estatístico"):
        z_slider = st.slider(
            "Desvio Mínimo Exato (Z-Score em σ):",
            min_value=0.0,
            max_value=15.0,
            value=float(z_min),
            step=0.5,
            on_change=ir_para_resultados,
            help="Permite afinar manualmente o desvio padronizado multivariado em sigmas."
        )
        st.caption("📊 **Régua:** < 2.0σ: Normal | 2.0–2.9σ: Atenção | 3.0–4.4σ: Alta Atipicidade | ≥ 4.5σ: Extrema")
    
        pct_slider = st.slider(
            "% Pós-17h Mínimo Exato:",
            min_value=0.0,
            max_value=100.0,
            value=float(pct_pos17_min),
            step=5.0,
            on_change=ir_para_resultados,
            help="Permite afinar manualmente o percentual de votos após as 17h."
        )
        st.caption("⏰ **Referência:** 0%: Todas | >10%: Fila Moderada | >25%: Fila Longa | >50%: Votação Prolongada")
    
    z_final = max(z_min, z_slider)
    pct_final = max(pct_pos17_min, pct_slider)
    
    df_filtrado = df_filtrado[df_filtrado["z_composto"] >= z_final]
    df_filtrado = df_filtrado[df_filtrado["pct_apos_17h"] >= pct_final]
    
    # Checkbox posicionado após todos os controles
    apenas_com_alertas = st.sidebar.checkbox(
        "Mostrar apenas seções com alertas confirmados",
        value=False,
        on_change=ir_para_resultados,
        help="Filtra apenas seções onde foi detectado desvio estatístico (Z ≥ 2.0σ) ou sinal de alerta explícito."
    )
    if apenas_com_alertas:
        df_filtrado = df_filtrado[df_filtrado["z_composto"] >= 2.0]
    
    # Filtro Vencedor da Seção (Boletim de Urna)
    venc_options = ["Todos", "Nº 13 (Lula)", "Nº 22 (Flávio Bolsonaro)"]
    venc_sel = st.sidebar.selectbox(
        "Mais Votado na Seção (Presidente):",
        venc_options,
        on_change=ir_para_resultados,
        help="Filtra seções onde o candidato selecionado obteve a maioria dos votos nominais no Boletim de Urna oficial."
    )
    if venc_sel == "Nº 13 (Lula)":
        df_filtrado = df_filtrado[df_filtrado["pres_venc_num"] == 13]
    elif venc_sel == "Nº 22 (Flávio Bolsonaro)":
        df_filtrado = df_filtrado[df_filtrado["pres_venc_num"] == 22]
    
    
    if aba_selecionada == OPCOES_NAV[0]:
        # ==========================================
        # CARDS DE KPI (MÉTRICAS GERAIS)
        # ==========================================
        if secao_selecionada != "Todas" and len(df_filtrado) == 1:
            r = df_filtrado.iloc[0]
            st.info(
                f"🔍 **Seção {r['secao']} (Zona {r['zona']} - {r['municipio_nome']}/{r['uf']}):** "
                f"Primeiro voto: **{r['primeiro_voto']}** | Último voto: **{r['ultimo_voto']}** | Encerramento: **{r['hora_encerramento']}** | "
                f"Pós-17h: **{fmt_int_br(r['votos_apos_17h'])} votos** ({fmt_float_br(r['pct_apos_17h'])}% | esp. mun.: {fmt_float_br(r['esp_pos17_pct'])}% | **Z: +{r['z_pos17']:.1f}σ**) | "
                f"Manual: **+{r['z_manual']:.1f}σ** | Desvio Geral: **+{r['z_composto']:.1f}σ** | "
                f"Alerta: **{r['motivos_alerta']}**"
            )
            if pd.notna(r.get("pres_venc_num")) and r.get("pres_total_validos", 0) > 0:
                v_num = int(r["pres_venc_num"])
                v_label = "Lula (13)" if v_num == 13 else ("Flávio Bolsonaro (22)" if v_num == 22 else f"Nº {v_num}")
                lula_v = int(r.get("votos_cand_13", 0))
                bolso_v = int(r.get("votos_cand_22", 0))
                tot_v = int(r.get("pres_total_validos", 0))
                lula_pct = (lula_v / tot_v * 100.0) if tot_v > 0 else 0.0
                bolso_pct = (bolso_v / tot_v * 100.0) if tot_v > 0 else 0.0
    
                delta_venc = r.get("delta_venc_zona")
                delta_str = f" ({fmt_float_br(delta_venc, force_sign=True)} pp vs Zona)" if pd.notna(delta_venc) else ""
                pct_13_z = r.get("pct_13_zona")
                pct_22_z = r.get("pct_22_zona")
                zona_info = f" | Média da Zona {r['zona']}: Lula {fmt_float_br(pct_13_z)}% vs Flávio Bolsonaro {fmt_float_br(pct_22_z)}%" if pd.notna(pct_13_z) else ""
    
                st.success(
                    f"🗳️ **Apuração Oficial do Boletim de Urna (BU):** "
                    f"Mais Votado: **{v_label}** com **{fmt_int_br(r['pres_venc_votos'])} votos ({fmt_float_br(r['pres_venc_pct'])}%){delta_str}** | "
                    f"Lula (13): **{fmt_int_br(lula_v)} votos ({fmt_float_br(lula_pct)}%)** | "
                    f"Flávio Bolsonaro (22): **{fmt_int_br(bolso_v)} votos ({fmt_float_br(bolso_pct)}%)** | "
                    f"Total Votos Válidos: **{fmt_int_br(tot_v)}**"
                    f"{zona_info}"
                )
    
        total_secoes = len(df_filtrado)
        total_votos = df_filtrado["total_votos_log"].sum() if total_secoes > 0 else 0
        total_pos17 = df_filtrado["votos_apos_17h"].sum() if total_secoes > 0 else 0
        pct_total_pos17 = (total_pos17 / total_votos * 100.0) if total_votos > 0 else 0.0
        criticas = len(df_filtrado[df_filtrado["z_composto"] >= 3.0])
    
        with st.container(key="kpi_metrics"):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(
                "Seções Filtradas",
                fmt_int_br(total_secoes),
                help="Quantidade total de seções eleitorais que atendem aos filtros selecionados na barra lateral."
            )
            c2.metric(
                "Total de Votos",
                fmt_int_br(total_votos),
                help="Soma dos votos oficiais registrados nos arquivos de log das urnas para as seções selecionadas."
            )
            c3.metric(
                "Votos Pós-17h",
                fmt_int_br(total_pos17),
                f"{fmt_float_br(pct_total_pos17)}% do total",
                help="Volume e proporção percentual de eleitores que votaram após as 17h00 (horário oficial de encerramento)."
            )
            c4.metric(
                "Alta Atipicidade (≥ 3.0σ)",
                fmt_int_br(criticas),
                help="Seções com desvio padronizado multivariado Z ≥ 3.0σ pelo Modelo Spiegelhalter 2005 (além de 3 desvios padrão do município)."
            )
            media_z = df_filtrado["z_composto"].mean() if total_secoes > 0 else 0.0
            c5.metric(
                "Desvio Médio (Z)",
                f"+{fmt_float_br(media_z)}σ",
                help="Média do desvio padronizado multivariado (em sigmas) das seções filtradas na tela."
            )
    
        st.markdown("---")
    
        # ==========================================
        # GRÁFICOS ANALÍTICOS (ALINHAMENTO SIMÉTRICO)
        # ==========================================
        with st.container(key="graficos_container"):
            c_top1, c_top2 = st.columns([1, 1])
            with c_top1:
                st.markdown("<p style='font-size: 0.92rem; font-weight: 500; color: #8b949e; margin-top: 14px; margin-bottom: 0;'>📈 Modelagem Estatística Multivariada (Spiegelhalter 2005)</p>", unsafe_allow_html=True)
            with c_top2:
                modo_distribuicao = st.radio(
                    "Tipo de Gráfico (Distribuição):",
                    options=["📊 Faixas de Risco", "🔬 Histograma (Z)"],
                    index=0,
                    horizontal=True,
                    help=(
                        "Escolha como prefere visualizar a distribuição das urnas:\n\n"
                        "• 📊 Faixas de Risco (Recomendado): Visão simples e direta que agrupa as seções em 4 níveis "
                        "(Normal, Atenção, Alta Atipicidade e Anomalia Extrema), mostrando o total e a porcentagem de urnas em cada grupo.\n\n"
                        "• 🔬 Histograma (Z): Curva matemática detalhada dos desvios em sigmas (σ), "
                        "ideal para quem deseja auditar tecnicamente a frequência e a intensidade dos desvios."
                    ),
                    key="modo_dist_toggle"
                )
    
            col_graf1, col_graf2 = st.columns(2)
    
            with col_graf1:
                st.subheader("📊 Desvio Pós-17h (Z) vs Desvio Manual (Z)")
                st.caption("Dispersão estatística multivariada padronizada (Modelo de Spiegelhalter 2005).")
                if not df_filtrado.empty:
                    # Amostra inteligente para dispersão quando volume for muito massivo (reduz de 17MB para 180KB)
                    if len(df_filtrado) > 5000:
                        criticas = df_filtrado[df_filtrado["z_composto"] >= 3.0]
                        if len(criticas) >= 5000:
                            df_scatter = criticas.sample(5000, random_state=42)
                        else:
                            outras = df_filtrado[df_filtrado["z_composto"] < 3.0]
                            amostra = outras.sample(min(len(outras), 5000 - len(criticas)), random_state=42)
                            df_scatter = pd.concat([criticas, amostra])
                    else:
                        df_scatter = df_filtrado
    
                    fig_scatter = px.scatter(
                        df_scatter,
                        x="z_pos17",
                        y="z_manual",
                        size="total_votos_log",
                        color="z_composto",
                        hover_data=["uf", "municipio_nome", "zona", "secao", "ultimo_voto", "motivos_alerta"],
                        color_continuous_scale="Reds",
                        labels={
                            "z_pos17": "Desvio Z Votos Pós-17h (σ)",
                            "z_manual": "Desvio Z Habilitação Manual (σ)",
                            "z_composto": "Desvio Geral (σ)"
                        }
                    )
                    # Linhas de referência de significância estatística (+2σ e +3σ) com geometria anti-colisão
                    fig_scatter.add_vline(
                        x=2.0, line_dash="dot", line_color="#f59e0b",
                        annotation_text="+2σ", annotation_position="top left",
                        annotation_font=dict(size=10, color="#f59e0b")
                    )
                    fig_scatter.add_vline(
                        x=3.0, line_dash="dash", line_color="#ef4444",
                        annotation_text="+3σ Crítico", annotation_position="top right",
                        annotation_yshift=-25,
                        annotation_font=dict(size=11, color="#ef4444")
                    )
                    fig_scatter.add_hline(
                        y=2.0, line_dash="dot", line_color="#f59e0b",
                        annotation_text="+2σ", annotation_position="top left",
                        annotation_font=dict(size=10, color="#f59e0b")
                    )
                    fig_scatter.add_hline(
                        y=3.0, line_dash="dash", line_color="#ef4444",
                        annotation_text="+3σ Crítico", annotation_position="top right",
                        annotation_font=dict(size=11, color="#ef4444")
                    )
                    # Viewport dinâmico focado nos 99.5% dos dados, evitando compressão por outliers extremos
                    q995_x = float(df_scatter["z_pos17"].quantile(0.995)) if len(df_scatter) > 10 else 20.0
                    q995_y = float(df_scatter["z_manual"].quantile(0.995)) if len(df_scatter) > 10 else 12.0
                    x_max = max(15.0, min(30.0, q995_x + 2.0))
                    y_max = max(10.0, min(20.0, q995_y + 2.0))
                    fig_scatter.update_xaxes(range=[-1.5, x_max])
                    fig_scatter.update_yaxes(range=[-1.5, y_max])
    
                    fig_scatter.update_layout(template=plotly_theme, height=420, margin=dict(l=20, r=20, t=40, b=20), separators=",.")
                    st.plotly_chart(fig_scatter, width="stretch")
                    if len(df_filtrado) > 5000:
                        st.caption("*💡 Amostra estatística de 5.000 seções (priorizando as seções de maior atipicidade). Pan e zoom habilitados.*")
    
            with col_graf2:
                st.subheader("📊 Distribuição de Anomalias")
    
                if modo_distribuicao == "📊 Faixas de Risco":
                    st.caption("Classificação das seções pelo desvio padronizado multivariado (Modelo Spiegelhalter).")
                    if not df_filtrado.empty:
                        total_s = len(df_filtrado)
                        c_normal = int((df_filtrado["z_composto"] < 2.0).sum())
                        c_atencao = int(((df_filtrado["z_composto"] >= 2.0) & (df_filtrado["z_composto"] < 3.0)).sum())
                        c_alta = int(((df_filtrado["z_composto"] >= 3.0) & (df_filtrado["z_composto"] < 4.5)).sum())
                        c_extrema = int((df_filtrado["z_composto"] >= 4.5).sum())
    
                        p_normal = c_normal * 100.0 / total_s
                        p_atencao = c_atencao * 100.0 / total_s
                        p_alta = c_alta * 100.0 / total_s
                        p_extrema = c_extrema * 100.0 / total_s
    
                        df_cat = pd.DataFrame({
                            "Faixa": [
                                "Normal (< 2σ)",
                                "Atenção (2-3σ)",
                                "Alta Atipicidade (3-4.5σ)",
                                "Anomalia Extrema (≥ 4.5σ)"
                            ],
                            "Qtd": [c_normal, c_atencao, c_alta, c_extrema],
                            "Rotulo": [
                                f"{p_normal:.1f}%<br>({fmt_int_br(c_normal)})",
                                f"{p_atencao:.1f}%<br>({fmt_int_br(c_atencao)})",
                                f"{p_alta:.1f}%<br>({fmt_int_br(c_alta)})",
                                f"{p_extrema:.1f}%<br>({fmt_int_br(c_extrema)})"
                            ]
                        })
    
                        cores_map = {
                            "Normal (< 2σ)": "#3b82f6",
                            "Atenção (2-3σ)": "#f59e0b",
                            "Alta Atipicidade (3-4.5σ)": "#f97316",
                            "Anomalia Extrema (≥ 4.5σ)": "#ef4444"
                        }
    
                        fig_cat = px.bar(
                            df_cat,
                            x="Faixa",
                            y="Qtd",
                            text="Rotulo",
                            color="Faixa",
                            color_discrete_map=cores_map,
                            labels={"Faixa": "Nível de Significância Forense", "Qtd": "Quantidade de Seções"}
                        )
                        fig_cat.update_traces(
                            textposition="outside",
                            cliponaxis=False,
                            textfont=dict(size=12, color="#f0f2f6")
                        )
                        fig_cat.update_layout(
                            template=plotly_theme,
                            height=420,
                            showlegend=False,
                            margin=dict(l=20, r=20, t=55, b=20),
                            separators=",."
                        )
                        st.plotly_chart(fig_cat, width="stretch")
                else:
                    st.caption("Histograma contínuo dos desvios padronizados em sigmas (σ) até 12σ.")
                    if not df_filtrado.empty:
                        z_valid = df_filtrado["z_composto"].dropna()
                        z_plot = z_valid.clip(0.0, 12.0)
                        fig_hist = px.histogram(
                            z_plot,
                            x="z_composto",
                            nbins=30,
                            range_x=[0.0, 12.0],
                            color_discrete_sequence=["#3b82f6"],
                            labels={"z_composto": "Desvio Padronizado Composto (σ)"}
                        )
                        fig_hist.add_vline(
                            x=2.0, line_dash="dash", line_color="#f59e0b",
                            annotation_text="+2σ Atenção", annotation_position="top left",
                            annotation_font=dict(size=10, color="#f59e0b")
                        )
                        fig_hist.add_vline(
                            x=3.0, line_dash="solid", line_color="#ef4444",
                            annotation_text="+3σ Crítico", annotation_position="top right",
                            annotation_yshift=-26,
                            annotation_font=dict(size=11, color="#ef4444")
                        )
                        fig_hist.update_layout(
                            template=plotly_theme,
                            height=420,
                            margin=dict(l=20, r=20, t=40, b=20),
                            separators=",."
                        )
                        st.plotly_chart(fig_hist, width="stretch")
                        st.caption("*💡 Exibição focada no intervalo de 0 a 12σ (onde se concentram 98,3% das seções). Casos extremos são consolidados na borda direita.*")
    
        # ==========================================
        # TABELA FORENSE RANKING DAS SEÇÕES
        # ==========================================
        st.subheader("📋 Ranking Detalhado das Seções Auditadas (Ordenado por Desvio Padronizado)")
    
        colunas_display = [
            "regiao", "uf", "municipio_nome", "zona", "secao", "total_votos_log", "votos_apos_17h", "pct_apos_17h",
            "esp_pos17_pct", "z_pos17", "ultimo_voto", "pct_manual_pos17h", "z_manual", "vencedor_display", "delta_display",
            "votos_cand_13", "votos_cand_22", "z_composto", "motivos_alerta"
        ]
    
        nomes_amigaveis = {
            "regiao": "Região",
            "uf": "UF",
            "municipio_nome": "Município",
            "zona": "Zona",
            "secao": "Seção",
            "total_votos_log": "Total Votos",
            "votos_apos_17h": "Pós-17h",
            "pct_apos_17h": "% Pós-17h",
            "esp_pos17_pct": "% Esp. Mun.",
            "z_pos17": "Z Pós-17h",
            "ultimo_voto": "Último Voto",
            "pct_manual_pos17h": "% Manual Pós",
            "z_manual": "Z Manual",
            "vencedor_display": "Mais Votado Pres.",
            "delta_display": "Δ vs Zona",
            "votos_cand_13": "Lula (13)",
            "votos_cand_22": "Flávio Bolsonaro (22)",
            "z_composto": "Desvio (Z)",
            "motivos_alerta": "Alertas Estatísticos & Forenses"
        }
    
        df_tabela = df_filtrado[colunas_display].rename(columns=nomes_amigaveis)
        df_tabela = df_tabela.sort_values(by=["Desvio (Z)", "Pós-17h"], ascending=[False, False])
        df_tabela = df_tabela.reset_index(drop=True)
        df_tabela.insert(0, "#", range(1, len(df_tabela) + 1))
    
        total_filtradas = len(df_tabela)
        if total_filtradas > 1000:
            df_tabela_display = df_tabela.head(1000)
            st.caption(f"📋 Exibindo as **1.000 seções prioritárias** com maior desvio padronizado Z (de um total de **{fmt_int_br(total_filtradas)}** seções filtradas).")
        else:
            df_tabela_display = df_tabela
    
        st.dataframe(
            df_tabela_display,
            width="stretch",
            height=400,
            hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn(
                    "#",
                    help="Posição no ranking de anomalia forense (1º = seção com maior desvio estatístico Z).",
                    format="%d",
                    width="small"
                ),
                "Região": st.column_config.TextColumn(
                    "Região",
                    help="Região geográfica do Brasil correspondente à seção eleitoral.",
                    width="small"
                ),
                "UF": st.column_config.TextColumn(
                    "UF",
                    help="Sigla da Unidade Federativa (Estado) onde a seção eleitoral operou.",
                    width="small"
                ),
                "Município": st.column_config.TextColumn(
                    "Município",
                    help="Nome oficial do município da seção eleitoral auditada."
                ),
                "Zona": st.column_config.NumberColumn(
                    "Zona",
                    help="Número da Zona Eleitoral da Justiça Eleitoral responsável pela circunscrição.",
                    format="%d",
                    width="small"
                ),
                "Seção": st.column_config.NumberColumn(
                    "Seção",
                    help="Número identificador oficial da seção eleitoral.",
                    format="%d",
                    width="small"
                ),
                "Total Votos": st.column_config.NumberColumn(
                    "Total Votos",
                    help="Total de eleitores que compareceram e registraram voto no log oficial da urna eletrônica.",
                    format="%d"
                ),
                "Pós-17h": st.column_config.NumberColumn(
                    "Pós-17h",
                    help="Quantidade absoluta de votos concluídos após o encerramento regular (17:00:00).",
                    format="%d"
                ),
                "% Pós-17h": st.column_config.NumberColumn(
                    "% Pós-17h",
                    help="Proporção de eleitores da seção que votaram após as 17h em relação ao comparecimento total.",
                    format="%.1f%%"
                ),
                "% Esp. Mun.": st.column_config.NumberColumn(
                    "% Esp. Mun.",
                    help="Proporção de votos pós-17h esperada para o município, calculada pelo método Leave-One-Out (Spiegelhalter 2005).",
                    format="%.1f%%"
                ),
                "Z Pós-17h": st.column_config.NumberColumn(
                    "Z Pós-17h",
                    help="Desvio estatístico padronizado (em sigmas σ) do volume pós-17h em relação ao município/UF.",
                    format="+%.1fσ"
                ),
                "Último Voto": st.column_config.TextColumn(
                    "Último Voto",
                    help="Horário exato (HH:MM:SS) em que o último eleitor concluiu seu voto e encerrou o fluxo da urna."
                ),
                "% Manual Pós": st.column_config.NumberColumn(
                    "% Manual Pós",
                    help="Percentual de eleitores pós-17h habilitados pelo mesário com código manual (dispensa de biometria).",
                    format="%.1f%%"
                ),
                "Z Manual": st.column_config.NumberColumn(
                    "Z Manual",
                    help="Desvio estatístico padronizado (em sigmas σ) da habilitação manual em relação ao município/UF.",
                    format="+%.1fσ"
                ),
                "Mais Votado Pres.": st.column_config.TextColumn(
                    "Mais Votado Pres.",
                    help="Candidato a Presidente com maior votação nominal apurada no Boletim de Urna (BU) oficial da seção."
                ),
                "Δ vs Zona": st.column_config.TextColumn(
                    "Δ vs Zona",
                    help="Desvio percentual (pontos percentuais) do candidato mais votado na seção em relação à média ponderada de todas as seções da sua Zona Eleitoral."
                ),
                "Lula (13)": st.column_config.NumberColumn(
                    "Lula (13)",
                    help="Total de votos nominais recebidos por Lula (13) no Boletim de Urna (BU) oficial da seção.",
                    format="%d"
                ),
                "Flávio Bolsonaro (22)": st.column_config.NumberColumn(
                    "Flávio Bolsonaro (22)",
                    help="Total de votos nominais recebidos por Flávio Bolsonaro (22) no Boletim de Urna (BU) oficial da seção.",
                    format="%d"
                ),
                "Desvio (Z)": st.column_config.NumberColumn(
                    "Desvio (Z-Score)",
                    help="Magnitude do desvio estatístico multivariado (Norma Euclidiana L2 em sigmas σ), integrando pós-17h, manual e horário.",
                    format="+%.1fσ"
                ),
                "Alertas Estatísticos & Forenses": st.column_config.TextColumn(
                    "Alertas Estatísticos & Forenses",
                    help="Gatilhos forenses e padrões atípicos confirmados pela inferência estatística de Spiegelhalter (2005)."
                ),
            }
        )
    
        # Download CSV completo
        csv = df_tabela.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Baixar Todas as {fmt_int_br(total_filtradas)} Seções Filtradas (CSV)",
            data=csv,
            file_name=f"auditoria_eleicoes_2026_{uf_selecionada}.csv",
            mime="text/csv"
        )
    
        st.markdown("---")
        st.markdown("<p style='margin-top: -1.1rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Versão 2.3.0</p>", unsafe_allow_html=True)
    

    
