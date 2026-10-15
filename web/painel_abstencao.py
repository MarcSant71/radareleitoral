"""
Módulo de Visualização e Auditoria de Abstenção & Comparecimento Eleitoral.
Implementa o painel de análise com o Modelo de Funil de Spiegelhalter (2005),
distribuição por faixas, comparativo regional/estadual e ranking forense de seções.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def renderizar_painel_abstencao(
    df: pd.DataFrame,
    modo_escuro: bool,
    plotly_theme: str,
    fmt_int_br,
    fmt_float_br
):
    """
    Renderiza o painel completo de Análise de Abstenção e Comparecimento,
    mantendo rigorosamente a identidade visual e os componentes de design do sistema.
    """
    if df.empty or "total_aptos" not in df.columns:
        st.warning("⚠️ Os dados de abstenção e comparecimento ainda não foram processados ou estão vazios.")
        return

    # Garante que as colunas de abstenção existam
    if "pct_abstencao" not in df.columns:
        df["pct_abstencao"] = (df["faltosos_bu"] * 100.0 / np.maximum(df["total_aptos"], 1)).round(2)
    if "pct_comparecimento" not in df.columns:
        df["pct_comparecimento"] = (df["comparecimento_bu"] * 100.0 / np.maximum(df["total_aptos"], 1)).round(2)

    OPCOES_NAV_ABST = [
        "📉 Análise de Abstenção & Comparecimento",
        "ℹ️ Sobre este Painel (Metodologia e Funil)"
    ]

    if "aba_abstencao" in st.query_params:
        if st.query_params["aba_abstencao"].lower() in ["sobre", "metodologia", "funil"]:
            st.session_state["aba_ativa_abstencao"] = OPCOES_NAV_ABST[1]
        else:
            st.session_state["aba_ativa_abstencao"] = OPCOES_NAV_ABST[0]
    elif "aba_ativa_abstencao" not in st.session_state:
        st.session_state["aba_ativa_abstencao"] = OPCOES_NAV_ABST[0]

    def _ir_para_resultados_abst():
        st.session_state["aba_ativa_abstencao"] = OPCOES_NAV_ABST[0]

    # ==========================================
    # FILTROS LATERAIS (SIDEBAR)
    # ==========================================
    st.sidebar.header("🔍 Filtros de Abstenção")

    col_reg, col_uf = st.sidebar.columns([3, 2])
    regioes_disponiveis = ["Todas", "Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]
    regiao_selecionada = col_reg.selectbox(
        "Região:",
        regioes_disponiveis,
        on_change=_ir_para_resultados_abst,
        key="abst_regiao"
    )

    df_filtrado = df.copy()
    if regiao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["regiao"] == regiao_selecionada]

    # Filtro Estado (UF) em cascata da região
    ufs_disponiveis = ["Todas"] + sorted(df_filtrado["uf"].unique().tolist())
    uf_selecionada = col_uf.selectbox(
        "UF:",
        ufs_disponiveis,
        on_change=_ir_para_resultados_abst,
        key="abst_uf"
    )
    if uf_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["uf"] == uf_selecionada]

    # Filtro Município
    municipios_disponiveis = ["Todos"] + sorted(df_filtrado["municipio_display"].unique().tolist())
    municipio_selecionado = st.sidebar.selectbox(
        "Município:",
        municipios_disponiveis,
        on_change=_ir_para_resultados_abst,
        key="abst_municipio"
    )
    if municipio_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["municipio_display"] == municipio_selecionado]

    # Filtro Zona e Seção
    col_zona, col_secao = st.sidebar.columns(2)
    zonas_disponiveis = ["Todas"] + sorted(df_filtrado["zona"].unique().tolist())
    zona_selecionada = col_zona.selectbox(
        "Zona:",
        zonas_disponiveis,
        on_change=_ir_para_resultados_abst,
        key="abst_zona"
    )
    if zona_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["zona"] == zona_selecionada]

    secoes_disponiveis = ["Todas"] + sorted(df_filtrado["secao"].unique().tolist())
    secao_selecionada = col_secao.selectbox(
        "Seção:",
        secoes_disponiveis,
        on_change=_ir_para_resultados_abst,
        key="abst_secao"
    )
    if secao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["secao"] == secao_selecionada]

    # Filtros de Atipicidade do Funil
    OPCOES_ATIP_ABST = {
        "Todas as Seções (Visão Geral)": "todas",
        "🟡 Atenção: Desvio Moderado (|Z| ≥ 2.0σ)": "mod_abs",
        "🟠 Alta Atipicidade (|Z| ≥ 3.0σ)": "alta_abs",
        "🔴 Baixa Abstenção Anômala (Z ≤ -2.0σ)": "baixa_2",
        "🚨 Baixa Abstenção Extrema (Z ≤ -3.0σ)": "baixa_3"
    }
    atip_selecionada = st.sidebar.selectbox(
        "Nível de Atipicidade do Funil:",
        list(OPCOES_ATIP_ABST.keys()),
        on_change=_ir_para_resultados_abst,
        key="abst_atipicidade",
        help="Filtra as seções de acordo com o desvio padronizado no Modelo de Spiegelhalter (2005) em relação ao esperado para o município."
    )
    modo_atip = OPCOES_ATIP_ABST[atip_selecionada]

    # Filtro de Faixa de Abstenção
    OPCOES_FAIXA_ABST = {
        "Qualquer taxa de abstenção": (0.0, 100.0),
        "Abstenção Crítica / Baixíssima (≤ 10%)": (0.0, 10.0),
        "Abstenção Baixa (10% a 15%)": (10.0, 15.0),
        "Abstenção Padrão (15% a 25%)": (15.0, 25.0),
        "Abstenção Elevada (≥ 25%)": (25.0, 100.0),
        "Abstenção Extrema (≥ 35%)": (35.0, 100.0)
    }
    faixa_selecionada = st.sidebar.selectbox(
        "Faixa de Abstenção:",
        list(OPCOES_FAIXA_ABST.keys()),
        on_change=_ir_para_resultados_abst,
        key="abst_faixa_sel",
        help="Filtra seções pelo percentual de eleitores faltosos."
    )
    faixa_min, faixa_max = OPCOES_FAIXA_ABST[faixa_selecionada]

    with st.sidebar.expander("⚙️ Ajuste Fino Estatístico"):
        slider_abst = st.slider(
            "Faixa Exata de Abstenção (%):",
            min_value=0.0,
            max_value=100.0,
            value=(float(faixa_min), float(faixa_max)),
            step=1.0,
            on_change=_ir_para_resultados_abst,
            key="abst_slider_faixa",
            help="Delimita o intervalo de taxa de abstenção das seções."
        )
        z_min_slider = st.slider(
            "Desvio Mínimo no Funil (|Z| em σ):",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            on_change=_ir_para_resultados_abst,
            key="abst_slider_z",
            help="Filtra a magnitude mínima do desvio em sigmas em relação à média esperada."
        )

    # Aplicação dos Filtros
    f_min = max(faixa_min, slider_abst[0])
    f_max = min(faixa_max, slider_abst[1])
    df_filtrado = df_filtrado[(df_filtrado["pct_abstencao"] >= f_min) & (df_filtrado["pct_abstencao"] <= f_max)]

    if modo_atip == "mod_abs":
        df_filtrado = df_filtrado[df_filtrado["z_abstencao"].abs() >= 2.0]
    elif modo_atip == "alta_abs":
        df_filtrado = df_filtrado[df_filtrado["z_abstencao"].abs() >= 3.0]
    elif modo_atip == "baixa_2":
        df_filtrado = df_filtrado[df_filtrado["z_abstencao"] <= -2.0]
    elif modo_atip == "baixa_3":
        df_filtrado = df_filtrado[df_filtrado["z_abstencao"] <= -3.0]

    if z_min_slider > 0:
        df_filtrado = df_filtrado[df_filtrado["z_abstencao"].abs() >= z_min_slider]

    # Checkbox de alertas
    apenas_com_alertas_abst = st.sidebar.checkbox(
        "Mostrar apenas seções com alertas de abstenção",
        value=False,
        on_change=_ir_para_resultados_abst,
        key="abst_apenas_alertas",
        help="Filtra apenas seções onde o desvio padronizado de abstenção foi sinalizado como atípico (|Z| ≥ 2.0σ ou abstenção ≤ 5%)."
    )
    if apenas_com_alertas_abst:
        df_filtrado = df_filtrado[(df_filtrado["z_abstencao"].abs() >= 2.0) | (df_filtrado["pct_abstencao"] <= 5.0)]

    # Filtro Vencedor da Seção
    venc_options = ["Todos", "Nº 13 (Lula)", "Nº 22 (Flávio Bolsonaro)"]
    venc_sel = st.sidebar.selectbox(
        "Mais Votado na Seção (Presidente):",
        venc_options,
        on_change=_ir_para_resultados_abst,
        key="abst_venc_sel",
        help="Filtra seções onde o candidato selecionado obteve a maioria dos votos nominais no Boletim de Urna."
    )
    if venc_sel == "Nº 13 (Lula)":
        df_filtrado = df_filtrado[df_filtrado["pres_venc_num"] == 13]
    elif venc_sel == "Nº 22 (Flávio Bolsonaro)":
        df_filtrado = df_filtrado[df_filtrado["pres_venc_num"] == 22]

    # ==========================================
    # NAVEGAÇÃO PRINCIPAL (CONTROLADA POR ESTADO)
    # ==========================================
    aba_selecionada = st.segmented_control(
        "Navegação",
        options=OPCOES_NAV_ABST,
        key="aba_ativa_abstencao",
        selection_mode="single",
        required=True,
        label_visibility="collapsed",
        width="stretch"
    )
    if not aba_selecionada:
        aba_selecionada = OPCOES_NAV_ABST[0]

    if aba_selecionada == OPCOES_NAV_ABST[0]:
        # ==========================================
        # INSPEÇÃO INDIVIDUAL DE SEÇÃO
        # ==========================================
        if secao_selecionada != "Todas" and len(df_filtrado) == 1:
            r = df_filtrado.iloc[0]
            st.info(
                f"🔍 **Seção {r['secao']} (Zona {r['zona']} - {r['municipio_nome']}/{r['uf']}):** "
                f"Aptos: **{fmt_int_br(r['total_aptos'])}** | "
                f"Comparecimento: **{fmt_int_br(r['comparecimento_bu'])}** ({fmt_float_br(r['pct_comparecimento'])}%) | "
                f"Abstenção: **{fmt_int_br(r['faltosos_bu'])} faltosos ({fmt_float_br(r['pct_abstencao'])}%)** | "
                f"Esperado do Município: **{fmt_float_br(r['esp_abstencao_pct'])}%** | "
                f"Desvio no Funil: **{r['z_abstencao']:+.1f}σ** | "
                f"Classificação: **{r['nivel_abstencao']}** | "
                f"Alerta: **{r['motivos_alerta_abst']}**"
            )
            if pd.notna(r.get("pres_venc_num")) and r.get("pres_total_validos", 0) > 0:
                v_num = int(r["pres_venc_num"])
                v_label = "Lula (13)" if v_num == 13 else ("Flávio Bolsonaro (22)" if v_num == 22 else f"Nº {v_num}")
                st.success(
                    f"🗳️ **Boletim de Urna (BU):** Mais Votado: **{v_label}** com **{fmt_int_br(r['pres_venc_votos'])} votos ({fmt_float_br(r['pres_venc_pct'])}%)** | "
                    f"Votos Válidos: **{fmt_int_br(r['pres_total_validos'])}** | "
                    f"Brancos: **{fmt_int_br(r['pres_brancos'])}** | Nulos: **{fmt_int_br(r['pres_nulos'])}**"
                )

        # ==========================================
        # CARDS DE KPI (MÉTRICAS GERAIS)
        # ==========================================
        total_secoes = len(df_filtrado)
        tot_aptos = df_filtrado["total_aptos"].sum() if total_secoes > 0 else 0
        tot_comp = df_filtrado["comparecimento_bu"].sum() if total_secoes > 0 else 0
        tot_falt = df_filtrado["faltosos_bu"].sum() if total_secoes > 0 else 0
        pct_comp_geral = (tot_comp * 100.0 / tot_aptos) if tot_aptos > 0 else 0.0
        pct_falt_geral = (tot_falt * 100.0 / tot_aptos) if tot_aptos > 0 else 0.0
        
        # Baixa abstenção anômala (desvio severo ou comparecimento superior a 90% em seção com >50 eleitores)
        baixa_anomala = len(df_filtrado[(df_filtrado["z_abstencao"] <= -2.0) | (df_filtrado["pct_abstencao"] <= 10.0)])
        media_abst_secoes = df_filtrado["pct_abstencao"].mean() if total_secoes > 0 else 0.0

        with st.container(key="kpi_metrics"):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(
                "Eleitores Aptos",
                fmt_int_br(tot_aptos),
                f"{fmt_int_br(total_secoes)} seções",
                help="Quantidade total de eleitores aptos a votar nas seções filtradas nesta consulta."
            )
            c2.metric(
                "Comparecimento Total",
                fmt_int_br(tot_comp),
                f"{fmt_float_br(pct_comp_geral)}% do total",
                help="Volume e percentual de eleitores que compareceram e votaram nas urnas das seções selecionadas."
            )
            c3.metric(
                "Abstenção Geral",
                fmt_int_br(tot_falt),
                f"{fmt_float_br(pct_falt_geral)}% do total",
                help="Total e taxa agregada de eleitores faltosos (abstenção) em relação ao total de eleitores aptos."
            )
            c4.metric(
                "Baixa Abstenção Anômala",
                fmt_int_br(baixa_anomala),
                f"Z ≤ -2σ ou ≤ 10%",
                help="Seções onde a taxa de abstenção foi significativamente inferior ao padrão municipal (Z ≤ -2.0σ no modelo de Spiegelhalter ou ≤ 10%)."
            )
            c5.metric(
                "Taxa Média por Seção",
                f"{fmt_float_br(media_abst_secoes)}%",
                f"Média aritmética",
                help="Média simples da taxa de abstenção percentual entre todas as seções atualmente filtradas."
            )

        st.markdown("---")

        # ==========================================
        # GRÁFICOS ANALÍTICOS (ALINHAMENTO SIMÉTRICO)
        # ==========================================
        with st.container(key="graficos_container"):
            c_top1, c_top2 = st.columns([1, 1])
            with c_top1:
                st.markdown("<p style='font-size: 0.92rem; font-weight: 500; color: #8b949e; margin-top: 14px; margin-bottom: 0;'>📈 Funil de Dispersão Estatística (Spiegelhalter 2005)</p>", unsafe_allow_html=True)
            with c_top2:
                modo_distribuicao = st.radio(
                    "Tipo de Gráfico (Distribuição):",
                    options=["📊 Faixas de Abstenção", "🔬 Histograma (% Abstenção)"],
                    index=0,
                    horizontal=True,
                    key="modo_dist_abst",
                    help="Escolha entre a visão simplificada por Faixas Percentuais ou o Histograma detalhado de distribuição contínua da abstenção."
                )

            col_funil, col_dist = st.columns([1, 1])

            # ------------------------------------------
            # GRÁFICO 1: FUNIL DE SPIEGELHALTER (2005)
            # ------------------------------------------
            with col_funil:
                if total_secoes > 0:
                    # Amostragem para alta performance visual caso haja > 15.000 seções
                    if total_secoes > 15000:
                        df_funil_sample = df_filtrado.sample(15000, random_state=42)
                        subtitulo_amostra = f" (Amostra de 15.000 de {fmt_int_br(total_secoes)} seções)"
                    else:
                        df_funil_sample = df_filtrado
                        subtitulo_amostra = ""

                    p_bar = (tot_falt / tot_aptos) if tot_aptos > 0 else 0.2077
                    # Determina o domínio do eixo X (Aptos)
                    x_min = max(30, int(df_funil_sample["total_aptos"].min()))
                    x_max = min(600, int(df_funil_sample["total_aptos"].max()) + 20)
                    if x_min >= x_max:
                        x_min, x_max = 30, 500

                    n_curvas = np.linspace(x_min, x_max, 120)
                    # Estimativa de superdispersão tau² do conjunto
                    tau2_est = 0.0006
                    sigma_n = np.sqrt((p_bar * (1.0 - p_bar) / n_curvas) + tau2_est)
                    u95 = (p_bar + 1.96 * sigma_n) * 100.0
                    l95 = np.maximum(0.0, (p_bar - 1.96 * sigma_n) * 100.0)
                    u99 = (p_bar + 3.09 * sigma_n) * 100.0
                    l99 = np.maximum(0.0, (p_bar - 3.09 * sigma_n) * 100.0)

                    fig_funil = go.Figure()

                    # Faixas de Controle do Funil
                    fig_funil.add_trace(go.Scatter(
                        x=n_curvas, y=u99,
                        mode="lines",
                        line=dict(color="#f85149", width=1.5, dash="dash"),
                        name="+3.09σ (IC 99.8%)",
                        hoverinfo="skip"
                    ))
                    fig_funil.add_trace(go.Scatter(
                        x=n_curvas, y=u95,
                        mode="lines",
                        line=dict(color="#d29922", width=1.5, dash="dot"),
                        name="+1.96σ (IC 95.0%)",
                        hoverinfo="skip"
                    ))
                    fig_funil.add_trace(go.Scatter(
                        x=n_curvas, y=[p_bar * 100.0] * len(n_curvas),
                        mode="lines",
                        line=dict(color="#58a6ff" if modo_escuro else "#0969da", width=2.0),
                        name=f"Média Ponderada ({p_bar*100.0:.1f}%)",
                        hoverinfo="skip"
                    ))
                    fig_funil.add_trace(go.Scatter(
                        x=n_curvas, y=l95,
                        mode="lines",
                        line=dict(color="#d29922", width=1.5, dash="dot"),
                        name="-1.96σ (IC 95.0%)",
                        hoverinfo="skip"
                    ))
                    fig_funil.add_trace(go.Scatter(
                        x=n_curvas, y=l99,
                        mode="lines",
                        line=dict(color="#f85149", width=1.5, dash="dash"),
                        name="-3.09σ (IC 99.8%)",
                        hoverinfo="skip"
                    ))

                    # Pontos das Seções
                    # Mapeia cores: Vermelho/Coral para Lula (13), Verde para Bolsonaro (22), Cinza para outros
                    def _cor_ponto(row):
                        if row.get("z_abstencao", 0) <= -2.0:
                            return "#f85149"  # Alerta vermelho de baixa abstenção extrema
                        v_num = row.get("pres_venc_num")
                        if v_num == 13:
                            return "#ff7b72" if modo_escuro else "#cf222e"
                        elif v_num == 22:
                            return "#3fb950" if modo_escuro else "#1a7f37"
                        return "#79c0ff" if modo_escuro else "#0969da"

                    cores = [_cor_ponto(r) for _, r in df_funil_sample.iterrows()]

                    fig_funil.add_trace(go.Scatter(
                        x=df_funil_sample["total_aptos"],
                        y=df_funil_sample["pct_abstencao"],
                        mode="markers",
                        marker=dict(
                            size=4.5,
                            color=cores,
                            opacity=0.6,
                            line=dict(width=0)
                        ),
                        customdata=np.stack([
                            df_funil_sample["uf"],
                            df_funil_sample["municipio_nome"],
                            df_funil_sample["zona"],
                            df_funil_sample["secao"],
                            df_funil_sample["faltosos_bu"],
                            df_funil_sample["z_abstencao"],
                            df_funil_sample["vencedor_display"]
                        ], axis=-1),
                        hovertemplate=(
                            "<b>Seção %{customdata[3]} (Zona %{customdata[2]} - %{customdata[1]}/%{customdata[0]})</b><br>"
                            "Aptos: %{x:,}<br>"
                            "Abstenção: %{customdata[4]:,} faltosos (<b>%{y:.1f}%</b>)<br>"
                            "Desvio no Funil: <b>%{customdata[5]:+.1f}σ</b><br>"
                            "Mais Votado: %{customdata[6]}"
                            "<extra></extra>"
                        ),
                        name="Seções Eleitorais"
                    ))

                    fig_funil.update_layout(
                        title=dict(
                            text=f"Funil de Abstenção vs Tamanho da Seção{subtitulo_amostra}",
                            font=dict(size=14)
                        ),
                        xaxis=dict(
                            title="Total de Eleitores Aptos na Seção (n)",
                            showgrid=True,
                            gridcolor="#21262d" if modo_escuro else "#e1e4e8"
                        ),
                        yaxis=dict(
                            title="Taxa de Abstenção (%)",
                            showgrid=True,
                            gridcolor="#21262d" if modo_escuro else "#e1e4e8",
                            range=[0, min(65, float(df_funil_sample["pct_abstencao"].quantile(0.999) + 5))]
                        ),
                        template=plotly_theme,
                        height=420,
                        margin=dict(l=40, r=20, t=45, b=40),
                        showlegend=False
                    )
                    st.plotly_chart(fig_funil, use_container_width=True)
                else:
                    st.warning("Nenhuma seção encontrada com os filtros selecionados.")

            # ------------------------------------------
            # GRÁFICO 2: DISTRIBUIÇÃO DA ABSTENÇÃO
            # ------------------------------------------
            with col_dist:
                if total_secoes > 0:
                    if modo_distribuicao == "📊 Faixas de Abstenção":
                        bins_labels = [
                            "< 10% (Baixíssima)",
                            "10% – 15% (Baixa)",
                            "15% – 20% (Moderada)",
                            "20% – 25% (Padrão Nacional)",
                            "25% – 30% (Elevada)",
                            "≥ 30% (Muito Elevada)"
                        ]
                        bins_edges = [-0.1, 10.0, 15.0, 20.0, 25.0, 30.0, 100.1]
                        faixas_series = pd.cut(df_filtrado["pct_abstencao"], bins=bins_edges, labels=bins_labels)
                        df_faixas = faixas_series.value_counts()[bins_labels].reset_index()
                        df_faixas.columns = ["Faixa", "Qtd"]
                        df_faixas["Pct"] = (df_faixas["Qtd"] / total_secoes * 100.0).round(1)

                        cores_faixas = [
                            "#f85149",  # < 10% (Alerta de baixa)
                            "#79c0ff",  # 10 - 15%
                            "#388bfd",  # 15 - 20%
                            "#1f6feb",  # 20 - 25%
                            "#d29922",  # 25 - 30%
                            "#da3633"   # >= 30%
                        ]

                        fig_dist = go.Figure(data=[
                            go.Bar(
                                x=df_faixas["Faixa"],
                                y=df_faixas["Qtd"],
                                marker_color=cores_faixas,
                                text=[f"{q:,}<br>({p:.1f}%)" for q, p in zip(df_faixas["Qtd"], df_faixas["Pct"])],
                                textposition="auto",
                                hovertemplate="<b>%{x}</b><br>Quantidade: %{y:,} seções<br>Proporção: %{text}<extra></extra>"
                            )
                        ])
                        fig_dist.update_layout(
                            title=dict(text="Distribuição por Faixas de Abstenção", font=dict(size=14)),
                            xaxis=dict(title=None, tickangle=-15),
                            yaxis=dict(
                                title="Número de Seções",
                                showgrid=True,
                                gridcolor="#21262d" if modo_escuro else "#e1e4e8"
                            ),
                            template=plotly_theme,
                            height=420,
                            margin=dict(l=40, r=20, t=45, b=40)
                        )
                        st.plotly_chart(fig_dist, use_container_width=True)
                    else:
                        # Histograma contínuo
                        fig_hist = px.histogram(
                            df_filtrado,
                            x="pct_abstencao",
                            nbins=40,
                            template=plotly_theme,
                            color_discrete_sequence=["#58a6ff" if modo_escuro else "#0969da"]
                        )
                        fig_hist.add_vline(
                            x=float(pct_falt_geral),
                            line_width=2,
                            line_dash="dash",
                            line_color="#f85149",
                            annotation_text=f"Média: {pct_falt_geral:.1f}%",
                            annotation_position="top right"
                        )
                        fig_hist.update_layout(
                            title=dict(text="Histograma Contínuo da Taxa de Abstenção (%)", font=dict(size=14)),
                            xaxis=dict(
                                title="Abstenção (%) na Seção",
                                showgrid=True,
                                gridcolor="#21262d" if modo_escuro else "#e1e4e8"
                            ),
                            yaxis=dict(
                                title="Frequência (Nº de Seções)",
                                showgrid=True,
                                gridcolor="#21262d" if modo_escuro else "#e1e4e8"
                            ),
                            height=420,
                            margin=dict(l=40, r=20, t=45, b=40)
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.warning("Sem dados para distribuição.")

        st.markdown("---")

        # ==========================================
        # COMPARATIVO REGIONAL / ESTADUAL
        # ==========================================
        with st.container():
            st.markdown("<p style='font-size: 0.92rem; font-weight: 500; color: #8b949e; margin-bottom: 8px;'>🗺️ Comparativo Geográfico de Abstenção</p>", unsafe_allow_html=True)
            
            # Se uma única UF estiver selecionada, agrupa por município (top 20)
            if uf_selecionada != "Todas":
                df_geo = df_filtrado.groupby("municipio_nome", observed=True).agg(
                    total_aptos=("total_aptos", "sum"),
                    faltosos_bu=("faltosos_bu", "sum"),
                    secoes=("secao", "count")
                ).reset_index()
                df_geo["pct_abstencao"] = (df_geo["faltosos_bu"] * 100.0 / df_geo["total_aptos"]).round(2)
                df_geo = df_geo[df_geo["secoes"] >= 3].sort_values("pct_abstencao", ascending=True).tail(25)
                titulo_geo = f"Top Municípios com Maior Abstenção em {uf_selecionada}"
                eixo_y_nome = "Município"
            else:
                # Agrupa por UF
                df_geo = df_filtrado.groupby("uf", observed=True).agg(
                    total_aptos=("total_aptos", "sum"),
                    faltosos_bu=("faltosos_bu", "sum"),
                    secoes=("secao", "count")
                ).reset_index()
                df_geo["pct_abstencao"] = (df_geo["faltosos_bu"] * 100.0 / df_geo["total_aptos"]).round(2)
                df_geo = df_geo.sort_values("pct_abstencao", ascending=True)
                titulo_geo = "Taxa de Abstenção Oficial por Estado (UF)"
                eixo_y_nome = "UF"

            fig_geo = go.Figure(data=[
                go.Bar(
                    x=df_geo["pct_abstencao"],
                    y=df_geo[df_geo.columns[0]],
                    orientation="h",
                    marker=dict(
                        color=df_geo["pct_abstencao"],
                        colorscale="Blues" if not modo_escuro else "Viridis",
                        showscale=False
                    ),
                    text=[f"{v:.1f}%" for v in df_geo["pct_abstencao"]],
                    textposition="outside",
                    hovertemplate=f"<b>%{{y}}</b><br>Abstenção: <b>%{{x:.2f}}%</b><br>Eleitores Aptos: %{{customdata[0]:,}}<br>Faltosos: %{{customdata[1]:,}}<extra></extra>",
                    customdata=np.stack([df_geo["total_aptos"], df_geo["faltosos_bu"]], axis=-1)
                )
            ])
            fig_geo.add_vline(
                x=float(pct_falt_geral),
                line_width=1.5,
                line_dash="dot",
                line_color="#f85149",
                annotation_text=f"Média Nacional/Filtro ({pct_falt_geral:.1f}%)",
                annotation_position="top right"
            )
            fig_geo.update_layout(
                title=dict(text=titulo_geo, font=dict(size=14)),
                xaxis=dict(
                    title="Taxa de Abstenção (%)",
                    showgrid=True,
                    gridcolor="#21262d" if modo_escuro else "#e1e4e8"
                ),
                yaxis=dict(title=None, dtick=1),
                template=plotly_theme,
                height=max(360, len(df_geo) * 22),
                margin=dict(l=60, r=40, t=45, b=40)
            )
            st.plotly_chart(fig_geo, use_container_width=True)

        st.markdown("---")

        # ==========================================
        # TABELA DE SEÇÕES SINALIZADAS / RANKING
        # ==========================================
        st.subheader("📋 Seções Sinalizadas & Ranking Forense de Abstenção")
        st.markdown(
            "Tabela detalhada de seções eleitorais com foco em desvios do Modelo de Funil de Spiegelhalter (2005) e identificação objetiva de atipicidades."
        )

        # Ordenação padrão: seções com baixa abstenção anômala primeiro (Z ascendente) ou desvio absoluto
        colunas_exibicao = [
            "uf", "municipio_nome", "zona", "secao",
            "total_aptos", "comparecimento_bu", "faltosos_bu",
            "pct_abstencao", "esp_abstencao_pct", "z_abstencao",
            "nivel_abstencao", "vencedor_display", "motivos_alerta_abst"
        ]
        
        # Filtra apenas colunas presentes
        cols_presentes = [c for c in colunas_exibicao if c in df_filtrado.columns]
        df_ranking = df_filtrado[cols_presentes].copy()
        df_ranking = df_ranking.sort_values("z_abstencao", ascending=True)

        col_config = {
            "uf": st.column_config.TextColumn("UF", width="small", help="Unidade Federativa."),
            "municipio_nome": st.column_config.TextColumn("Município", width="medium", help="Nome do município."),
            "zona": st.column_config.TextColumn("Zona", width="small", help="Número da Zona Eleitoral."),
            "secao": st.column_config.TextColumn("Seção", width="small", help="Número da Seção Eleitoral."),
            "total_aptos": st.column_config.NumberColumn("Aptos", format="%d", help="Total de eleitores cadastrados e aptos."),
            "comparecimento_bu": st.column_config.NumberColumn("Comparecimento", format="%d", help="Total de eleitores que votaram."),
            "faltosos_bu": st.column_config.NumberColumn("Abstenção", format="%d", help="Quantidade de faltosos."),
            "pct_abstencao": st.column_config.NumberColumn("Abstenção (%)", format="%.2f%%", help="Taxa percentual de faltosos na seção."),
            "esp_abstencao_pct": st.column_config.NumberColumn("Esperado (%)", format="%.1f%%", help="Taxa média esperada calculada para o município (Leave-One-Out)."),
            "z_abstencao": st.column_config.NumberColumn("Desvio Funil (σ)", format="%+.1fσ", help="Desvio padronizado no modelo binomial superdisperso de Spiegelhalter."),
            "nivel_abstencao": st.column_config.TextColumn("Classificação", width="medium", help="Faixa de atipicidade estatística."),
            "vencedor_display": st.column_config.TextColumn("Mais Votado", width="medium", help="Candidato a Presidente com maior votação na urna."),
            "motivos_alerta_abst": st.column_config.TextColumn("Diagnóstico Forense", width="large", help="Detalhamento objetivo das razões de alerta estatístico.")
        }

        st.dataframe(
            df_ranking,
            column_config=col_config,
            use_container_width=True,
            hide_index=True,
            height=460
        )

        csv_bytes = df_ranking.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 Baixar Dados da Tabela de Abstenção em CSV",
            data=csv_bytes,
            file_name=f"abstencao_eleicoes2026_{uf_selecionada.lower()}.csv",
            mime="text/csv",
            key="btn_download_abst_csv"
        )

    elif aba_selecionada == OPCOES_NAV_ABST[1]:
        # ==========================================
        # METODOLOGIA FORENSE DE ABSTENÇÃO (SOBRE)
        # ==========================================
        st.markdown("""
        ### 📉 Caderno Metodológico: Análise Forense de Abstenção & Gráfico em Funil

        Este módulo aplica modelos matemáticos de inferência estatística para analisar a dinâmica de comparecimento e abstenção
        nas eleições brasileiras, tomando como base os dados oficiais de apuração divulgados pelo Tribunal Superior Eleitoral (TSE).

        ---

        #### 🎯 1. Por que Auditar a Abstenção Eleitoral?
        Em eleições democráticas, o comparecimento do eleitorado e a abstenção refletem o comportamento cívico regular da população.
        Historicamente, a taxa de abstenção em eleições nacionais no Brasil gravita em torno de **18% a 22%**, variando conforme o estado,
        a distância até o local de votação e condições climáticas locais.

        Em auditoria forense eleitoral internacional, a identificação de **picos anômalos de comparecimento** (*turnout spikes*) e 
        **baixa abstenção extrema** (seções com menos de 3% ou 5% de faltosos em localidades cuja média é de 20%) é um dos indicadores
        mais sensíveis para detecção de irregularidades operacionais, como preenchimento fraudulento de cédulas, ausência física de eleitores
        ou falhas na fiscalização da mesa receptora.

        ---

        #### 🔬 2. O Gráfico em Funil de David Spiegelhalter (2005)
        Para comparar taxas de abstenção de forma estatisticamente justa entre seções de tamanhos distintos (por exemplo, seções pequenas
        com 80 eleitores versus seções grandes com 450 eleitores), utilizamos a consagrada metodologia de **Funnel Plots** proposta
        por **David Spiegelhalter (2005)**.

        ##### A. O Princípio da Flutuação Amostral
        Uma seção com apenas 50 eleitores possui, por pura probabilidade binomial, uma variabilidade natural muito superior à de uma seção
        com 400 eleitores. Se em uma seção de 50 eleitores faltarem 5 pessoas (10% de abstenção), o resultado pode ter ocorrido por mero acaso.
        Porém, se em uma seção de 400 eleitores a abstenção despencar para 5% (apenas 20 faltosos quando o esperado eram 85), o desvio é
        matematicamente incomum e improvável sob a hipótese nula.

        O gráfico em funil desenha curvas de controle que se estreitam conforme o tamanho da seção ($n$) aumenta, delimitando as fronteiras
        de flutuação esperada pelo Teorema Central do Limite.

        ##### B. Formulação Matemática das Curvas de Controle
        Para uma seção com $n_i$ eleitores aptos e taxa observada de abstenção $p_i = \text{faltosos}_i / n_i$:

        **1. Variância Teórica Binomial com Superdispersão:**

        $$
        \sigma_i^2 = \frac{\bar{p}(1 - \bar{p})}{n_i} + \tau^2
        $$

        Onde:
        * $\bar{p}$ é a taxa média ponderada de abstenção do grupo de referência (município, estado ou país).
        * $n_i$ é o número de eleitores aptos da seção.
        * $\tau^2$ representa a superdispersão residual intra-UF (variação natural entre escolas e bairros), estimada de forma robusta via MAD.

        **2. Limites de Significância Estatística:**

        * **Intervalo de Confiança de 95,0% (Limite Moderado / Atenção):**
        $$
        \text{Limite}_{95\%} = \bar{p} \pm 1{,}96 \cdot \sigma_i
        $$

        * **Intervalo de Confiança de 99,8% (Limite Rigoroso / Alta Atipicidade):**
        $$
        \text{Limite}_{99{,}8\%} = \bar{p} \pm 3{,}09 \cdot \sigma_i
        $$

        ---

        #### 🔍 3. Interpretação dos Desvios e Alertas
        * **Pontos dentro das curvas amarelas ($\pm 1{,}96\sigma$):** Seções com comportamento perfeitamente típico e esperado (95% da distribuição).
        * **Pontos além da curva amarela superior ($> +1{,}96\sigma$):** Seções com abstenção acima da média local (possíveis filas, chuvas ou desinteresse).
        * **Pontos abaixo da curva vermelha inferior ($< -3{,}09\sigma$):** **O foco central da auditoria.** Seções onde quase ninguém faltou,
          exibindo taxas de comparecimento de 95% a 99% que destoam fortemente do restante da cidade.

        > [!IMPORTANT]
        > Um desvio padronizado no gráfico em funil **não constitui presunção automática de irregularidade**, mas sim um **sinalizador objetivo
        > de prioridade para verificação**. Em caso de atipicidade extrema ($Z \le -3{,}0\sigma$), a folha de presença e o caderno de votação
        > com assinaturas e confirmações biométricas devem ser checados no Cartório Eleitoral.

        ---

        #### 🛡️ 4. Privacidade, LGPD e Sigilo do Voto
        Todos os dados apresentados neste módulo são estritamente públicos, consolidados a partir do repositório de Dados Abertos do TSE
        em conformidade com a **Lei de Acesso à Informação (Lei Federal nº 12.527/2011)** e o **Art. 7º, § 4º da LGPD (Lei nº 13.709/2018)**.
        Nenhum registro individual de voto de eleitor é exposto ou inferido, preservando o sigilo constitucional preconizado no Art. 14 da CF/88.
        """)

        st.subheader("🏷️ Histórico de Versões")
        st.markdown("""
| Versão | Data | Principais Mudanças |
| :--- | :---: | :--- |
| **v2.4.0** | **15/10/2026** | **Módulo Analítico de Abstenção & Comparecimento Eleitoral:**<br>• Integração completa do painel de abstenção com modelo de Funil de Spiegelhalter (2005) e limites de controle paramétricos (95% e 99.8%).<br>• Incorporação da base oficial consolidada do TSE com 152 milhões de eleitores aptos e 472 mil seções apuradas.<br>• Detecção automatizada de seções com baixa abstenção anômala (*turnout spikes*) e geração de diagnósticos forenses objetivos.<br>• Gráficos dinâmicos de dispersão em funil, faixas de distribuição e comparativo estadual/regional.<br>• Isolamento modular da arquitetura e preservação estrita da identidade visual do sistema. |
| **v2.3.0** | **15/10/2026** | **Didática Forense & Acessibilidade Universal:**<br>• Reformulação didática do caderno metodológico com analogias conceituais (MAD, termômetro Z e norma euclidiana L2).<br>• Tooltips universais de alto contraste invertido e conformidade com critérios WCAG. |
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<p style='margin-top: -1.1rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Versão 2.4.0</p>", unsafe_allow_html=True)
