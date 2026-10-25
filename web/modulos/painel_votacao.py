"""
Módulo do Painel de Votação (Telão Interativo da Apuração).
Inspirado na cobertura analítica e dinâmica da TV Globo (William Bonner e Renata Lo Prete).
Exibe o placar de apuração em tempo real com fotos/cards dos candidatos, barra proporcional
de disputa, mapa coroplético do Brasil e drill-down hierárquico por estado e município.
Suporta arquitetura multi-eleição (ano e turno) com carregamento 100% Local-First.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Diretórios de geometria local-first
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
GEODATA_DIR = ROOT_DIR / "db" / "geodata"
BR_ESTADOS_GEOJSON = GEODATA_DIR / "br_estados.json"
UFS_GEOJSON_DIR = GEODATA_DIR / "ufs"

# Catálogo declarativo multi-eleição
CATALOGO_ELEICOES = {
    (2026, 1): {
        "titulo": "Eleição Presidencial 2026 — 1º Turno",
        "data": "04 de Outubro de 2026",
        "status_oficial": "2º TURNO CONFIRMADO",
        "status_cor": "#f59e0b",
        "candidatos": {
            22: {
                "nome_urna": "FLÁVIO BOLSONARO",
                "partido": "PL",
                "numero": 22,
                "cor": "#1E88E5",
                "cor_fundo": "rgba(30, 136, 229, 0.12)",
                "cor_borda": "#1E88E5",
                "coluna_votos": "votos_cand_22"
            },
            13: {
                "nome_urna": "LULA",
                "partido": "PT",
                "numero": 13,
                "cor": "#E53935",
                "cor_fundo": "rgba(229, 57, 53, 0.12)",
                "cor_borda": "#E53935",
                "coluna_votos": "votos_cand_13"
            }
        }
    }
}

# Nomes oficiais das 27 Unidades Federativas
NOMES_UFS = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins"
}


@st.cache_data(show_spinner=False)
def carregar_geojson_estados() -> Optional[Dict[str, Any]]:
    """Carrega o GeoJSON simplificado dos 27 estados do Brasil (Local-First)."""
    if not BR_ESTADOS_GEOJSON.exists():
        return None
    try:
        with open(BR_ESTADOS_GEOJSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def carregar_geojson_uf(uf: str) -> Optional[Dict[str, Any]]:
    """Carrega o GeoJSON dos municípios de uma UF específica sob demanda (Local-First)."""
    uf_path = UFS_GEOJSON_DIR / f"{uf.upper()}.json"
    if not uf_path.exists():
        return None
    try:
        with open(uf_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def renderizar_placar_candidatos(
    meta_eleicao: Dict[str, Any],
    cand_1: Dict[str, Any],
    cand_2: Dict[str, Any],
    v1: int,
    v2: int,
    total_validos: int,
    modo_escuro: bool,
    fmt_int_br,
    fmt_float_br
):
    """Renderiza os cards dos candidatos estilo telão da TV Globo (Face-to-Face)."""
    p1 = (v1 / total_validos * 100) if total_validos > 0 else 0.0
    p2 = (v2 / total_validos * 100) if total_validos > 0 else 0.0
    
    # Identifica quem está na frente
    na_frente_1 = v1 >= v2
    delta_votos = abs(v1 - v2)
    delta_pct = abs(p1 - p2)

    bg_card = "#161b22" if modo_escuro else "#ffffff"
    border_color = "#30363d" if modo_escuro else "#e2e8f0"
    text_color = "#f0f2f6" if modo_escuro else "#0f172a"
    sub_color = "#94a3b8" if modo_escuro else "#64748b"

    c1_cor = cand_1["cor"]
    c2_cor = cand_2["cor"]
    borda_1 = c1_cor if na_frente_1 else border_color
    borda_2 = c2_cor if not na_frente_1 else border_color
    shadow_1 = f"0 0 15px {c1_cor}33" if na_frente_1 else "none"
    shadow_2 = f"0 0 15px {c2_cor}33" if not na_frente_1 else "none"
    badge_lider_1 = f'<span style="background-color: {c1_cor}; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">LIDERANÇA</span>' if na_frente_1 else ""
    badge_lider_2 = f'<span style="background-color: {c2_cor}; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">LIDERANÇA</span>' if not na_frente_1 else ""

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown(
            f"""
            <div style="background-color: {bg_card}; border: 2px solid {borda_1}; 
                        border-radius: 12px; padding: 1.25rem; box-shadow: {shadow_1};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="background-color: {c1_cor}; color: #ffffff; font-weight: 800; font-size: 0.9rem; padding: 2px 8px; border-radius: 6px;">
                            {cand_1['numero']}
                        </span>
                        <span style="font-weight: 700; color: {c1_cor}; font-size: 0.95rem;">
                            {cand_1['partido']}
                        </span>
                    </div>
                    {badge_lider_1}
                </div>
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1.35rem; font-weight: 800; color: {text_color}; letter-spacing: -0.02em;">
                    {cand_1['nome_urna']}
                </h3>
                <div style="display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.35rem;">
                    <span style="font-size: 2.5rem; font-weight: 900; color: {c1_cor}; line-height: 1;">
                        {fmt_float_br(p1)}%
                    </span>
                    <span style="font-size: 0.95rem; color: {sub_color}; font-weight: 600;">
                        {fmt_int_br(v1)} votos
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_c2:
        st.markdown(
            f"""
            <div style="background-color: {bg_card}; border: 2px solid {borda_2}; 
                        border-radius: 12px; padding: 1.25rem; box-shadow: {shadow_2};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="background-color: {c2_cor}; color: #ffffff; font-weight: 800; font-size: 0.9rem; padding: 2px 8px; border-radius: 6px;">
                            {cand_2['numero']}
                        </span>
                        <span style="font-weight: 700; color: {c2_cor}; font-size: 0.95rem;">
                            {cand_2['partido']}
                        </span>
                    </div>
                    {badge_lider_2}
                </div>
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1.35rem; font-weight: 800; color: {text_color}; letter-spacing: -0.02em;">
                    {cand_2['nome_urna']}
                </h3>
                <div style="display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.35rem;">
                    <span style="font-size: 2.5rem; font-weight: 900; color: {c2_cor}; line-height: 1;">
                        {fmt_float_br(p2)}%
                    </span>
                    <span style="font-size: 0.95rem; color: {sub_color}; font-weight: 600;">
                        {fmt_int_br(v2)} votos
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Barra proporcional horizontal de disputa (Tug-of-war)
    st.markdown(
        f"""
        <div style="margin-top: 1rem; margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700; color: {sub_color}; margin-bottom: 4px;">
                <span>{cand_1['nome_urna']} ({fmt_float_br(p1)}%)</span>
                <span>Diferença: {fmt_int_br(delta_votos)} votos ({fmt_float_br(delta_pct)} pp)</span>
                <span>{cand_2['nome_urna']} ({fmt_float_br(p2)}%)</span>
            </div>
            <div style="width: 100%; height: 14px; background-color: #30363d; border-radius: 9999px; overflow: hidden; display: flex; position: relative;">
                <div style="width: {p1}%; height: 100%; background-color: {cand_1['cor']};"></div>
                <div style="width: {p2}%; height: 100%; background-color: {cand_2['cor']};"></div>
                <!-- Marcador de 50% -->
                <div style="position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; background-color: #ffffff; opacity: 0.8; z-index: 2;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def renderizar_mapa_nacional(
    df: pd.DataFrame,
    cand_1: Dict[str, Any],
    cand_2: Dict[str, Any],
    modo_escuro: bool,
    plotly_theme: str
):
    """Renderiza o Mapa Coroplético do Brasil com os estados coloridos pelo vencedor."""
    geo_brasil = carregar_geojson_estados()
    if not geo_brasil:
        st.warning("⚠️ Malha geográfica nacional não encontrada em `db/geodata/br_estados.json`.")
        return

    # Agregação por UF
    df_uf = df.groupby("uf", observed=True).agg({
        "pres_total_validos": "sum",
        cand_1["coluna_votos"]: "sum",
        cand_2["coluna_votos"]: "sum"
    }).reset_index()

    v1_col = cand_1["coluna_votos"]
    v2_col = cand_2["coluna_votos"]

    df_uf["pct_c1"] = (df_uf[v1_col] / df_uf["pres_total_validos"] * 100).round(2)
    df_uf["pct_c2"] = (df_uf[v2_col] / df_uf["pres_total_validos"] * 100).round(2)
    
    df_uf["vencedor"] = df_uf.apply(
        lambda r: cand_1["nome_urna"] if r[v1_col] >= r[v2_col] else cand_2["nome_urna"],
        axis=1
    )
    df_uf["nome_uf"] = df_uf["uf"].map(NOMES_UFS).fillna(df_uf["uf"])

    cor_map = {
        cand_1["nome_urna"]: cand_1["cor"],
        cand_2["nome_urna"]: cand_2["cor"]
    }

    fig = px.choropleth(
        df_uf,
        geojson=geo_brasil,
        locations="uf",
        featureidkey="id",
        color="vencedor",
        color_discrete_map=cor_map,
        hover_name="nome_uf",
        hover_data={
            "uf": False,
            "vencedor": True,
            "pct_c1": ":.2f",
            "pct_c2": ":.2f",
            "pres_total_validos": ":,"
        },
        labels={
            "pct_c1": f"% {cand_1['partido']}",
            "pct_c2": f"% {cand_2['partido']}",
            "pres_total_validos": "Votos Válidos",
            "vencedor": "Vencedor no Estado"
        }
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="rgba(0,0,0,0)"
    )

    fig.update_layout(
        template=plotly_theme,
        margin={"r": 0, "t": 10, "l": 0, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            title_text=""
        ),
        height=520
    )

    st.plotly_chart(fig, use_container_width=True)


def renderizar_mapa_estadual(
    df_uf: pd.DataFrame,
    uf: str,
    cand_1: Dict[str, Any],
    cand_2: Dict[str, Any],
    modo_escuro: bool,
    plotly_theme: str
):
    """Renderiza o Mapa Coroplético Municipal da UF selecionada."""
    geo_uf = carregar_geojson_uf(uf)
    nome_uf = NOMES_UFS.get(uf, uf)

    if not geo_uf:
        st.warning(f"⚠️ Malha municipal de {nome_uf} ({uf}) não encontrada em `db/geodata/ufs/{uf}.json`.")
        return

    # Agregação municipal da UF
    v1_col = cand_1["coluna_votos"]
    v2_col = cand_2["coluna_votos"]

    df_mun = df_uf.groupby(["municipio", "municipio_nome"], observed=True).agg({
        "pres_total_validos": "sum",
        v1_col: "sum",
        v2_col: "sum"
    }).reset_index()

    df_mun["pct_c1"] = (df_mun[v1_col] / df_mun["pres_total_validos"] * 100).round(2)
    df_mun["pct_c2"] = (df_mun[v2_col] / df_mun["pres_total_validos"] * 100).round(2)

    df_mun["vencedor"] = df_mun.apply(
        lambda r: cand_1["nome_urna"] if r[v1_col] >= r[v2_col] else cand_2["nome_urna"],
        axis=1
    )

    cor_map = {
        cand_1["nome_urna"]: cand_1["cor"],
        cand_2["nome_urna"]: cand_2["cor"]
    }

    fig = px.choropleth(
        df_mun,
        geojson=geo_uf,
        locations="municipio",
        featureidkey="id",
        color="vencedor",
        color_discrete_map=cor_map,
        hover_name="municipio_nome",
        hover_data={
            "municipio": False,
            "vencedor": True,
            "pct_c1": ":.2f",
            "pct_c2": ":.2f",
            "pres_total_validos": ":,"
        },
        labels={
            "pct_c1": f"% {cand_1['partido']}",
            "pct_c2": f"% {cand_2['partido']}",
            "pres_total_validos": "Votos Válidos",
            "vencedor": "Vencedor no Município"
        }
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="rgba(0,0,0,0)"
    )

    fig.update_layout(
        template=plotly_theme,
        margin={"r": 0, "t": 10, "l": 0, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            title_text=""
        ),
        height=520
    )

    st.plotly_chart(fig, use_container_width=True)


def renderizar_painel_votacao(
    df: pd.DataFrame,
    ano: int = 2026,
    turno: int = 1,
    modo_escuro: bool = True,
    plotly_theme: str = "plotly_dark",
    fmt_int_br=lambda x: f"{x:,}".replace(",", "."),
    fmt_float_br=lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
):
    """
    Função principal de renderização do Painel de Votação (Telão Interativo da Apuração).
    """
    chave_pleito = (ano, turno)
    meta = CATALOGO_ELEICOES.get(chave_pleito)

    if not meta:
        st.info(
            f"🗳️ **{ano} — {turno}º Turno: Base em Sincronização**\n\n"
            "Os dados analíticos e de votação para este pleito serão disponibilizados assim que homologados "
            "e compilados na base local do tribunal."
        )
        return

    candidatos = meta["candidatos"]
    chaves_cands = list(candidatos.keys())
    cand_1 = candidatos[chaves_cands[0]]
    cand_2 = candidatos[chaves_cands[1]]

    # Controle de navegação (Drill-down)
    if "painel_uf_ativa" not in st.session_state:
        st.session_state["painel_uf_ativa"] = None
    if "painel_mun_ativo" not in st.session_state:
        st.session_state["painel_mun_ativo"] = None

    uf_selecionada = st.session_state["painel_uf_ativa"]
    mun_selecionado = st.session_state["painel_mun_ativo"]

    # Barra superior de status da apuração estilo TV Globo
    total_secoes = len(df)
    secoes_apuradas = len(df[df["pres_total_validos"] > 0])
    pct_totalizacao = (secoes_apuradas / total_secoes * 100) if total_secoes > 0 else 0.0

    # Header dinâmico com breadcrumb
    col_nav1, col_nav2 = st.columns([3, 1])
    with col_nav1:
        if uf_selecionada is None:
            breadcrumb_txt = "🇧🇷 **BRASIL — APURAÇÃO NACIONAL**"
        else:
            nome_uf = NOMES_UFS.get(uf_selecionada, uf_selecionada)
            if mun_selecionado is None:
                breadcrumb_txt = f"🇧🇷 Brasil  ›  📍 **{nome_uf.upper()} ({uf_selecionada})**"
            else:
                breadcrumb_txt = f"🇧🇷 Brasil  ›  📍 {nome_uf}  ›  🏙️ **{mun_selecionado.upper()}**"

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.15rem; font-weight: 800; letter-spacing: -0.01em;">
                    {breadcrumb_txt}
                </span>
                <span style="background-color: {meta['status_cor']}; color: #000000; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">
                    {meta['status_oficial']}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_nav2:
        if uf_selecionada is not None:
            if st.button("🔙 Voltar à Visão Nacional", use_container_width=True, key="btn_voltar_nacional"):
                st.session_state["painel_uf_ativa"] = None
                st.session_state["painel_mun_ativo"] = None
                st.rerun()

    # Barra de Progresso de Totalização
    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: #94a3b8; margin-bottom: 4px;">
                <span>SEÇÕES TOTALIZADAS: {fmt_float_br(pct_totalizacao)}% ({fmt_int_br(secoes_apuradas)} de {fmt_int_br(total_secoes)})</span>
                <span>ÚLTIMA ATUALIZAÇÃO OFICIAL</span>
            </div>
            <div style="width: 100%; height: 6px; background-color: #30363d; border-radius: 9999px; overflow: hidden;">
                <div style="width: {pct_totalizacao}%; height: 100%; background: linear-gradient(90deg, #10b981, #059669);"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Filtra os dados conforme o nível de drill-down
    if uf_selecionada is None:
        df_foco = df
    else:
        df_foco = df[df["uf"] == uf_selecionada]
        if mun_selecionado is not None:
            df_foco = df_foco[df_foco["municipio_nome"] == mun_selecionado]

    # Votação do nível ativo
    v1_tot = int(df_foco[cand_1["coluna_votos"]].sum())
    v2_tot = int(df_foco[cand_2["coluna_votos"]].sum())
    validos_tot = int(df_foco["pres_total_validos"].sum())
    aptos_tot = int(df_foco["total_aptos"].sum())
    comp_tot = int(df_foco["comparecimento_bu"].sum())
    abst_tot = int(df_foco["faltosos_bu"].sum())

    pct_comp = (comp_tot / aptos_tot * 100) if aptos_tot > 0 else 0.0
    pct_abst = (abst_tot / aptos_tot * 100) if aptos_tot > 0 else 0.0

    # 1. PLACAR FACE-TO-FACE
    renderizar_placar_candidatos(
        meta_eleicao=meta,
        cand_1=cand_1,
        cand_2=cand_2,
        v1=v1_tot,
        v2=v2_tot,
        total_validos=validos_tot,
        modo_escuro=modo_escuro,
        fmt_int_br=fmt_int_br,
        fmt_float_br=fmt_float_br
    )

    # Linha divisória
    st.markdown("<hr style='margin: 1.25rem 0; border: none; border-top: 1px solid #30363d;'>", unsafe_allow_html=True)

    # 2. ÁREA INTERATIVA DO MAPA & SELEÇÃO
    col_mapa, col_painel = st.columns([1.7, 1.0])

    with col_mapa:
        if uf_selecionada is None:
            st.markdown("#### 🗺️ Mapa de Vencedores por Estado")
            renderizar_mapa_nacional(df, cand_1, cand_2, modo_escuro, plotly_theme)
        else:
            nome_uf = NOMES_UFS.get(uf_selecionada, uf_selecionada)
            st.markdown(f"#### 🗺️ Vencedores por Município — {nome_uf} ({uf_selecionada})")
            renderizar_mapa_estadual(df_foco if mun_selecionado is None else df[df["uf"] == uf_selecionada], 
                                     uf_selecionada, cand_1, cand_2, modo_escuro, plotly_theme)

    with col_painel:
        if uf_selecionada is None:
            st.markdown("#### 🔍 Explorar Estado")
            st.caption("Selecione um estado para abrir o mapa municipal detalhado:")

            lista_ufs = sorted(list(df["uf"].unique()))
            # Remove exterior se houver
            lista_ufs = [u for u in lista_ufs if u in NOMES_UFS]

            opcoes_display = [f"{NOMES_UFS[u]} ({u})" for u in lista_ufs]
            
            sel_uf_idx = st.selectbox(
                "Estado:",
                options=range(len(opcoes_display)),
                format_func=lambda i: opcoes_display[i],
                key="seletor_uf_drilldown"
            )

            if st.button("📍 Abrir Detalhe do Estado", use_container_width=True, type="primary"):
                st.session_state["painel_uf_ativa"] = lista_ufs[sel_uf_idx]
                st.session_state["painel_mun_ativo"] = None
                st.rerun()

            # Resumo dos Maiores Colégios Eleitorais
            st.markdown("<div style='margin-top: 1.25rem;'></div>", unsafe_allow_html=True)
            st.markdown("##### 🏆 Maiores Colégios Eleitorais")
            
            df_top_ufs = df.groupby("uf", observed=True).agg({
                "pres_total_validos": "sum",
                cand_1["coluna_votos"]: "sum",
                cand_2["coluna_votos"]: "sum"
            }).reset_index()

            v1_c = cand_1["coluna_votos"]
            v2_c = cand_2["coluna_votos"]
            df_top_ufs["pct_1"] = (df_top_ufs[v1_c] / df_top_ufs["pres_total_validos"] * 100).round(1)
            df_top_ufs["pct_2"] = (df_top_ufs[v2_c] / df_top_ufs["pres_total_validos"] * 100).round(1)
            df_top_ufs["Vencedor"] = df_top_ufs.apply(lambda r: cand_1["partido"] if r[v1_c] >= r[v2_c] else cand_2["partido"], axis=1)

            df_top_ufs = df_top_ufs.sort_values(by="pres_total_validos", ascending=False).head(5)
            
            tabela_resumo = pd.DataFrame({
                "UF": df_top_ufs["uf"],
                "Vencedor": df_top_ufs["Vencedor"],
                f"% {cand_1['partido']}": df_top_ufs["pct_1"],
                f"% {cand_2['partido']}": df_top_ufs["pct_2"],
                "Válidos": df_top_ufs["pres_total_validos"]
            })

            st.dataframe(
                tabela_resumo,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Válidos": st.column_config.NumberColumn(format="%d"),
                    f"% {cand_1['partido']}": st.column_config.NumberColumn(format="%.1f%%"),
                    f"% {cand_2['partido']}": st.column_config.NumberColumn(format="%.1f%%")
                }
            )

        else:
            # Visão Estadual Ativa: Seletor de Município
            st.markdown(f"#### 🔍 Municípios de {NOMES_UFS.get(uf_selecionada, uf_selecionada)}")
            
            df_estado_muns = df[df["uf"] == uf_selecionada]
            lista_muns = sorted(list(df_estado_muns["municipio_nome"].unique()))

            sel_mun = st.selectbox(
                "Filtrar Município:",
                options=["(Todos os Municípios)"] + lista_muns,
                index=0 if mun_selecionado is None else (lista_muns.index(mun_selecionado) + 1 if mun_selecionado in lista_muns else 0),
                key="seletor_mun_drilldown"
            )

            if sel_mun != "(Todos os Municípios)" and sel_mun != mun_selecionado:
                st.session_state["painel_mun_ativo"] = sel_mun
                st.rerun()
            elif sel_mun == "(Todos os Municípios)" and mun_selecionado is not None:
                st.session_state["painel_mun_ativo"] = None
                st.rerun()

            # Métricas cívicas adicionais da localidade
            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📊 Indicadores Cívicos")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Comparecimento", f"{fmt_float_br(pct_comp)}%", f"{fmt_int_br(comp_tot)} eleitores")
            with col_m2:
                st.metric("Abstenção", f"{fmt_float_br(pct_abst)}%", f"{fmt_int_br(abst_tot)} faltosos", delta_color="inverse")

            # Ranking dos maiores municípios da UF
            st.markdown("##### 🏙️ Mais Votados do Estado")
            df_m_rank = df_estado_muns.groupby("municipio_nome", observed=True).agg({
                "pres_total_validos": "sum",
                cand_1["coluna_votos"]: "sum",
                cand_2["coluna_votos"]: "sum"
            }).reset_index()

            df_m_rank["pct_1"] = (df_m_rank[cand_1["coluna_votos"]] / df_m_rank["pres_total_validos"] * 100).round(1)
            df_m_rank["pct_2"] = (df_m_rank[cand_2["coluna_votos"]] / df_m_rank["pres_total_validos"] * 100).round(1)
            df_m_rank["Vencedor"] = df_m_rank.apply(lambda r: cand_1["partido"] if r[cand_1["coluna_votos"]] >= r[cand_2["coluna_votos"]] else cand_2["partido"], axis=1)
            df_m_rank = df_m_rank.sort_values(by="pres_total_validos", ascending=False).head(5)

            tabela_muns = pd.DataFrame({
                "Município": df_m_rank["municipio_nome"],
                "Vencedor": df_m_rank["Vencedor"],
                f"% {cand_1['partido']}": df_m_rank["pct_1"],
                f"% {cand_2['partido']}": df_m_rank["pct_2"],
                "Válidos": df_m_rank["pres_total_validos"]
            })

            st.dataframe(
                tabela_muns,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Válidos": st.column_config.NumberColumn(format="%d"),
                    f"% {cand_1['partido']}": st.column_config.NumberColumn(format="%.1f%%"),
                    f"% {cand_2['partido']}": st.column_config.NumberColumn(format="%.1f%%")
                }
            )
