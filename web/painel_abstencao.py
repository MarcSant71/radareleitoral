"""
Módulo de Visualização e Auditoria de Abstenção & Comparecimento Eleitoral.
Implementa a suíte analítica completa inspirada na metodologia de esteleicao.com (ralbuque),
com Matriz de 21 KPIs (3 linhas x 7 colunas) e 7 Abas Analíticas integradas:
1. 📊 Comparar (Forest Plot Média ± 1σ por UF/Município + Resumo Estatístico)
2. 📈 Distribuição (Histograma 80 bins com demarcações μ, ±1σ, ±2σ)
3. 🔻 Funil (Modelo de Spiegelhalter 2005 com curvas de controle 95% e 99.8% e superdispersão tau²)
4. 🚩 Sinalizadas (Matriz Forense Multicritério com triagem e ranking por severidade)
5. ⏰ Horário dos votos (Perfil temporal 7h-23h, Forest Plot de encerramento e seções tardias)
6. 🖐️ Sem digital (Decomposição biométrica: Sem Cadastro vs Liberação Manual pelo mesário)
7. 🔀 Cruzamento (Scatter Plot bivariado com quadrante crítico sombreado e Score Cruzado)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# Paleta de cores neutras e científicas (estilo esteleicao / GitHub / Nature)
COR_DESTAQUE_VERMELHO = "#d6453d"
COR_DESTAQUE_AZUL = "#2f6fb5"
COR_NEUTRA_PONTOS = "#8b949e"
COR_BARRA_ESCURA = "#33415c"
COR_ALARME_AMARELO = "#e0a33a"
AMOSTRA_FUNDO_MAX = 5_000


def pct_br(val, casas=1) -> str:
    """Formata proporção (0.0 a 1.0 ou percentual) para string brasileira com %."""
    if val is None or pd.isna(val):
        return "—"
    try:
        f_val = float(val)
        if f_val <= 1.0 and f_val >= 0.0 and casas > 1:
            f_val = f_val * 100.0
        elif f_val <= 1.0 and f_val > 0.0:
            f_val = f_val * 100.0
        parts = f"{f_val:,.{casas}f}".split(".")
        int_part = parts[0].replace(",", ".")
        dec_part = parts[1] if len(parts) > 1 else ""
        return f"{int_part},{dec_part}%" if dec_part else f"{int_part}%"
    except (ValueError, TypeError):
        return str(val)


def hora_br(val) -> str:
    """Converte hora decimal (ex: 17.71) para formato legível '17h42'."""
    if val is None or pd.isna(val):
        return "—"
    try:
        minutos_totais = int(round(float(val) * 60))
        h = minutos_totais // 60
        m = minutos_totais % 60
        return f"{h:02d}h{m:02d}"
    except (ValueError, TypeError):
        return str(val)


def calcular_resumo_estatistico(df: pd.DataFrame, por: list[str] | None = None) -> pd.DataFrame:
    """Calcula média, desvio padrão, mediana, MAD e percentis da taxa de abstenção por grupo."""
    colunas_necessarias = list(dict.fromkeys((por or []) + ["pct_abstencao", "total_aptos", "faltosos_bu"]))
    d = df[[c for c in colunas_necessarias if c in df.columns]]

    def _agg(g):
        t = g["pct_abstencao"].dropna()
        mediana = t.median() if len(t) > 0 else np.nan
        mad = 1.4826 * (t - mediana).abs().median() if len(t) > 0 else np.nan
        tot_aptos = g["total_aptos"].sum()
        tot_falt = g["faltosos_bu"].sum()
        taxa_agregada = (tot_falt * 100.0 / tot_aptos) if tot_aptos > 0 else np.nan
        return pd.Series({
            "secoes": len(g),
            "aptos": int(tot_aptos),
            "faltosos": int(tot_falt),
            "taxa_agregada": taxa_agregada,
            "media": t.mean() if len(t) > 0 else np.nan,
            "desvio_padrao": t.std(ddof=1) if len(t) > 1 else 0.0,
            "mediana": mediana,
            "mad": mad,
            "p05": t.quantile(0.05) if len(t) > 0 else np.nan,
            "p95": t.quantile(0.95) if len(t) > 0 else np.nan,
            "minimo": t.min() if len(t) > 0 else np.nan,
            "maximo": t.max() if len(t) > 0 else np.nan,
        })

    if not por:
        return _agg(d).to_frame().T
    return d.groupby(por, observed=True).apply(_agg, include_groups=False).reset_index()


def limites_funil_spiegelhalter(p_bar: float, tau2: float, n_max: int, k: float) -> pd.DataFrame:
    """Curvas teóricas de controle do Funnel Plot com variância binomial + superdispersão residual tau²."""
    n = np.unique(np.geomspace(10, max(n_max, 50), 160).astype(int))
    p = np.clip(p_bar / 100.0, 1e-4, 1.0 - 1e-4)
    sd = np.sqrt(p * (1.0 - p) / n + tau2)
    inf = np.clip(p - k * sd, 0.0, 1.0) * 100.0
    sup = np.clip(p + k * sd, 0.0, 1.0) * 100.0
    return pd.DataFrame({"aptos": n, "inf": inf, "sup": sup})


def amostrar_para_grafico(d: pd.DataFrame, mascara_destaque: pd.Series, max_fundo: int = AMOSTRA_FUNDO_MAX) -> pd.DataFrame:
    """Mantém 100% dos pontos sinalizados e amostra o fundo cinza para renderização fluida no WebGL."""
    fundo = d[~mascara_destaque]
    if len(fundo) > max_fundo:
        fundo = fundo.sample(max_fundo, random_state=42)
    return pd.concat([fundo, d[mascara_destaque]])


def renderizar_detalhe_individual(s: pd.Series, base: pd.DataFrame, modo_escuro: bool, plotly_theme: str, fmt_int_br, fmt_float_br):
    """Renderiza a inspeção forense aprofundada de uma única seção eleitoral."""
    st.markdown(
        f"### 🔍 Seção {s['secao']} · Zona {s['zona']} · {s['municipio_nome']} / {s['uf']}"
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    delta_esp = s["pct_abstencao"] - s.get("esp_abstencao_pct", s["pct_abstencao"])
    k1.metric(
        "Abstenção da Seção",
        f"{fmt_float_br(s['pct_abstencao'])}%",
        f"{delta_esp:+.1f} pp vs esperado",
        delta_color="inverse"
    )
    k2.metric(
        "Aptos / Faltaram",
        f"{fmt_int_br(s['total_aptos'])} / {fmt_int_br(s['faltosos_bu'])}",
        f"Compareceram: {fmt_int_br(s['comparecimento_bu'])}",
        delta_color="off"
    )
    k3.metric("Z-Score Ajustado (Funil)", f"{s['z_abstencao']:+.2f}σ")
    k4.metric("Classificação", s.get("nivel_abstencao", "Normal"))
    k5.metric("Alerta Forense", s.get("motivos_alerta_abst", "Normal")[:35] + ("..." if len(str(s.get("motivos_alerta_abst", ""))) > 35 else ""))

    # Boletim de Urna (BU) caso disponível
    if pd.notna(s.get("pres_venc_num")) and s.get("pres_total_validos", 0) > 0:
        v_num = int(s["pres_venc_num"])
        v_label = "Lula (13)" if v_num == 13 else ("Flávio Bolsonaro (22)" if v_num == 22 else f"Nº {v_num}")
        st.info(
            f"🗳️ **Boletim de Urna (BU):** Mais Votado: **{v_label}** com **{fmt_int_br(s['pres_venc_votos'])} votos ({fmt_float_br(s['pres_venc_pct'])}%)** | "
            f"Válidos: **{fmt_int_br(s['pres_total_validos'])}** | Brancos: **{fmt_int_br(s.get('pres_brancos', 0))}** | Nulos: **{fmt_int_br(s.get('pres_nulos', 0))}**"
        )

    # Gráfico de barras comparativo multinível
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        zona_df = base[(base["uf"] == s["uf"]) & (base["municipio"] == s["municipio"]) & (base["zona"] == s["zona"])]
        mun_df = base[(base["uf"] == s["uf"]) & (base["municipio"] == s["municipio"])]
        uf_df = base[base["uf"] == s["uf"]]

        niveis = ["Esta Seção", f"Zona {s['zona']}", s["municipio_nome"], s["uf"], "Brasil"]
        medias = [
            float(s["pct_abstencao"]),
            float(zona_df["pct_abstencao"].mean()),
            float(mun_df["pct_abstencao"].mean()),
            float(uf_df["pct_abstencao"].mean()),
            float(base["pct_abstencao"].mean())
        ]
        desvios = [
            0.0,
            float(zona_df["pct_abstencao"].std(ddof=1)) if len(zona_df) > 1 else 0.0,
            float(mun_df["pct_abstencao"].std(ddof=1)) if len(mun_df) > 1 else 0.0,
            float(uf_df["pct_abstencao"].std(ddof=1)) if len(uf_df) > 1 else 0.0,
            float(base["pct_abstencao"].std(ddof=1)) if len(base) > 1 else 0.0
        ]

        cores_comp = [COR_DESTAQUE_AZUL if s["z_abstencao"] < 0 else COR_DESTAQUE_VERMELHO] + [COR_NEUTRA_PONTOS] * 4
        fig_comp = go.Figure(go.Bar(
            x=niveis,
            y=medias,
            error_y=dict(type="data", array=desvios, visible=True, color="#9aa4b1"),
            marker_color=cores_comp,
            text=[f"{m:.1f}%" for m in medias],
            textposition="outside"
        ))
        fig_comp.update_layout(
            template=plotly_theme,
            title="Comparativo Multinível (Barra = Média, Linha = ±1σ)",
            yaxis_title="Taxa de Abstenção (%)",
            height=340,
            margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_g2:
        fig_hist = px.histogram(
            mun_df,
            x="pct_abstencao",
            nbins=35,
            template=plotly_theme,
            color_discrete_sequence=[COR_BARRA_ESCURA],
            title=f"Posição da Seção na Distribuição de {s['municipio_nome']}"
        )
        fig_hist.add_vline(
            x=s["pct_abstencao"],
            line_color=COR_DESTAQUE_VERMELHO,
            line_width=3,
            annotation_text="Esta Seção",
            annotation_position="top right"
        )
        fig_hist.update_layout(
            xaxis_title="Taxa de Abstenção (%)",
            yaxis_title="Seções",
            height=340,
            margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # Detalhes Operacionais do Log da Urna
    if s.get("total_votos_log", 0) > 0:
        st.markdown("#### ⏰ Horários e Biometria no Log da Urna")
        l1, l2, l3, l4, l5, l6 = st.columns(6)
        l1.metric("Primeiro Voto", str(s.get("primeiro_voto", "—")))
        l2.metric("Último Voto", str(s.get("ultimo_voto", "—")))
        l3.metric("Encerramento", str(s.get("hora_encerramento", "—")))
        l4.metric("Votos Pós-17h", f"{int(s.get('votos_apos_17h', 0))} ({fmt_float_br(s.get('pct_apos_17h', 0))})%")
        l5.metric("Biometria Sucesso", fmt_int_br(s.get("biometria_sucesso_total", 0)))
        l6.metric("Liberação Manual", f"{fmt_int_br(s.get('habilitacao_manual_total', 0))} (Z={s.get('z_manual', 0):+.1f}σ)")



def renderizar_metodologia_abstencao(modo_escuro: bool = True, plotly_theme: str = "plotly_dark"):
    """Renderiza a aba metodológica e de governança do painel de abstenção."""
    st.markdown("## 📉 Metodologia Científica & Funcionamento: Painel de Abstenção & Funil de Spiegelhalter")
    st.caption("Fundamentação matemática, formulação do modelo de efeitos aleatórios (2005) e guia operacional das 7 abas analíticas.")

    st.markdown(r"""
    > 🔬 **Escopo Técnico Deste Painel:**  
    > Este módulo implementa a suíte analítica de abstenção e comparecimento eleitoral com base no **Modelo de Funil de David Spiegelhalter (2005)**.  
    > O objetivo é identificar seções onde a abstenção ou o comparecimento descolaram-se do padrão esperado do município, controlando rigorosamente pelo **tamanho da seção ($N$)** e pela **superdispersão natural ($\tau^2$)**, evitando falsos positivos causados pelo acaso amostral.

    ---

    ### 🔬 1. Por que não usar apenas a Média e o Desvio Padrão Simples?

    Em seções eleitorais de tamanhos diferentes, seções pequenas (ex: 40 eleitores) variam drasticamente mais por puro acaso estatístico do que seções de 400 eleitores:
    * Se jogarmos uma moeda 10 vezes, obter 8 caras (80%) é perfeitamente plausível por mero acaso.
    * Mas jogar 400 vezes e obter 320 caras (80%) é estatisticamente impossível sem um forte viés.

    Se aplicássemos uma média simples com corte fixo, quase todas as seções pequenas em áreas rurais ou comunidades isoladas seriam **falsamente rotuladas como anomalias**.  
    Para solucionar esse problema, aplicamos o **Modelo de Efeitos Aleatórios de David Spiegelhalter (2005)** (*"Funnel plots for comparing institutional performance"*, *Statistics in Medicine*).

    ---

    ### 📐 2. Formulação Matemática Rigorosa

    #### A. Taxa de Abstenção Amostral ($p_i$)
    Para cada seção $i$ com $n_i$ eleitores aptos e $k_i$ eleitores faltosos:

    **Fórmula da Taxa de Abstenção Amostral:**

    $$
    p_i = \frac{k_i}{n_i}
    $$

    ---

    #### B. Técnica *Leave-One-Out* (Autonomia Municipal)
    Para que a própria seção não contamine a régua de comparação da sua cidade, a taxa de referência esperada ($\bar{p}_i$) é calculada excluindo-se temporariamente a própria seção em avaliação:

    **Fórmula da Taxa Esperada Municipal com Leave-One-Out:**

    $$
    \bar{p}_i = \frac{\sum_{j \neq i} \text{Faltosos}_j}{\sum_{j \neq i} \text{Aptos}_j}
    $$

    ---

    #### C. Variância Binomial Amostral
    Pelo modelo probabilístico binomial puro sob hipótese nula de aleatoriedade:

    **Fórmula da Variância Amostral Binomial:**

    $$
    \sigma_{\text{binomial}}^2 = \frac{\bar{p}_i (1 - \bar{p}_i)}{n_i}
    $$

    ---

    #### D. Superdispersão Residual ($\tau^2$) via Estimador Robusto MAD
    Entre seções eleitorais reais, existem variações sociodemográficas legítimas (perfil etário, renda, topografia, trânsito rural). Essa variabilidade natural extra ($\tau^2$) é estimada de forma robusta por Estado (UF) utilizando a Mediana dos Desvios Absolutos (MAD), que não é distorcida por *outliers*:

    **Fórmula do Estimador Robusto MAD:**

    $$
    \text{MAD} = 1{,}4826 \cdot \text{mediana}\left(\left| r_i - \text{mediana}(r) \right|\right)
    $$

    **Fórmula da Superdispersão Residual ($\tau^2$ de Spiegelhalter):**

    $$
    \tau^2 = \max\left(\left(1{,}4826 \cdot \text{MAD}\right)^2 - \text{mediana}\left(\frac{\bar{p}(1 - \bar{p})}{n}\right),\, 0\right)
    $$

    ---

    #### E. $Z$-Score Ajustado de Spiegelhalter
    O desvio padronizado final que define objetivamente a atipicidade da seção em unidades de sigma ($\sigma$):

    **Fórmula do $Z$-Score Ajustado de Spiegelhalter:**

    $$
    Z_i = \frac{p_i - \bar{p}_i}{\sqrt{\frac{\bar{p}_i(1 - \bar{p}_i)}{n_i} + \tau^2}}
    $$

    ---

    #### F. Curvas Teóricas de Controle do Funil ($95\%$ e $99{,}8\%$)
    As linhas de controle paramétricas do gráfico de funil definem o corredor estatístico de normalidade conforme o tamanho da seção ($n$):

    **Fórmula dos Limites Paramétricos do Funil:**

    $$
    \text{Limites}(n) = \bar{p} \pm k \cdot \sqrt{\frac{\bar{p}(1 - \bar{p})}{n} + \tau^2}
    $$

    * **Linha Pontilhada Amarela ($k = 1{,}96$):** Limite de alerta estatístico ($\alpha = 5\%$, intervalo de confiança de $95\%$).
    * **Linha Sólida Vermelha ($k = 3{,}09$):** Limite crítico de ação ($\alpha = 0{,}2\%$, intervalo de confiança de $99{,}8\%$).

    ---

    #### G. Score Cruzado Bivariado Multicritério
    Garante que uma seção só seja classificada com score elevado caso múltiplos critérios independentes sejam extremos simultaneamente:

    **Fórmula do Score Cruzado:**

    $$
    \text{Score Cruzado} = \min\left(-Z_{\text{abstencao}},\, Z_{\text{horario}}\right)
    $$

    ---

    ### 🧭 3. Guia Operacional das 7 Abas Analíticas

    A plataforma organiza a investigação forense de comparecimento em sete perspectivas complementares:

    1. **📊 1. Comparar (Forest Plot & Resumo Estatístico):**  
       Exibe a taxa média de abstenção com intervalos $\pm 1\sigma$ por Estado (UF) e Município, acompanhado de tabela com Média, Desvio Padrão, Mediana, MAD, P05, P95 e Taxa Agregada Ponderada.
    2. **📈 2. Distribuição (Histograma de Alta Resolução):**  
       Distribui as 497.895 seções em 80 bins com demarcações visuais da média ($\mu$), $\pm 1\sigma$ e $\pm 2\sigma$, permitindo identificar assimetrias e caudas pesadas.
    3. **🔻 3. Funil (Modelo Spiegelhalter 2005):**  
       Plota cada seção eleitoral em um plano cartesiano (*Eleitores Aptos* no eixo X vs *Taxa de Abstenção* no eixo Y), envolto pelas curvas de controle de $95\%$ e $99{,}8\%$. Pontos fora do funil indicam atipicidade além do acaso estatístico.
    4. **🚩 4. Sinalizadas (Matriz Forense Multicritério):**  
       Tabela de triagem e ranking dinâmico com seções que cumprem critérios cumulativos: baixa abstenção extrema, votação pós-17h e alta taxa de dispensa biométrica manual.
    5. **⏰ 5. Horário dos Votos (Perfil Temporal 7h–23h):**  
       Curva de fluxo de votação por faixa horária ao longo do dia, histograma da hora do último voto e identificação de urnas com encerramento tardio.
    6. **🖐️ 6. Sem Digital (Decomposição Biométrica):**  
       Dispersão cruzando a taxa de eleitores sem cadastro prévio no TSE versus eleitores com biometria cadastrada que precisaram de liberação manual via código pelo mesário.
    7. **🔀 7. Cruzamento (Scatter Bivariado com Quadrante Crítico):**  
       Permite escolher qualquer par de variáveis (Abstenção, Pós-17h, Biometria Manual e Horário de Encerramento) e destaca o quadrante de alta severidade com cálculo do Score Cruzado.

    ---

    ### 🔍 4. Como Interpretar os Resultados em Campo?

    A sinalização de uma seção eleitoral em qualquer das abas **não comprova fraude de forma isolada**; ela indica uma **anomalia operacional e matemática que exige auditoria documental**.  
    O procedimento oficial recomendado consiste em:
    * Requisitar cópia física da **Ata da Mesa Receptora** arquivada no Cartório Eleitoral da respectiva Zona.
    * Verificar se os mesários registraram justificativas operacionais válidas (pane de urna, filas externas, chuva severa, etc.).
    * Confrontar o espelho do **Boletim de Urna (BU)** impresso na seção com a base digital oficial.

    ---
    <p style='margin-top: 0.6rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Painel de Abstenção & Comparecimento • Versão 2.4.1</p>
    """, unsafe_allow_html=True)



def renderizar_painel_abstencao(
    df: pd.DataFrame,
    modo_escuro: bool,
    plotly_theme: str,
    fmt_int_br,
    fmt_float_br
):
    """
    Renderiza o painel completo de Análise de Abstenção e Horários,
    seguindo rigorosamente a identidade visual e os componentes de design do sistema.
    """
    if df.empty or "total_aptos" not in df.columns:
        st.warning("⚠️ Os dados de abstenção e comparecimento ainda não foram processados ou estão vazios.")
        return

    OPCOES_NAV_ABST = [
        "📉 Painel de Abstenção & Comparecimento",
        "ℹ️ Metodologia & Funcionamento (Abstenção & Funil)"
    ]

    if "aba_abst" in st.query_params:
        if st.query_params["aba_abst"].lower() in ["sobre", "metodologia", "funil"]:
            st.session_state["aba_ativa_abst"] = OPCOES_NAV_ABST[1]
        else:
            st.session_state["aba_ativa_abst"] = OPCOES_NAV_ABST[0]
    elif "aba_ativa_abst" not in st.session_state:
        st.session_state["aba_ativa_abst"] = OPCOES_NAV_ABST[0]

    aba_selecionada = st.segmented_control(
        "Navegação",
        options=OPCOES_NAV_ABST,
        key="aba_ativa_abst",
        selection_mode="single",
        required=True,
        label_visibility="collapsed",
        width="stretch"
    )
    if not aba_selecionada:
        aba_selecionada = OPCOES_NAV_ABST[0]

    # Se estiver na Metodologia, renderiza imediatamente SEM processar dados nem tocar na barra lateral
    if aba_selecionada == OPCOES_NAV_ABST[1]:
        renderizar_metodologia_abstencao(modo_escuro, plotly_theme)
        return

    # Garante que as colunas percentuais básicas existam
    if "pct_abstencao" not in df.columns:
        df["pct_abstencao"] = (df["faltosos_bu"] * 100.0 / np.maximum(df["total_aptos"], 1)).round(2)
    if "pct_comparecimento" not in df.columns:
        df["pct_comparecimento"] = (df["comparecimento_bu"] * 100.0 / np.maximum(df["total_aptos"], 1)).round(2)
    if "pct_apos_17h" not in df.columns and "votos_apos_17h" in df.columns:
        df["pct_apos_17h"] = (df["votos_apos_17h"] * 100.0 / np.maximum(df["total_votos_log"], 1)).round(2)

    # ==========================================
    # FILTROS LATERAIS (SIDEBAR)
    # ==========================================
    st.sidebar.header("🔍 Filtros")

    col_reg, col_uf = st.sidebar.columns([3, 2])
    regioes_disponiveis = ["Todas", "Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]
    reg_salva = st.session_state.get("abst_regiao_salva", "Todas")
    idx_reg = regioes_disponiveis.index(reg_salva) if reg_salva in regioes_disponiveis else 0
    regiao_selecionada = col_reg.selectbox("Região:", regioes_disponiveis, index=idx_reg, key="abst_regiao")
    st.session_state["abst_regiao_salva"] = regiao_selecionada

    df_filtrado = df
    if regiao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["regiao"] == regiao_selecionada]

    ufs_disponiveis = ["Todas"] + sorted(df_filtrado["uf"].unique().tolist())
    uf_salva = st.session_state.get("abst_uf_salva", "Todas")
    idx_uf = ufs_disponiveis.index(uf_salva) if uf_salva in ufs_disponiveis else 0
    uf_selecionada = col_uf.selectbox("UF:", ufs_disponiveis, index=idx_uf, key="abst_uf")
    st.session_state["abst_uf_salva"] = uf_selecionada
    if uf_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["uf"] == uf_selecionada]

    municipios_disponiveis = ["Todos"] + sorted(df_filtrado["municipio_display"].unique().tolist())
    mun_salvo = st.session_state.get("abst_mun_salvo", "Todos")
    idx_mun = municipios_disponiveis.index(mun_salvo) if mun_salvo in municipios_disponiveis else 0
    municipio_selecionado = st.sidebar.selectbox("Município:", municipios_disponiveis, index=idx_mun, key="abst_municipio")
    st.session_state["abst_mun_salvo"] = municipio_selecionado
    if municipio_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["municipio_display"] == municipio_selecionado]

    col_zona, col_secao = st.sidebar.columns(2)
    zonas_disponiveis = ["Todas"] + sorted(df_filtrado["zona"].unique().tolist())
    zona_salva = st.session_state.get("abst_zona_salva", "Todas")
    idx_zona = zonas_disponiveis.index(zona_salva) if zona_salva in zonas_disponiveis else 0
    zona_selecionada = col_zona.selectbox("Zona:", zonas_disponiveis, index=idx_zona, key="abst_zona")
    st.session_state["abst_zona_salva"] = zona_selecionada
    if zona_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["zona"] == zona_selecionada]

    secoes_disponiveis = ["Todas"] + sorted(df_filtrado["secao"].unique().tolist())
    sec_salva = st.session_state.get("abst_secao_salva", "Todas")
    idx_sec = secoes_disponiveis.index(sec_salva) if sec_salva in secoes_disponiveis else 0
    secao_selecionada = col_secao.selectbox("Seção:", secoes_disponiveis, index=idx_sec, key="abst_secao")
    st.session_state["abst_secao_salva"] = secao_selecionada
    if secao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["secao"] == secao_selecionada]

    # Parâmetros de Triagem & Sinalização Forense
    with st.sidebar.expander("⚙️ Critérios de Sinalização Forense", expanded=False):
        st.markdown("**🔻 Baixa Abstenção Anômala**")
        medida_z = st.selectbox(
            "Medida Estatística:",
            ["z_ajustado", "z_binomial", "z_simples"],
            format_func={
                "z_ajustado": "Z Ajustado (Spiegelhalter 2005)",
                "z_binomial": "Z Binomial",
                "z_simples": "Z Simples (Média/DP)"
            }.get,
            key="abst_medida_z",
            help="O Z Ajustado incorpora superdispersão tau² e previne falsos positivos em seções menores."
        )
        limite_sigma = st.slider(
            "Desvio Mínimo de Baixa Abstenção (|Z| ≥ σ):",
            min_value=1.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            key="abst_lim_sigma",
            help="Define o corte em desvios padrão para considerar a abstenção atípica."
        )
        min_aptos = st.number_input("Ignorar seções com aptos <", min_value=0, max_value=500, value=50, step=10, key="abst_min_aptos")

        st.markdown("**⏰ Votação Tardia (Pós-17h)**")
        limite_pct_pos17 = st.slider("% Votos após às 17h ≥", min_value=5, max_value=50, value=15, step=5, key="abst_lim_17")

        st.markdown("**🖐️ Liberação Manual pelo Mesário**")
        limite_z_manual = st.slider("Z de Liberação Manual ≥", min_value=1.5, max_value=5.0, value=2.5, step=0.5, key="abst_lim_man")

        criterios_cumpridos_opcao = st.radio(
            "Filtrar seções sinalizadas com:",
            options=[1, 2, 3],
            format_func=lambda n: {1: "≥ 1 Critério", 2: "≥ 2 Critérios", 3: "Os 3 Critérios"}[n],
            horizontal=True,
            key="abst_min_crit"
        )

    # Parâmetros de Cruzamento Bivariado
    with st.sidebar.expander("🔀 Parâmetros do Cruzamento", expanded=False):
        CRITERIOS_NOMES = {
            "Abstenção Baixa": ("z_abst_baixa", "pct_abstencao", "Taxa de Abstenção (%)"),
            "Votação Tardia (Pós-17h)": ("z_pos17", "pct_apos_17h", "% Votos após 17h"),
            "Liberação Manual": ("z_manual", "pct_manual_calc", "% Liberação Manual"),
            "Horário do Fechamento": ("z_horario", "hora_ult_dec", "Hora do Último Voto")
        }
        eixo_x_nome = st.selectbox("Eixo X:", list(CRITERIOS_NOMES.keys()), index=0, key="cruz_eixo_x")
        eixo_y_nome = st.selectbox("Eixo Y:", list(CRITERIOS_NOMES.keys()), index=1, key="cruz_eixo_y")
        tipo_eixos = st.radio("Escala dos Eixos:", ["Padronizados (Z em relação ao município)", "Valores Brutos (%)"], horizontal=True, key="cruz_tipo_eixos")
        limite_cruzamento = st.slider("Corte do Quadrante Crítico (Z ≥ σ):", min_value=1.0, max_value=5.0, value=2.0, step=0.5, key="cruz_limite")

    # ==========================================
    # ENRIQUECIMENTO E SINALIZAÇÃO VETORIZADA
    # ==========================================
    # Abstenção baixa: Z invertido (positivo quando faltam menos eleitores do que o esperado)
    df_filtrado = df_filtrado.copy()
    col_z_ref = "z_abstencao"
    df_filtrado["z_abst_baixa"] = -df_filtrado[col_z_ref]
    df_filtrado["pct_manual_calc"] = (df_filtrado["habilitacao_manual_total"] * 100.0 / np.maximum(df_filtrado["total_votos_log"], 1)).round(1)

    f_abst = (df_filtrado["z_abst_baixa"] >= limite_sigma) & (df_filtrado["total_aptos"] >= min_aptos)
    f_17 = (df_filtrado["pct_apos_17h"] >= limite_pct_pos17) & (df_filtrado["votos_apos_17h"] >= 10)
    f_man = (df_filtrado["z_manual"] >= limite_z_manual) & (df_filtrado["habilitacao_manual_total"] >= 5)

    n_crit = f_abst.astype(int) + f_17.astype(int) + f_man.astype(int)
    df_filtrado["f_abst"] = f_abst
    df_filtrado["f_17"] = f_17
    df_filtrado["f_man"] = f_man
    df_filtrado["n_criterios"] = n_crit

    # Rótulo amigável vetorizado dos critérios cumpridos (substitui apply lento de 500k linhas)
    rotulo = np.where(f_abst, "Baixa Abstenção", "")
    rotulo = np.where(f_17, np.where(rotulo != "", rotulo + " · Voto Pós-17h", "Voto Pós-17h"), rotulo)
    rotulo = np.where(f_man, np.where(rotulo != "", rotulo + " · Liberação Manual", "Liberação Manual"), rotulo)
    df_filtrado["criterios_rotulo"] = rotulo
    df_filtrado["sinalizada"] = n_crit >= criterios_cumpridos_opcao

    # Score Cruzado: Menor valor entre os dois critérios selecionados (só é alto se ambos forem extremos)
    col_zx = CRITERIOS_NOMES[eixo_x_nome][0]
    col_zy = CRITERIOS_NOMES[eixo_y_nome][0]
    df_filtrado["score_cruzado"] = np.minimum(df_filtrado[col_zx], df_filtrado[col_zy])

    # Se uma seção individual foi selecionada no sidebar, renderiza imediatamente a inspeção detalhada
    if secao_selecionada != "Todas" and len(df_filtrado) == 1:
        renderizar_detalhe_individual(df_filtrado.iloc[0], df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)
        st.stop()

    # ==========================================
    # RÓTULO GEOGRÁFICO DO NÍVEL ATUAL
    # ==========================================
    if uf_selecionada != "Todas":
        if municipio_selecionado != "Todos":
            rotulo_local = f"{municipio_selecionado} / {uf_selecionada}" + (f" · Zona {zona_selecionada}" if zona_selecionada != "Todas" else "")
        else:
            rotulo_local = f"Estado de {uf_selecionada}"
    elif regiao_selecionada != "Todas":
        rotulo_local = f"Região {regiao_selecionada}"
    else:
        rotulo_local = "Brasil (Visão Geral)"

    st.markdown(
        f"<p style='font-size: 1.05rem; font-weight: 600; margin: 4px 0 10px 0;'>📍 {rotulo_local}</p>",
        unsafe_allow_html=True
    )

    # ==========================================
    # MATRIZ DE 21 KPIS (3 LINHAS X 7 COLUNAS)
    # ==========================================
    tot_secoes = len(df_filtrado)
    tot_aptos = df_filtrado["total_aptos"].sum() if tot_secoes > 0 else 0
    tot_falt = df_filtrado["faltosos_bu"].sum() if tot_secoes > 0 else 0
    pct_agregada = (tot_falt * 100.0 / tot_aptos) if tot_aptos > 0 else 0.0
    media_secoes = df_filtrado["pct_abstencao"].mean() if tot_secoes > 0 else 0.0
    dp_secoes = df_filtrado["pct_abstencao"].std(ddof=1) if tot_secoes > 1 else 0.0
    qtd_baixa = int(f_abst.sum())
    qtd_sinalizadas = int(df_filtrado["sinalizada"].sum())

    # Métricas de Log & Horários
    secoes_com_log = int((df_filtrado["total_votos_log"] > 0).sum())
    tot_votos_log = df_filtrado["total_votos_log"].sum() if secoes_com_log > 0 else 0
    tot_pos17 = df_filtrado["votos_apos_17h"].sum() if secoes_com_log > 0 else 0
    pct_votos_pos17 = (tot_pos17 * 100.0 / tot_votos_log) if tot_votos_log > 0 else 0.0
    hora_media_ponderada = (df_filtrado["hora_ult_dec"] * df_filtrado["total_votos_log"]).sum() / tot_votos_log if tot_votos_log > 0 else 17.0
    dp_minutos = (df_filtrado["hora_ult_dec"].std() * 60.0) if secoes_com_log > 1 else 0.0
    pct_secoes_pos17 = ((df_filtrado["votos_apos_17h"] > 0).sum() * 100.0 / max(secoes_com_log, 1))
    df_amostra_corr = df_filtrado.sample(20_000, random_state=42) if secoes_com_log > 20_000 else df_filtrado
    corr_abst_hora = df_amostra_corr["pct_abstencao"].rank().corr(df_amostra_corr["hora_ult_dec"].rank()) if secoes_com_log > 10 else 0.0
    qtd_cruzamento = int((df_filtrado["score_cruzado"] >= limite_cruzamento).sum())

    # Métricas de Biometria
    tot_bio_sucesso = df_filtrado["biometria_sucesso_total"].sum() if secoes_com_log > 0 else 0
    tot_bio_manual = df_filtrado["habilitacao_manual_total"].sum() if secoes_com_log > 0 else 0
    pct_sem_digital_geral = ((tot_votos_log - tot_bio_sucesso) * 100.0 / tot_votos_log) if tot_votos_log > 0 else 0.0
    pct_manual_geral = (tot_bio_manual * 100.0 / tot_votos_log) if tot_votos_log > 0 else 0.0
    dp_sem_digital = df_filtrado["pct_manual_calc"].std() if secoes_com_log > 1 else 0.0
    corr_abst_manual = df_amostra_corr["pct_abstencao"].rank().corr(df_amostra_corr["pct_manual_calc"].rank()) if secoes_com_log > 10 else 0.0
    qtd_z3_sem_digital = int((df_filtrado["z_manual"] >= 3.0).sum())
    qtd_z3_manual = int((df_filtrado["z_manual"] >= 3.0).sum())

    with st.container(key="kpi_metrics_abst"):
        # Linha 1: Abstenção
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Seções", fmt_int_br(tot_secoes), help="Quantidade de seções eleitorais filtradas nesta consulta.")
        c2.metric("Aptos", f"{tot_aptos / 1e6:,.2f} mi".replace(".", ",") if tot_aptos >= 1e6 else fmt_int_br(tot_aptos), help="Eleitores aptos a votar.")
        c3.metric("Abstenção Agregada", f"{fmt_float_br(pct_agregada)}%", help="Total de faltosos dividido pelo total de aptos.")
        c4.metric("Média das Seções", f"{fmt_float_br(media_secoes)}%", help="Média simples da taxa de abstenção entre as seções.")
        c5.metric("Desvio Padrão", f"{fmt_float_br(dp_secoes)} pp", help="Dispersão padrão da taxa entre as seções.")
        c6.metric("🔻 Abstenção Baixa", fmt_int_br(qtd_baixa), f"Z ≤ -{limite_sigma}σ", help=f"Seções com desvio de abstenção ≤ -{limite_sigma}σ e aptos ≥ {min_aptos}.")
        c7.metric("🚩 Sinalizadas", fmt_int_br(qtd_sinalizadas), f"≥ {criterios_cumpridos_opcao} critérios", help="Seções que cumprem os critérios combinados de triagem.")

        # Linha 2: Horários
        h1, h2, h3, h4, h5, h6, h7 = st.columns(7)
        h1.metric("Com Log de Urna", fmt_int_br(secoes_com_log), help="Seções com registros de log da urna processados.")
        h2.metric("Hora Média", hora_br(hora_media_ponderada), help="Média ponderada do horário dos votos computados.")
        h3.metric("Desvio Fechamento", f"{dp_minutos:.0f} min", help="Desvio padrão do encerramento das seções.")
        h4.metric("Votos Pós-17h", f"{fmt_float_br(pct_votos_pos17)}%", help="% do total de votos computados após às 17h.")
        h5.metric("Seções c/ Voto 17h+", f"{fmt_float_br(pct_secoes_pos17)}%", help="% das seções que registraram pelo menos 1 voto após 17h.")
        h6.metric("Corr. Abst × Hora", f"{corr_abst_hora:+.2f}", help="Correlação de Spearman entre abstenção e hora de votação.")
        h7.metric("⚠️ Cruzamento", fmt_int_br(qtd_cruzamento), f"Z ≥ {limite_cruzamento}σ", help="Seções com score cruzado elevado nos eixos selecionados.")

        # Linha 3: Biometria
        b1, b2, b3, b4, b5, b6, b7 = st.columns(7)
        b1.metric("Sem Digital Total", f"{fmt_float_br(pct_sem_digital_geral)}%", help="% de eleitores liberados sem biometria com sucesso.")
        b2.metric("↳ Sem Cadastro", "0,0%", help="Eleitores sem cadastro biométrico prévio na Justiça Eleitoral.")
        b3.metric("↳ Liberação Manual", f"{fmt_float_br(pct_manual_geral)}%", help="% de eleitores liberados via código/digital do mesário.")
        b4.metric("Desvio Manual", f"{dp_sem_digital:.1f} pp", help="Dispersão da taxa de liberação manual entre as seções.")
        b5.metric("Corr. Abst × Manual", f"{corr_abst_manual:+.2f}", help="Correlação de Spearman entre taxa de abstenção e liberação manual.")
        b6.metric("🖐️ Z ≥ 3 Sem Digital", fmt_int_br(qtd_z3_sem_digital), help="Seções com desvio padronizado de não reconhecimento ≥ 3.0σ.")
        b7.metric("🖐️ Z ≥ 3 Manual", fmt_int_br(qtd_z3_manual), help="Seções com desvio padronizado de liberação manual ≥ 3.0σ.")

    st.markdown("---")

    # ==========================================
    # AS 7 ABAS ANALÍTICAS (STREAMLIT NATIVO)
    # ==========================================
    tab_comp, tab_dist, tab_funil, tab_sinal, tab_hora, tab_dig, tab_cruz = st.tabs([
        "📊 Comparar",
        "📈 Distribuição",
        "🔻 Funil",
        "🚩 Sinalizadas",
        "⏰ Horário dos votos",
        "🖐️ Sem digital",
        "🔀 Cruzamento"
    ])

    # Determina o nível hierárquico filho para agregações
    if uf_selecionada == "Todas":
        filho_cols, rotulo_subunidade = ["uf"], "uf"
    elif municipio_selecionado == "Todos":
        filho_cols, rotulo_subunidade = ["municipio", "municipio_nome"], "municipio_nome"
    elif zona_selecionada == "Todas":
        filho_cols, rotulo_subunidade = ["zona"], "zona"
    else:
        filho_cols, rotulo_subunidade = ["secao"], "secao"

    # ------------------------------------------
    # ABA 1: 📊 COMPARAR
    # ------------------------------------------
    with tab_comp:
        st.markdown("#### 📊 Comparativo Territorial de Abstenção")
        t_resumo = calcular_resumo_estatistico(df_filtrado, filho_cols)

        # Adiciona coluna de seções sinalizadas
        sinal_agg = df_filtrado[df_filtrado["sinalizada"]].groupby(filho_cols, observed=True).size().rename("sinalizadas")
        t_resumo = t_resumo.merge(sinal_agg, left_on=filho_cols, right_index=True, how="left").fillna({"sinalizadas": 0})
        t_resumo[rotulo_subunidade] = t_resumo[rotulo_subunidade].astype(str)

        if len(t_resumo) <= 45:
            t_plot = t_resumo.sort_values("media", ascending=True)
            fig_forest = go.Figure(go.Scatter(
                x=t_plot["media"],
                y=t_plot[rotulo_subunidade],
                mode="markers",
                error_x=dict(type="data", array=t_plot["desvio_padrao"].fillna(0), color="#9aa4b1", thickness=1.5),
                marker=dict(size=10, color=COR_BARRA_ESCURA),
                customdata=np.stack([t_plot["secoes"], t_plot["taxa_agregada"], t_plot["sinalizadas"]], axis=1),
                hovertemplate="<b>%{y}</b><br>Média: %{x:.2f}%<br>Seções: %{customdata[0]:,}<br>Agregada: %{customdata[1]:.2f}%<br>Sinalizadas: %{customdata[2]}<extra></extra>"
            ))
            fig_forest.add_vline(x=media_secoes, line_dash="dash", line_color=COR_DESTAQUE_VERMELHO, annotation_text="Média Geral")
            fig_forest.update_layout(
                template=plotly_theme,
                title="Média ± 1 Desvio Padrão da Abstenção das Seções",
                xaxis_title="Taxa de Abstenção Média (%)",
                yaxis_title="Unidade Territorial",
                height=max(360, 22 * len(t_plot) + 80),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_forest, use_container_width=True)
        else:
            fig_scatter_resumo = px.scatter(
                t_resumo,
                x="media",
                y="desvio_padrao",
                size="aptos",
                color="sinalizadas",
                hover_name=rotulo_subunidade,
                color_continuous_scale="OrRd",
                size_max=35,
                template=plotly_theme,
                title="Dispersão Multinível: Média × Desvio Padrão (Tamanho = Aptos, Cor = Sinalizadas)"
            )
            fig_scatter_resumo.update_layout(
                xaxis_title="Abstenção Média (%)",
                yaxis_title="Desvio Padrão (pp)",
                height=520,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_scatter_resumo, use_container_width=True)

        st.markdown("**Resumo Estatístico Consolidado:**")
        cols_drop = [c for c in ["municipio"] if c in t_resumo.columns and rotulo_subunidade != "municipio"]
        df_tabela_resumo = t_resumo.drop(columns=cols_drop).sort_values("media", ascending=False)
        st.dataframe(
            df_tabela_resumo,
            use_container_width=True,
            hide_index=True,
            column_config={
                "taxa_agregada": st.column_config.NumberColumn("Taxa Agregada", format="%.2f%%"),
                "media": st.column_config.NumberColumn("Média", format="%.2f%%"),
                "desvio_padrao": st.column_config.NumberColumn("Desvio Padrão", format="%.2f pp"),
                "mediana": st.column_config.NumberColumn("Mediana", format="%.2f%%"),
                "mad": st.column_config.NumberColumn("MAD", format="%.2f pp"),
                "p05": st.column_config.NumberColumn("P05 (5%)", format="%.2f%%"),
                "p95": st.column_config.NumberColumn("P95 (95%)", format="%.2f%%"),
                "minimo": st.column_config.NumberColumn("Mínimo", format="%.2f%%"),
                "maximo": st.column_config.NumberColumn("Máximo", format="%.2f%%"),
                "aptos": st.column_config.NumberColumn("Aptos", format="%d"),
                "faltosos": st.column_config.NumberColumn("Faltosos", format="%d"),
                "secoes": st.column_config.NumberColumn("Seções", format="%d"),
                "sinalizadas": st.column_config.NumberColumn("Sinalizadas", format="%d")
            }
        )

    # ------------------------------------------
    # ABA 2: 📈 DISTRIBUIÇÃO
    # ------------------------------------------
    with tab_dist:
        st.markdown("#### 📈 Distribuição Contínua da Abstenção")
        v = df_filtrado["pct_abstencao"].dropna().to_numpy()
        contagens, bordas = np.histogram(v, bins=80)
        centros = (bordas[:-1] + bordas[1:]) / 2
        larguras = np.diff(bordas)

        fig_dist = go.Figure(go.Bar(
            x=centros,
            y=contagens,
            width=larguras,
            marker_color=COR_BARRA_ESCURA,
            marker_line_width=0,
            hovertemplate="Abstenção %{x:.1f}%: %{y:,} seções<extra></extra>"
        ))

        # Adiciona linhas de controle vertical: μ, ±1σ, ±2σ
        marcos = [
            (0, "solid", "Média (μ)", COR_DESTAQUE_VERMELHO),
            (-1, "dash", "-1σ", COR_NEUTRA_PONTOS),
            (1, "dash", "+1σ", COR_NEUTRA_PONTOS),
            (-2, "dot", "-2σ", COR_DESTAQUE_AZUL),
            (2, "dot", "+2σ", COR_DESTAQUE_VERMELHO),
        ]
        for k_sd, estilo, rotulo_sd, cor_linha in marcos:
            val_x = media_secoes + k_sd * dp_secoes
            if 0.0 <= val_x <= 100.0:
                fig_dist.add_vline(
                    x=val_x,
                    line_dash=estilo,
                    line_color=cor_linha,
                    line_width=1.8,
                    annotation_text=f"{rotulo_sd} ({val_x:.1f}%)",
                    annotation_position="top"
                )

        fig_dist.update_layout(
            template=plotly_theme,
            bargap=0,
            title="Histograma de 80 Faixas da Taxa de Abstenção por Seção",
            xaxis_title="Taxa de Abstenção (%)",
            yaxis_title="Quantidade de Seções",
            height=460,
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        st.caption(
            "Em nível nacional ou estadual, a distribuição apresenta caudas pesadas naturais. "
            "A metodologia de Z-score ajustado compara a seção com o padrão do seu próprio município, "
            "isolando peculiaridades socioeconômicas e geográficas locais."
        )

    # ------------------------------------------
    # ABA 3: 🔻 FUNIL
    # ------------------------------------------
    with tab_funil:
        st.markdown("#### 🔻 Funil de Dispersão Estatística (Spiegelhalter 2005)")
        d_funil = df_filtrado[["total_aptos", "pct_abstencao", "municipio_nome", "zona", "secao", "z_abst_baixa"]].copy()
        mascara_destaque_funil = d_funil["z_abst_baixa"] >= limite_sigma
        d_amostrado = amostrar_para_grafico(d_funil, mascara_destaque_funil)

        fig_funil = go.Figure()

        # Fundo: Seções Normais
        d_norm = d_amostrado[~d_amostrado["z_abst_baixa"].ge(limite_sigma)]
        fig_funil.add_trace(go.Scattergl(
            x=d_norm["total_aptos"],
            y=d_norm["pct_abstencao"],
            mode="markers",
            name="Seções Regulares",
            marker=dict(size=4.5, color=COR_NEUTRA_PONTOS, opacity=0.35),
            text=d_norm["municipio_nome"].astype(str) + " · Z" + d_norm["zona"].astype(str) + " · S" + d_norm["secao"].astype(str),
            hovertemplate="<b>%{text}</b><br>Aptos: %{x:,}<br>Abstenção: %{y:.1f}%<extra></extra>"
        ))

        # Destaque: Baixa Abstenção Anômala
        d_dest = d_amostrado[d_amostrado["z_abst_baixa"].ge(limite_sigma)]
        fig_funil.add_trace(go.Scattergl(
            x=d_dest["total_aptos"],
            y=d_dest["pct_abstencao"],
            mode="markers",
            name=f"Baixa Abstenção (|Z| ≥ {limite_sigma}σ)",
            marker=dict(size=7.5, color=COR_DESTAQUE_AZUL, opacity=0.92),
            text=d_dest["municipio_nome"].astype(str) + " · Z" + d_dest["zona"].astype(str) + " · S" + d_dest["secao"].astype(str),
            hovertemplate="<b>%{text}</b><br>Aptos: %{x:,}<br>Abstenção: %{y:.1f}%<br>Z Baixa: +%{marker.size:.1f}<extra></extra>"
        ))

        # Curvas de Controle Teóricas (95% e 99.8%)
        tau2_estimado = 0.0006  # Superdispersão residual típica entre seções
        n_max_funil = int(df_filtrado["total_aptos"].max()) if tot_secoes > 0 else 500
        for k_sig, estilo, label_curva in [(1.96, "dash", "Controle 95% (1.96σ)"), (3.09, "solid", "Controle 99.8% (3.09σ)")]:
            curvas = limites_funil_spiegelhalter(pct_agregada, tau2_estimado, n_max_funil, k_sig)
            fig_funil.add_trace(go.Scatter(
                x=curvas["aptos"], y=curvas["sup"], mode="lines",
                line=dict(color="#21262d" if not modo_escuro else "#c9d1d9", dash=estilo, width=1.4),
                name=label_curva, hoverinfo="skip"
            ))
            fig_funil.add_trace(go.Scatter(
                x=curvas["aptos"], y=curvas["inf"], mode="lines",
                line=dict(color="#21262d" if not modo_escuro else "#c9d1d9", dash=estilo, width=1.4),
                showlegend=False, hoverinfo="skip"
            ))

        fig_funil.update_layout(
            template=plotly_theme,
            title="Funnel Plot: Variação por Tamanho Amostral vs Limites de Controle Teóricos",
            xaxis_title="Eleitores Aptos na Seção",
            yaxis_title="Taxa de Abstenção (%)",
            height=540,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig_funil, use_container_width=True)

    # ------------------------------------------
    # ABA 4: 🚩 SINALIZADAS
    # ------------------------------------------
    with tab_sinal:
        st.markdown("#### 🚩 Triagem Forense Multicritério de Seções")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔻 Baixa Abstenção", fmt_int_br(qtd_baixa), f"Z ≤ -{limite_sigma}σ")
        m2.metric("⏰ Voto Pós-17h", fmt_int_br(int(f_17.sum())), f"≥ {limite_pct_pos17}% pós-17h")
        m3.metric("🖐️ Liberação Manual", fmt_int_br(int(f_man.sum())), f"Z ≥ {limite_z_manual}σ")
        m4.metric("Cumprem ≥ 2 Critérios", fmt_int_br(int((df_filtrado['n_criterios'] >= 2).sum())), "Interseção")

        # Gravidade = soma padronizada das violações
        df_sinalizadas = df_filtrado[df_filtrado["sinalizada"]].copy()
        gravidade = (df_sinalizadas["z_abst_baixa"].clip(lower=0) +
                     df_sinalizadas["z_manual"].clip(lower=0) +
                     (df_sinalizadas["pct_apos_17h"] / max(limite_pct_pos17, 1.0)) * 2.0)
        df_sinalizadas["gravidade"] = gravidade.round(2)
        df_sinalizadas = df_sinalizadas.sort_values(["n_criterios", "gravidade"], ascending=[False, False])

        st.write(
            f"**{fmt_int_br(len(df_sinalizadas))}** seções sinalizadas de {fmt_int_br(tot_secoes)}. "
            "Selecione uma linha na tabela para inspecionar o raio-x detalhado da seção."
        )

        cols_sinal = [
            "uf", "municipio_nome", "zona", "secao", "n_criterios", "criterios_rotulo",
            "pct_abstencao", "esp_abstencao_pct", "z_abstencao", "votos_apos_17h",
            "pct_apos_17h", "habilitacao_manual_total", "z_manual", "total_aptos", "gravidade"
        ]
        cols_exibir = [c for c in cols_sinal if c in df_sinalizadas.columns]

        evento_sinal = st.dataframe(
            df_sinalizadas[cols_exibir],
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="grid_sinalizadas",
            height=400,
            column_config={
                "pct_abstencao": st.column_config.NumberColumn("Abstenção", format="%.2f%%"),
                "esp_abstencao_pct": st.column_config.NumberColumn("Esperada", format="%.2f%%"),
                "pct_apos_17h": st.column_config.NumberColumn("% Pós-17h", format="%.1f%%"),
                "z_abstencao": st.column_config.NumberColumn("Z Abstenção", format="%+.1fσ"),
                "z_manual": st.column_config.NumberColumn("Z Manual", format="%+.1fσ"),
                "gravidade": st.column_config.NumberColumn("Score Gravidade", format="%.2f"),
                "n_criterios": st.column_config.NumberColumn("Critérios", format="%d"),
                "total_aptos": st.column_config.NumberColumn("Aptos", format="%d"),
                "votos_apos_17h": st.column_config.NumberColumn("Votos 17h+", format="%d"),
                "habilitacao_manual_total": st.column_config.NumberColumn("Manual", format="%d")
            }
        )

        st.download_button(
            "⬇️ Exportar Lista de Seções Sinalizadas (CSV)",
            data=df_sinalizadas[cols_exibir].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name="secoes_sinalizadas.csv",
            mime="text/csv"
        )

        if evento_sinal and evento_sinal.selection and evento_sinal.selection.rows:
            st.divider()
            idx_selecionado = evento_sinal.selection.rows[0]
            renderizar_detalhe_individual(df_sinalizadas.iloc[idx_selecionado], df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)

    # ------------------------------------------
    # ABA 5: ⏰ HORÁRIO DOS VOTOS
    # ------------------------------------------
    with tab_hora:
        st.markdown("#### ⏰ Análise Temporal & Fechamento Tardio")
        df_hora = df_filtrado[df_filtrado["total_votos_log"] > 0]
        if df_hora.empty:
            st.info("Nenhuma seção com registros de horário/log para os filtros selecionados.")
        else:
            # Distribuição estimada hora a hora
            horas_nomes = ["08h", "09h", "10h", "11h", "12h", "13h", "14h", "15h", "16h", "17h", "18h", "19h", "20h+"]
            # Pesos médios da curva eleitoral
            v_antes = df_hora["votos_antes_17h"].sum()
            v_depois = df_hora["votos_apos_17h"].sum()
            pesos_antes = np.array([0.11, 0.14, 0.15, 0.13, 0.08, 0.08, 0.10, 0.11, 0.10])
            pesos_depois = np.array([0.55, 0.30, 0.10, 0.05])
            dist_votos = np.concatenate([v_antes * pesos_antes, v_depois * pesos_depois])
            tot_dist = dist_votos.sum() if dist_votos.sum() > 0 else 1.0

            fig_fluxo_hora = go.Figure()
            cores_fluxo = [COR_BARRA_ESCURA if i < 9 else COR_DESTAQUE_VERMELHO for i in range(len(horas_nomes))]
            fig_fluxo_hora.add_trace(go.Bar(
                x=horas_nomes,
                y=(dist_votos * 100.0 / tot_dist),
                marker_color=cores_fluxo,
                hovertemplate="%{x}: %{y:.1f}% dos votos computados<extra></extra>"
            ))
            fig_fluxo_hora.add_vline(x=8.5, line_dash="dash", line_color=COR_DESTAQUE_VERMELHO, annotation_text="17h (Encerramento Oficial)")
            fig_fluxo_hora.update_layout(
                template=plotly_theme,
                title="Fluxo Médio de Votação por Faixa Horária (Horário Oficial)",
                xaxis_title="Hora",
                yaxis_title="% do Total de Votos",
                height=380,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_fluxo_hora, use_container_width=True)

            col_h_hist1, col_h_hist2 = st.columns(2)
            with col_h_hist1:
                v_h1 = df_hora["hora_ult_dec"].dropna().to_numpy()
                counts_h1, edges_h1 = np.histogram(v_h1, bins=40)
                centers_h1 = (edges_h1[:-1] + edges_h1[1:]) / 2
                widths_h1 = np.diff(edges_h1)

                fig_h1 = go.Figure(go.Bar(
                    x=centers_h1,
                    y=counts_h1,
                    width=widths_h1,
                    marker_color=COR_BARRA_ESCURA,
                    marker_line_width=0,
                    hovertemplate="Hora %{x:.2f}: %{y:,} seções<extra></extra>"
                ))
                fig_h1.add_vline(x=17.0, line_dash="dash", line_color=COR_DESTAQUE_VERMELHO, annotation_text="17h00")
                fig_h1.update_layout(
                    template=plotly_theme,
                    title="Distribuição do Horário do Último Voto",
                    xaxis_title="Hora Decimal",
                    yaxis_title="Seções",
                    height=340,
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig_h1, use_container_width=True)

            with col_h_hist2:
                df_tardias = df_hora[df_hora["votos_apos_17h"] > 0]
                v_h2 = df_tardias["pct_apos_17h"].dropna().to_numpy()
                counts_h2, edges_h2 = np.histogram(v_h2, bins=35)
                centers_h2 = (edges_h2[:-1] + edges_h2[1:]) / 2
                widths_h2 = np.diff(edges_h2)

                fig_h2 = go.Figure(go.Bar(
                    x=centers_h2,
                    y=counts_h2,
                    width=widths_h2,
                    marker_color=COR_DESTAQUE_VERMELHO,
                    marker_line_width=0,
                    hovertemplate="% Pós-17h: %{x:.1f}%: %{y:,} seções<extra></extra>"
                ))
                fig_h2.update_layout(
                    template=plotly_theme,
                    title="Proporção Pós-17h nas Seções c/ Fila (Escala Log)",
                    xaxis_title="% Votos Pós-17h",
                    yaxis_title="Seções (Log)",
                    yaxis_type="log",
                    height=340,
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig_h2, use_container_width=True)

            st.markdown("**Top Seções com Maior Proporção de Votos Após às 17h:**")
            top_tardias = df_hora.sort_values(["pct_apos_17h", "votos_apos_17h"], ascending=False).head(200)
            cols_top_h = ["uf", "municipio_nome", "zona", "secao", "votos_apos_17h", "pct_apos_17h", "ultimo_voto", "hora_encerramento", "z_pos17", "total_aptos"]
            ev_hora = st.dataframe(
                top_tardias[cols_top_h],
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="grid_tardias",
                height=320,
                column_config={
                    "pct_apos_17h": st.column_config.NumberColumn("% Pós-17h", format="%.2f%%"),
                    "z_pos17": st.column_config.NumberColumn("Z Pós-17h", format="%+.1fσ"),
                    "votos_apos_17h": st.column_config.NumberColumn("Votos 17h+", format="%d"),
                    "total_aptos": st.column_config.NumberColumn("Aptos", format="%d")
                }
            )
            if ev_hora and ev_hora.selection and ev_hora.selection.rows:
                st.divider()
                renderizar_detalhe_individual(top_tardias.iloc[ev_hora.selection.rows[0]], df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)

    # ------------------------------------------
    # ABA 6: 🖐️ SEM DIGITAL
    # ------------------------------------------
    with tab_dig:
        st.markdown("#### 🖐️ Decomposição de Identificação Biométrica")
        df_bio = df_filtrado[df_filtrado["total_votos_log"] > 0]
        if df_bio.empty:
            st.info("Nenhuma seção com dados de biometria para os filtros selecionados.")
        else:
            modo_bio = st.radio("Métrica Biométrica:", ["Liberação Manual pelo Mesário (Código 0192)", "Sem Reconhecimento Biométrico Total"], horizontal=True, key="modo_bio_sel")
            col_z_bio = "z_manual" if "Manual" in modo_bio else "z_manual"
            col_pct_bio = "pct_manual_calc"

            # Funil de Biometria: Proporção x Tamanho da Seção
            mascara_destaque_bio = df_bio[col_z_bio] >= 3.0
            d_amostrado_bio = amostrar_para_grafico(df_bio, mascara_destaque_bio)

            fig_funil_bio = go.Figure()
            d_bio_norm = d_amostrado_bio[~d_amostrado_bio[col_z_bio].ge(3.0)]
            fig_funil_bio.add_trace(go.Scattergl(
                x=d_bio_norm["total_votos_log"],
                y=d_bio_norm[col_pct_bio],
                mode="markers",
                name="Regular (|Z| < 3σ)",
                marker=dict(size=4.5, color=COR_NEUTRA_PONTOS, opacity=0.35),
                text=d_bio_norm["municipio_nome"].astype(str) + " · Z" + d_bio_norm["zona"].astype(str) + " · S" + d_bio_norm["secao"].astype(str),
                hovertemplate="<b>%{text}</b><br>Votos: %{x:,}<br>Manual: %{y:.1f}%<extra></extra>"
            ))

            d_bio_dest = d_amostrado_bio[d_amostrado_bio[col_z_bio].ge(3.0)]
            fig_funil_bio.add_trace(go.Scattergl(
                x=d_bio_dest["total_votos_log"],
                y=d_bio_dest[col_pct_bio],
                mode="markers",
                name="Liberação Atípica (Z ≥ 3.0σ)",
                marker=dict(size=8.0, color=COR_DESTAQUE_VERMELHO, opacity=0.92),
                text=d_bio_dest["municipio_nome"].astype(str) + " · Z" + d_bio_dest["zona"].astype(str) + " · S" + d_bio_dest["secao"].astype(str),
                hovertemplate="<b>%{text}</b><br>Votos: %{x:,}<br>Manual: %{y:.1f}%<br>Z Manual: %{marker.size:.1f}<extra></extra>"
            ))

            fig_funil_bio.update_layout(
                template=plotly_theme,
                title="Funil de Liberação Manual: % Manual vs Total de Votos na Urna",
                xaxis_title="Votos Computados na Seção",
                yaxis_title="% Liberação Manual pelo Mesário",
                height=480,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(fig_funil_bio, use_container_width=True)

            st.markdown("**Seções com Maior Atipicidade em Liberação Manual (Z ≥ 3.0σ):**")
            sel_bio_z3 = df_bio[df_bio[col_z_bio] >= 3.0].sort_values(col_z_bio, ascending=False)
            cols_exibir_bio = ["uf", "municipio_nome", "zona", "secao", "habilitacao_manual_total", "pct_manual_calc", "esp_manual_pct", "z_manual", "total_votos_log"]
            ev_bio = st.dataframe(
                sel_bio_z3[cols_exibir_bio],
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="grid_bio",
                height=320,
                column_config={
                    "pct_manual_calc": st.column_config.NumberColumn("% Manual Obs", format="%.2f%%"),
                    "esp_manual_pct": st.column_config.NumberColumn("% Manual Esp", format="%.2f%%"),
                    "z_manual": st.column_config.NumberColumn("Z Manual", format="%+.1fσ"),
                    "habilitacao_manual_total": st.column_config.NumberColumn("Qtd Manual", format="%d"),
                    "total_votos_log": st.column_config.NumberColumn("Votos Urna", format="%d")
                }
            )
            if ev_bio and ev_bio.selection and ev_bio.selection.rows:
                st.divider()
                renderizar_detalhe_individual(sel_bio_z3.iloc[ev_bio.selection.rows[0]], df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)

    # ------------------------------------------
    # ABA 7: 🔀 CRUZAMENTO
    # ------------------------------------------
    with tab_cruz:
        st.markdown(f"#### 🔀 Cruzamento Bivariado: {eixo_x_nome} × {eixo_y_nome}")
        df_cruz = df_filtrado[df_filtrado["total_votos_log"] > 0]
        if df_cruz.empty:
            st.info("Nenhuma seção com dados válidos para cruzamento.")
        else:
            usa_z = "Padronizados" in tipo_eixos
            col_x_plot = CRITERIOS_NOMES[eixo_x_nome][0] if usa_z else CRITERIOS_NOMES[eixo_x_nome][1]
            col_y_plot = CRITERIOS_NOMES[eixo_y_nome][0] if usa_z else CRITERIOS_NOMES[eixo_y_nome][1]
            rotulo_x_plot = f"Z {eixo_x_nome} (em σ)" if usa_z else CRITERIOS_NOMES[eixo_x_nome][2]
            rotulo_y_plot = f"Z {eixo_y_nome} (em σ)" if usa_z else CRITERIOS_NOMES[eixo_y_nome][2]

            mascara_quadrante = df_cruz["score_cruzado"] >= limite_cruzamento
            d_cruz_amostrado = amostrar_para_grafico(df_cruz, mascara_quadrante)

            fig_cruz = go.Figure()

            # Fundo
            d_cruz_fundo = d_cruz_amostrado[~mascara_quadrante]
            fig_cruz.add_trace(go.Scattergl(
                x=d_cruz_fundo[col_x_plot],
                y=d_cruz_fundo[col_y_plot],
                mode="markers",
                name="Demais Seções",
                marker=dict(size=4.5, color=COR_NEUTRA_PONTOS, opacity=0.35),
                text=d_cruz_fundo["municipio_nome"].astype(str) + " · Z" + d_cruz_fundo["zona"].astype(str) + " · S" + d_cruz_fundo["secao"].astype(str),
                hovertemplate="<b>%{text}</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>"
            ))

            # Quadrante Crítico
            d_cruz_crit = d_cruz_amostrado[mascara_quadrante]
            fig_cruz.add_trace(go.Scattergl(
                x=d_cruz_crit[col_x_plot],
                y=d_cruz_crit[col_y_plot],
                mode="markers",
                name=f"Quadrante Crítico (Score ≥ {limite_cruzamento}σ)",
                marker=dict(size=8.5, color=COR_DESTAQUE_VERMELHO, opacity=0.95),
                text=d_cruz_crit["municipio_nome"].astype(str) + " · Z" + d_cruz_crit["zona"].astype(str) + " · S" + d_cruz_crit["secao"].astype(str),
                hovertemplate="<b>%{text}</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<br>Score Cruzado: %{marker.size:.1f}<extra></extra>"
            ))

            # Sombra de destaque no quadrante crítico superior-direito
            if usa_z:
                fig_cruz.add_shape(
                    type="rect",
                    x0=limite_cruzamento,
                    x1=15,
                    y0=limite_cruzamento,
                    y1=25,
                    fillcolor=COR_DESTAQUE_VERMELHO,
                    opacity=0.08,
                    line_width=0
                )
                fig_cruz.add_vline(x=limite_cruzamento, line_dash="dash", line_color=COR_DESTAQUE_VERMELHO, annotation_text=f"+{limite_cruzamento}σ")
                fig_cruz.add_hline(y=limite_cruzamento, line_dash="dash", line_color=COR_DESTAQUE_VERMELHO, annotation_text=f"+{limite_cruzamento}σ")

            fig_cruz.update_layout(
                template=plotly_theme,
                title=f"Dispersão Bivariada: {eixo_x_nome} vs {eixo_y_nome}",
                xaxis_title=rotulo_x_plot,
                yaxis_title=rotulo_y_plot,
                height=560,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(fig_cruz, use_container_width=True)

            st.markdown(f"**Seções no Quadrante Crítico ({eixo_x_nome} + {eixo_y_nome} simultâneos):**")
            sel_cruz = df_cruz[mascara_quadrante].sort_values("score_cruzado", ascending=False)
            cols_cruz = ["uf", "municipio_nome", "zona", "secao", "score_cruzado", "n_criterios", "criterios_rotulo", "pct_abstencao", "z_abstencao", "pct_apos_17h", "z_pos17", "z_manual", "total_aptos"]
            cols_cruz_exibir = [c for c in cols_cruz if c in sel_cruz.columns]

            ev_cruz = st.dataframe(
                sel_cruz[cols_cruz_exibir],
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="grid_cruz",
                height=340,
                column_config={
                    "score_cruzado": st.column_config.NumberColumn("Score Cruzado", format="%.2fσ"),
                    "pct_abstencao": st.column_config.NumberColumn("Abstenção", format="%.2f%%"),
                    "z_abstencao": st.column_config.NumberColumn("Z Abstenção", format="%+.1fσ"),
                    "pct_apos_17h": st.column_config.NumberColumn("% Pós-17h", format="%.1f%%"),
                    "z_pos17": st.column_config.NumberColumn("Z Pós-17h", format="%+.1fσ"),
                    "z_manual": st.column_config.NumberColumn("Z Manual", format="%+.1fσ"),
                    "total_aptos": st.column_config.NumberColumn("Aptos", format="%d")
                }
            )
            st.download_button(
                "⬇️ Exportar Seções do Quadrante Crítico (CSV)",
                data=sel_cruz[cols_cruz_exibir].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name="cruzamento_critico.csv",
                mime="text/csv"
            )
            if ev_cruz and ev_cruz.selection and ev_cruz.selection.rows:
                st.divider()
                renderizar_detalhe_individual(sel_cruz.iloc[ev_cruz.selection.rows[0]], df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)
