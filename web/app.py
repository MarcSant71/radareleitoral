"""
Painel Interativo de Auditoria Eleitoral 2026 (Clone Avançado do esteleicao.com).
Conecta diretamente ao banco relacional SQLite local (eleicoes2026.db) para exibir
anomalias de votos pós-17h, liberação manual por mesário e ociosidade.
"""

import sys
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_web_dir = Path(__file__).resolve().parent
_root_dir = _web_dir.parent
for _p in (_web_dir, _root_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from dados.db import DB_PATH
from dados.carregador import (
    obter_dados_analiticos,
    obter_locais_votacao,
    obter_secoes_mapeadas,
    PARQUET_CACHE_PATH,
    MAPA_REGIOES
)
from motores.estatistica import aplicar_motor_estatistico, aplicar_motor_abstencao
from modulos.auditoria import renderizar_auditoria
from modulos.abstencao import renderizar_abstencao
from modulos.mapa import renderizar_mapa
from modulos.governanca import renderizar_governanca
from versao import VERSAO_APP, COMMIT_APP, VERSAO_DISPLAY

st.set_page_config(
    page_title="Radar Eleitoral - Inteligência Analítica e Auditoria de Urnas",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "modo_escuro" not in st.session_state:
    if "tema" in st.query_params:
        st.session_state["modo_escuro"] = (st.query_params["tema"].lower() != "claro")
    else:
        st.session_state["modo_escuro"] = True

modo_escuro = st.session_state["modo_escuro"]
plotly_theme = "plotly_dark" if modo_escuro else "plotly_white"

# Custom CSS dinâmico (KISS): sem 3 pontinhos e com suporte instantâneo a Claro/Escuro em TODOS os elementos
if modo_escuro:
    css_tema = """
    /* ========================================================
       TEMA ESCURO (DARK MODE) - TODOS OS ELEMENTOS POLIDOS
       ======================================================== */
    .stApp {
        background-color: #0e1117 !important;
        color: #f0f2f6 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d !important;
    }
    [data-testid="stSidebarHeader"]::before {
        color: #f0f2f6 !important;
        opacity: 0.75 !important;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, [data-testid="stMarkdownContainer"] * {
        color: #f0f2f6 !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] * {
        color: #8b949e !important;
    }

    /* Links */
    .stApp a,
    [data-testid="stMarkdownContainer"] a {
        color: #58a6ff !important;
        text-decoration: underline !important;
    }
    .stApp a:hover,
    [data-testid="stMarkdownContainer"] a:hover {
        color: #79c0ff !important;
    }

    /* Código inline e blocos de código */
    .stApp code,
    [data-testid="stMarkdownContainer"] code,
    [data-testid="stMarkdownContainer"] p code,
    [data-testid="stMarkdownContainer"] li code,
    [data-testid="stMarkdownContainer"] strong code {
        background-color: #21262d !important;
        color: #79c0ff !important;
        border: 1px solid #30363d !important;
        border-radius: 4px !important;
        padding: 0.15em 0.45em !important;
        font-size: 0.88em !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }
    .stApp pre,
    [data-testid="stCode"],
    [data-testid="stCodeBlock"],
    pre[data-testid="stCodeBlock"],
    div[data-testid="stCodeBlock"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    .stApp pre code,
    [data-testid="stCode"] code,
    [data-testid="stCodeBlock"] code,
    [data-testid="stCodeBlock"] code * {
        background-color: transparent !important;
        color: #f0f2f6 !important;
        border: none !important;
        padding: 0 !important;
    }

    /* Citações (Blockquotes) */
    .stApp blockquote,
    [data-testid="stMarkdownContainer"] blockquote {
        border-left: 4px solid #1f6feb !important;
        background-color: #161b22 !important;
        padding: 0.75rem 1rem !important;
        border-radius: 0 8px 8px 0 !important;
        margin: 1rem 0 !important;
    }
    .stApp blockquote *,
    [data-testid="stMarkdownContainer"] blockquote * {
        color: #f0f2f6 !important;
    }

    /* 1. SELECTBOXES (DROPDOWNS) & INPUTS */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: #f0f2f6 !important;
    }
    div[data-baseweb="select"] *,
    div[data-baseweb="input"] *,
    div[data-baseweb="input"] input {
        color: #f0f2f6 !important;
        fill: #f0f2f6 !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
    }
    ul[role="listbox"] li {
        background-color: #161b22 !important;
        color: #f0f2f6 !important;
    }
    ul[role="listbox"] li:hover, ul[role="listbox"] li[aria-selected="true"] {
        background-color: #30363d !important;
        color: #58a6ff !important;
    }

    /* 2. BOTÃO ATUALIZAR PÁGINA */
    div.stButton > button, [data-testid="stBaseButton-secondary"] {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: #f0f2f6 !important;
        font-weight: 500 !important;
    }
    div.stButton > button *, [data-testid="stBaseButton-secondary"] * {
        color: #f0f2f6 !important;
    }
    div.stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover {
        background-color: #30363d !important;
        border-color: #58a6ff !important;
        color: #ffffff !important;
    }

    /* 2.1 MODAL DIALOG (MODO ESCURO) */
    div[role="dialog"],
    div[data-testid="stDialog"] > div {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        color: #f0f2f6 !important;
        border-radius: 12px !important;
    }
    div[role="dialog"] h2,
    div[data-testid="stDialog"] h2 {
        color: #f0f2f6 !important;
    }
    div[role="dialog"] button[aria-label="Close"],
    div[data-testid="stDialog"] button[aria-label="Close"] {
        color: #f0f2f6 !important;
    }

    /* 3. EXPANDER */
    [data-testid="stExpander"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        color: #f0f2f6 !important;
    }
    [data-testid="stExpander"] summary * {
        color: #f0f2f6 !important;
        fill: #f0f2f6 !important;
    }

    /* 5. CHECKBOX & RADIO */
    [data-testid="stCheckbox"] label *,
    [data-testid="stRadio"] label * {
        color: #f0f2f6 !important;
    }

    /* 6. CARDS DE MÉTRICA */
    [data-testid="stMetric"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
        color: #f0f2f6 !important;
    }
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] label,
    [data-testid="stMetricLabel"] span {
        color: #c9d1d9 !important;
    }
    /* Ícone de ajuda (?) legível e nítido no modo escuro */
    .stApp .stTooltipIcon svg,
    .stApp .stTooltipHoverTarget svg,
    .stApp [data-testid="stTooltipIcon"] svg {
        color: #94a3b8 !important;
        stroke: #94a3b8 !important;
        fill: none !important;
        opacity: 0.85 !important;
        transition: color 0.15s ease, opacity 0.15s ease !important;
    }
    .stApp .stTooltipIcon svg *,
    .stApp .stTooltipHoverTarget svg *,
    .stApp [data-testid="stTooltipIcon"] svg * {
        stroke: #94a3b8 !important;
        fill: none !important;
    }
    .stApp .stTooltipHoverTarget:hover svg,
    .stApp .stTooltipIcon:hover svg,
    .stApp [data-testid="stTooltipIcon"]:hover svg,
    .stApp [data-testid="stTooltipHoverTarget"]:hover svg * {
        color: #58a6ff !important;
        stroke: #58a6ff !important;
        opacity: 1 !important;
    }
    /* Conteúdo flutuante do tooltip no Modo Escuro (Alto Contraste Invertido para Acessibilidade) */
    [data-baseweb="tooltip"],
    div[data-baseweb="tooltip"],
    div[role="tooltip"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    [data-testid="stTooltipContent"],
    .stTooltipContent,
    [data-testid="stDataFrameTooltipContent"],
    .stDataFrameTooltipContent,
    [data-testid="stTooltipErrorContent"],
    .stTooltipErrorContent {
        background-color: #f8fafc !important;
        background: #f8fafc !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(88, 166, 255, 0.25) !important;
        padding: 8px 12px !important;
        max-width: 360px !important;
        line-height: 1.5 !important;
        z-index: 1000000 !important;
    }
    [data-testid="stTooltipContent"] div,
    .stTooltipContent div,
    [data-testid="stDataFrameTooltipContent"] div,
    .stDataFrameTooltipContent div,
    [data-testid="stTooltipContent"] [data-testid="stMarkdownContainer"],
    .stTooltipContent [data-testid="stMarkdownContainer"],
    [data-testid="stDataFrameTooltipContent"] [data-testid="stMarkdownContainer"],
    .stDataFrameTooltipContent [data-testid="stMarkdownContainer"] {
        background: transparent !important;
        background-color: transparent !important;
    }
    [data-testid="stTooltipContent"] *,
    .stTooltipContent *,
    [data-testid="stDataFrameTooltipContent"] *,
    .stDataFrameTooltipContent *,
    [data-testid="stTooltipErrorContent"] *,
    .stTooltipErrorContent *,
    div[role="tooltip"] p,
    div[role="tooltip"] span {
        color: #0f172a !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        line-height: 1.5 !important;
    }
    [data-testid="stTooltipContent"] strong,
    .stTooltipContent strong,
    [data-testid="stDataFrameTooltipContent"] strong,
    .stDataFrameTooltipContent strong {
        color: #020617 !important;
        font-weight: 700 !important;
    }
    [data-testid="stTooltipContent"] code,
    .stTooltipContent code,
    [data-testid="stDataFrameTooltipContent"] code,
    .stDataFrameTooltipContent code {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        padding: 0.1em 0.35em !important;
    }

    /* 7. BOTÕES CIRCULARES DE TEMA E AJUDA (?) (MODO ESCURO) */
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"],
    div.st-key-btn_theme_toggle button,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"],
    div.st-key-btn_help button {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
        color: #f0f2f6 !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_theme_toggle button:hover,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_help button:hover {
        background-color: #21262d !important;
        border-color: #58a6ff !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.6) !important;
        color: #58a6ff !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:focus,
    div.st-key-btn_theme_toggle button:focus,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"]:focus,
    div.st-key-btn_help button:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px #58a6ff !important;
    }

    /* 8. NAVEGAÇÃO PRINCIPAL NO MODO ESCURO */
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"],
    .stApp [data-testid="stButtonGroup"],
    .stApp div.stButtonGroup {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 3px !important;
    }
    .stApp .st-key-aba_ativa [role="radiogroup"],
    .stApp [data-testid="stButtonGroup"] [role="radiogroup"] {
        display: flex !important;
        gap: 4px !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    .stApp .st-key-aba_ativa div,
    .stApp [data-testid="stButtonGroup"] div {
        background-color: transparent !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button,
    .stApp .st-key-aba_ativa button[data-variant="segmented_control"],
    .stApp [data-testid="stButtonGroup"] button,
    .stApp button[data-variant="segmented_control"],
    .stApp button[data-variant="segmented_control"]:not([data-selected]) {
        background-color: transparent !important;
        background: transparent !important;
        color: #8b949e !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        margin: 0 !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button *,
    .stApp .st-key-aba_ativa button[data-variant="segmented_control"] *,
    .stApp [data-testid="stButtonGroup"] button *,
    .stApp button[data-variant="segmented_control"] *,
    .stApp button[data-variant="segmented_control"]:not([data-selected]) * {
        color: #8b949e !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button:not([data-selected]):hover,
    .stApp button[data-variant="segmented_control"]:not([data-selected]):hover {
        background-color: rgba(110, 118, 129, 0.12) !important;
        color: #f0f2f6 !important;
        border-color: rgba(110, 118, 129, 0.25) !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button:not([data-selected]):hover *,
    .stApp button[data-variant="segmented_control"]:not([data-selected]):hover * {
        color: #f0f2f6 !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[data-selected],
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-selected="true"],
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-checked="true"],
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-pressed="true"],
    .stApp button[data-variant="segmented_control"][data-selected],
    .stApp button[data-variant="segmented_control"][aria-selected="true"],
    .stApp button[data-variant="segmented_control"][aria-checked="true"],
    .stApp button[data-variant="segmented_control"][aria-pressed="true"] {
        background-color: #21262d !important;
        background: #21262d !important;
        color: #58a6ff !important;
        font-weight: 600 !important;
        border: 1px solid #58a6ff !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
        position: relative !important;
        z-index: 2 !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[data-selected] *,
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-selected="true"] *,
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-checked="true"] *,
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
    .stApp button[data-variant="segmented_control"][data-selected] *,
    .stApp button[data-variant="segmented_control"][aria-selected="true"] *,
    .stApp button[data-variant="segmented_control"][aria-checked="true"] *,
    .stApp button[data-variant="segmented_control"][aria-pressed="true"] * {
        color: #58a6ff !important;
        font-weight: 600 !important;
    }

    /* 9. BOTÕES << (RECOLHER) E >> (EXPANDIR) NO MODO ESCURO */
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stSidebarCollapseButton"] button {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: #f0f2f6 !important;
    }
    [data-testid="stExpandSidebarButton"] button svg,
    [data-testid="stSidebarCollapseButton"] button svg {
        fill: #f0f2f6 !important;
        color: #f0f2f6 !important;
    }
    [data-testid="stExpandSidebarButton"] button:hover,
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #30363d !important;
        border-color: #58a6ff !important;
        color: #ffffff !important;
    }
    [data-testid="stExpandSidebarButton"] button:hover svg,
    [data-testid="stSidebarCollapseButton"] button:hover svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    /* Centralização e Cores do Spinner no Modo Escuro */
    [data-testid="stSpinner"],
    .stSpinner,
    .stCacheSpinner,
    div[data-testid="stSpinner"] {
        background-color: #161b22 !important;
        background: #161b22 !important;
        background-image: none !important;
        border: 1px solid #30363d !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.05) !important;
        color: #f0f2f6 !important;
    }
    [data-testid="stSpinner"] *,
    .stSpinner *,
    .stCacheSpinner * {
        background: transparent !important;
        background-image: none !important;
        color: #f0f2f6 !important;
    }
    [data-testid="stSpinnerIcon"],
    [data-testid="stSpinner"] [data-testid="stSpinnerIcon"],
    .stSpinner [data-testid="stSpinnerIcon"],
    .stCacheSpinner [data-testid="stSpinnerIcon"] {
        border-color: rgba(88, 166, 255, 0.25) !important;
        border-top-color: #58a6ff !important;
        border-width: 2.5px !important;
    }
    [data-testid="stSpinner"] svg,
    .stSpinner svg {
        stroke: #58a6ff !important;
        color: #58a6ff !important;
        fill: none !important;
    }

    /* Tabela / Grid Estruturado no Modo Escuro */
    [data-testid="stMarkdownContainer"] table {
        width: 100% !important;
        border-collapse: collapse !important;
        margin: 1rem 0 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
    }
    [data-testid="stMarkdownContainer"] table thead tr {
        background-color: #161b22 !important;
        border-bottom: 2px solid #30363d !important;
    }
    [data-testid="stMarkdownContainer"] table th {
        padding: 10px 14px !important;
        font-weight: 600 !important;
        color: #f0f2f6 !important;
        text-align: left !important;
        border-right: 1px solid #21262d !important;
    }
    [data-testid="stMarkdownContainer"] table th:nth-child(2) {
        text-align: center !important;
    }
    [data-testid="stMarkdownContainer"] table td {
        border-bottom: 1px solid #21262d !important;
        border-right: 1px solid #21262d !important;
        padding: 12px 14px !important;
        vertical-align: top !important;
        color: #c9d1d9 !important;
        line-height: 1.6 !important;
    }
    [data-testid="stMarkdownContainer"] table td:last-child,
    [data-testid="stMarkdownContainer"] table th:last-child {
        border-right: none !important;
    }
    [data-testid="stMarkdownContainer"] table td:nth-child(2) {
        text-align: center !important;
        color: #8b949e !important;
    }
    [data-testid="stMarkdownContainer"] table tbody tr:nth-child(even) {
        background-color: rgba(22, 27, 34, 0.45) !important;
    }
    [data-testid="stMarkdownContainer"] table tbody tr:hover {
        background-color: rgba(110, 118, 129, 0.12) !important;
    }

    /* 12. SKELETON SCREEN (MODO ESCURO - YOUTUBE SHIMMER) */
    .skeleton-card,
    [data-testid="stMarkdownContainer"] .skeleton-card {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
    }
    .skeleton-line,
    [data-testid="stMarkdownContainer"] .skeleton-line {
        background-color: #21262d !important;
    }
    .skeleton-card::after,
    .skeleton-line::after,
    .skeleton-tab-pill::after {
        background: linear-gradient(
            105deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.03) 25%,
            rgba(255, 255, 255, 0.14) 50%,
            rgba(255, 255, 255, 0.03) 75%,
            rgba(255, 255, 255, 0) 100%
        ) !important;
    }
    """
else:
    css_tema = """
    /* ========================================================
       TEMA CLARO (LIGHT MODE) - TODOS OS ELEMENTOS CORRIGIDOS
       ======================================================== */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebarHeader"]::before {
        color: #0f172a !important;
        opacity: 0.75 !important;
    }
    
    /* Textos, títulos e legendas */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, [data-testid="stMarkdownContainer"] * {
        color: #0f172a !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] * {
        color: #475569 !important;
    }

    /* Links */
    .stApp a,
    [data-testid="stMarkdownContainer"] a {
        color: #0284c7 !important;
        text-decoration: underline !important;
    }
    .stApp a:hover,
    [data-testid="stMarkdownContainer"] a:hover {
        color: #0369a1 !important;
    }

    /* Código inline e blocos de código */
    .stApp code,
    [data-testid="stMarkdownContainer"] code,
    [data-testid="stMarkdownContainer"] p code,
    [data-testid="stMarkdownContainer"] li code,
    [data-testid="stMarkdownContainer"] strong code {
        background-color: #f1f5f9 !important;
        color: #0369a1 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        padding: 0.15em 0.45em !important;
        font-size: 0.88em !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }
    .stApp pre,
    [data-testid="stCode"],
    [data-testid="stCodeBlock"],
    pre[data-testid="stCodeBlock"],
    div[data-testid="stCodeBlock"] {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    .stApp pre code,
    [data-testid="stCode"] code,
    [data-testid="stCodeBlock"] code,
    [data-testid="stCodeBlock"] code * {
        background-color: transparent !important;
        color: #0f172a !important;
        border: none !important;
        padding: 0 !important;
    }

    /* Citações (Blockquotes) */
    .stApp blockquote,
    [data-testid="stMarkdownContainer"] blockquote {
        border-left: 4px solid #0284c7 !important;
        background-color: #f1f5f9 !important;
        padding: 0.75rem 1rem !important;
        border-radius: 0 8px 8px 0 !important;
        margin: 1rem 0 !important;
    }
    .stApp blockquote *,
    [data-testid="stMarkdownContainer"] blockquote * {
        color: #0f172a !important;
    }

    /* 1. SELECTBOXES (DROPDOWNS) & INPUTS */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    div[data-baseweb="select"] *,
    div[data-baseweb="input"] *,
    div[data-baseweb="input"] input {
        color: #0f172a !important;
        fill: #0f172a !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1) !important;
    }
    ul[role="listbox"] li {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    ul[role="listbox"] li:hover, ul[role="listbox"] li[aria-selected="true"] {
        background-color: #e2e8f0 !important;
        color: #0284c7 !important;
    }

    /* 2. BOTÃO ATUALIZAR PÁGINA */
    div.stButton > button, [data-testid="stBaseButton-secondary"] {
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        font-weight: 500 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    div.stButton > button *, [data-testid="stBaseButton-secondary"] * {
        color: #0f172a !important;
    }
    div.stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover {
        background-color: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }

    /* 2.1 MODAL DIALOG (MODO CLARO) */
    div[role="dialog"],
    div[data-testid="stDialog"] > div {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        border-radius: 12px !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15) !important;
    }
    div[role="dialog"] h2,
    div[data-testid="stDialog"] h2 {
        color: #0f172a !important;
    }
    div[role="dialog"] button[aria-label="Close"],
    div[data-testid="stDialog"] button[aria-label="Close"] {
        color: #0f172a !important;
    }

    /* 3. EXPANDER (AJUSTE FINO) */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    [data-testid="stExpander"] summary:hover {
        background-color: #f8fafc !important;
    }
    [data-testid="stExpander"] summary * {
        color: #0f172a !important;
        fill: #0f172a !important;
    }
    [data-testid="stExpanderDetails"] {
        background-color: #ffffff !important;
    }

    /* 5. CHECKBOX & RADIO */
    [data-testid="stCheckbox"] label *,
    [data-testid="stRadio"] label * {
        color: #0f172a !important;
    }
    [data-testid="stCheckbox"] div[role="checkbox"] {
        background-color: #ffffff !important;
        border: 1px solid #94a3b8 !important;
    }
    [data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"] {
        background-color: #0284c7 !important;
    }

    /* 6. SLIDERS */
    [data-testid="stSlider"] * {
        color: #0f172a !important;
    }

    /* 7. CARDS DE MÉTRICA */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
        color: #0f172a !important;
    }
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] label,
    [data-testid="stMetricLabel"] span {
        color: #334155 !important;
    }
    /* Ícone de ajuda (?) legível e nítido no modo claro (sem preenchimento sólido) */
    .stApp .stTooltipIcon svg,
    .stApp .stTooltipHoverTarget svg,
    .stApp [data-testid="stTooltipIcon"] svg {
        color: #475569 !important;
        stroke: #475569 !important;
        fill: none !important;
        opacity: 0.85 !important;
        transition: color 0.15s ease, opacity 0.15s ease !important;
    }
    .stApp .stTooltipIcon svg *,
    .stApp .stTooltipHoverTarget svg *,
    .stApp [data-testid="stTooltipIcon"] svg * {
        stroke: #475569 !important;
        fill: none !important;
    }
    .stApp .stTooltipHoverTarget:hover svg,
    .stApp .stTooltipIcon:hover svg,
    .stApp [data-testid="stTooltipIcon"]:hover svg,
    .stApp [data-testid="stTooltipHoverTarget"]:hover svg * {
        color: #0284c7 !important;
        stroke: #0284c7 !important;
        opacity: 1 !important;
    }
    /* Conteúdo flutuante do tooltip no Modo Claro (Invertido Escuro de Alto Contraste) */
    [data-baseweb="tooltip"],
    div[data-baseweb="tooltip"],
    div[role="tooltip"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    [data-testid="stTooltipContent"],
    .stTooltipContent,
    [data-testid="stDataFrameTooltipContent"],
    .stDataFrameTooltipContent,
    [data-testid="stTooltipErrorContent"],
    .stTooltipErrorContent {
        background-color: #0f172a !important;
        background: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25), 0 2px 6px rgba(0, 0, 0, 0.1) !important;
        padding: 8px 12px !important;
        max-width: 360px !important;
        line-height: 1.5 !important;
        z-index: 1000000 !important;
    }
    [data-testid="stTooltipContent"] div,
    .stTooltipContent div,
    [data-testid="stDataFrameTooltipContent"] div,
    .stDataFrameTooltipContent div,
    [data-testid="stTooltipContent"] [data-testid="stMarkdownContainer"],
    .stTooltipContent [data-testid="stMarkdownContainer"],
    [data-testid="stDataFrameTooltipContent"] [data-testid="stMarkdownContainer"],
    .stDataFrameTooltipContent [data-testid="stMarkdownContainer"] {
        background: transparent !important;
        background-color: transparent !important;
    }
    [data-testid="stTooltipContent"] *,
    .stTooltipContent *,
    [data-testid="stDataFrameTooltipContent"] *,
    .stDataFrameTooltipContent *,
    [data-testid="stTooltipErrorContent"] *,
    .stTooltipErrorContent *,
    div[role="tooltip"] p,
    div[role="tooltip"] span {
        color: #f8fafc !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        line-height: 1.5 !important;
    }
    [data-testid="stTooltipContent"] strong,
    .stTooltipContent strong,
    [data-testid="stDataFrameTooltipContent"] strong,
    .stDataFrameTooltipContent strong {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    [data-testid="stTooltipContent"] code,
    .stTooltipContent code,
    [data-testid="stDataFrameTooltipContent"] code,
    .stDataFrameTooltipContent code {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border: 1px solid #334155 !important;
        border-radius: 4px !important;
        padding: 0.1em 0.35em !important;
    }

    /* 8. BOTÕES CIRCULARES DE TEMA E AJUDA (?) (MODO CLARO) */
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"],
    div.st-key-btn_theme_toggle button,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"],
    div.st-key-btn_help button {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        color: #0f172a !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_theme_toggle button:hover,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_help button:hover {
        background-color: #f1f5f9 !important;
        border-color: #94a3b8 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
        color: #0284c7 !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:focus,
    div.st-key-btn_theme_toggle button:focus,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"]:focus,
    div.st-key-btn_help button:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px #0284c7 !important;
    }

    /* 9. NAVEGAÇÃO PRINCIPAL NO MODO CLARO (SEGMENTED CONTROL / BUTTON GROUP) */
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"],
    .stApp [data-testid="stButtonGroup"],
    .stApp div.stButtonGroup {
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 3px !important;
    }
    .stApp .st-key-aba_ativa [role="radiogroup"],
    .stApp [data-testid="stButtonGroup"] [role="radiogroup"] {
        display: flex !important;
        gap: 4px !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    .stApp .st-key-aba_ativa div,
    .stApp [data-testid="stButtonGroup"] div {
        background-color: transparent !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button,
    .stApp .st-key-aba_ativa button[data-variant="segmented_control"],
    .stApp [data-testid="stButtonGroup"] button,
    .stApp button[data-variant="segmented_control"],
    .stApp button[data-variant="segmented_control"]:not([data-selected]) {
        background-color: transparent !important;
        background: transparent !important;
        color: #475569 !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        margin: 0 !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button *,
    .stApp .st-key-aba_ativa button[data-variant="segmented_control"] *,
    .stApp [data-testid="stButtonGroup"] button *,
    .stApp button[data-variant="segmented_control"] *,
    .stApp button[data-variant="segmented_control"]:not([data-selected]) * {
        color: #475569 !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button:not([data-selected]):hover,
    .stApp button[data-variant="segmented_control"]:not([data-selected]):hover {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button:not([data-selected]):hover *,
    .stApp button[data-variant="segmented_control"]:not([data-selected]):hover * {
        color: #0f172a !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[data-selected],
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-selected="true"],
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-checked="true"],
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-pressed="true"],
    .stApp button[data-variant="segmented_control"][data-selected],
    .stApp button[data-variant="segmented_control"][aria-selected="true"],
    .stApp button[data-variant="segmented_control"][aria-checked="true"],
    .stApp button[data-variant="segmented_control"][aria-pressed="true"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #0284c7 !important;
        font-weight: 600 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        position: relative !important;
        z-index: 2 !important;
    }
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[data-selected] *,
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-selected="true"] *,
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-checked="true"] *,
    .stApp .st-key-aba_ativa [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
    .stApp button[data-variant="segmented_control"][data-selected] *,
    .stApp button[data-variant="segmented_control"][aria-selected="true"] *,
    .stApp button[data-variant="segmented_control"][aria-checked="true"] *,
    .stApp button[data-variant="segmented_control"][aria-pressed="true"] * {
        color: #0284c7 !important;
        font-weight: 600 !important;
    }

    /* 10. TABELA (DATAFRAME) E DOWNLOAD */
    [data-testid="stDataFrame"] {
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    [data-testid="stDownloadButton"] button {
        background-color: #0284c7 !important;
        border: 1px solid #0284c7 !important;
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    [data-testid="stDownloadButton"] button * {
        color: #ffffff !important;
    }
    [data-testid="stDownloadButton"] button:hover {
        background-color: #0369a1 !important;
        color: #ffffff !important;
    }

    /* 11. BOTÕES << (RECOLHER) E >> (EXPANDIR) NO MODO CLARO */
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stSidebarCollapseButton"] button {
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
    }
    [data-testid="stExpandSidebarButton"] button svg,
    [data-testid="stSidebarCollapseButton"] button svg {
        fill: #0f172a !important;
        color: #0f172a !important;
    }
    [data-testid="stExpandSidebarButton"] button:hover,
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }
    [data-testid="stExpandSidebarButton"] button:hover svg,
    [data-testid="stSidebarCollapseButton"] button:hover svg {
        fill: #0f172a !important;
        color: #0f172a !important;
    }

    /* Centralização e Cores do Spinner no Modo Claro */
    [data-testid="stSpinner"],
    .stSpinner,
    .stCacheSpinner,
    div[data-testid="stSpinner"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        background-image: none !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.06) !important;
        color: #0f172a !important;
    }
    [data-testid="stSpinner"] *,
    .stSpinner *,
    .stCacheSpinner * {
        background: transparent !important;
        background-image: none !important;
        color: #0f172a !important;
    }
    [data-testid="stSpinnerIcon"],
    [data-testid="stSpinner"] [data-testid="stSpinnerIcon"],
    .stSpinner [data-testid="stSpinnerIcon"],
    .stCacheSpinner [data-testid="stSpinnerIcon"] {
        border-color: rgba(2, 132, 199, 0.25) !important;
        border-top-color: #0284c7 !important;
        border-width: 2.5px !important;
    }
    [data-testid="stSpinner"] svg,
    .stSpinner svg {
        stroke: #0284c7 !important;
        color: #0284c7 !important;
        fill: none !important;
    }

    /* Tabela / Grid Estruturado no Modo Claro */
    [data-testid="stMarkdownContainer"] table {
        width: 100% !important;
        border-collapse: collapse !important;
        margin: 1rem 0 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
    }
    [data-testid="stMarkdownContainer"] table thead tr {
        background-color: #f1f5f9 !important;
        border-bottom: 2px solid #cbd5e1 !important;
    }
    [data-testid="stMarkdownContainer"] table th {
        padding: 10px 14px !important;
        font-weight: 600 !important;
        color: #0f172a !important;
        text-align: left !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    [data-testid="stMarkdownContainer"] table th:nth-child(2) {
        text-align: center !important;
    }
    [data-testid="stMarkdownContainer"] table td {
        border-bottom: 1px solid #e2e8f0 !important;
        border-right: 1px solid #e2e8f0 !important;
        padding: 12px 14px !important;
        vertical-align: top !important;
        color: #1e293b !important;
        line-height: 1.6 !important;
    }
    [data-testid="stMarkdownContainer"] table td:last-child,
    [data-testid="stMarkdownContainer"] table th:last-child {
        border-right: none !important;
    }
    [data-testid="stMarkdownContainer"] table td:nth-child(2) {
        text-align: center !important;
        color: #64748b !important;
    }
    [data-testid="stMarkdownContainer"] table tbody tr:nth-child(even) {
        background-color: rgba(248, 250, 252, 0.7) !important;
    }
    [data-testid="stMarkdownContainer"] table tbody tr:hover {
        background-color: rgba(241, 245, 249, 0.9) !important;
    }

    /* 12. SKELETON SCREEN (MODO CLARO - YOUTUBE SHIMMER) */
    .skeleton-card,
    [data-testid="stMarkdownContainer"] .skeleton-card {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    .skeleton-line,
    [data-testid="stMarkdownContainer"] .skeleton-line {
        background-color: #e2e8f0 !important;
    }
    .skeleton-card::after,
    .skeleton-line::after,
    .skeleton-tab-pill::after {
        background: linear-gradient(
            105deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.45) 25%,
            rgba(255, 255, 255, 0.9) 50%,
            rgba(255, 255, 255, 0.45) 75%,
            rgba(255, 255, 255, 0) 100%
        ) !important;
    }
    """

css_global = """
    /* Mantém o header e toolbar transparentes com altura padrão e alinhada */
    header[data-testid="stHeader"],
    .stAppHeader {
        background: transparent !important;
        height: 2.75rem !important;
        z-index: 99 !important;
    }
    [data-testid="stToolbar"],
    .stAppToolbar {
        background: transparent !important;
        height: 2.75rem !important;
        display: flex !important;
        align-items: center !important;
    }
    /* Oculta estritamente o menu dos 3 pontinhos na direita */
    [data-testid="stToolbarActions"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }

    /* Botões Circulares Minimalistas no Topo Direito: Ajuda/Governança (?) e Alternância de Tema */
    div.st-key-btn_help {
        position: fixed !important;
        top: 0.35rem !important;
        right: 3.90rem !important;
        z-index: 1000 !important;
        width: auto !important;
        height: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div.st-key-btn_theme_toggle {
        position: fixed !important;
        top: 0.35rem !important;
        right: 1.25rem !important;
        z-index: 1000 !important;
        width: auto !important;
        height: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"],
    div.st-key-btn_theme_toggle button,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"],
    div.st-key-btn_help button {
        width: 2.25rem !important;
        height: 2.25rem !important;
        min-width: 2.25rem !important;
        min-height: 2.25rem !important;
        max-width: 2.25rem !important;
        max-height: 2.25rem !important;
        border-radius: 50% !important;
        padding: 0 !important;
        margin: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: transform 0.15s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_theme_toggle button:hover,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_help button:hover {
        transform: scale(1.08) !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:active,
    div.st-key-btn_theme_toggle button:active,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"]:active,
    div.st-key-btn_help button:active {
        transform: scale(0.94) !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"] *,
    div.st-key-btn_theme_toggle button *,
    div.st-key-btn_help [data-testid="stBaseButton-secondary"] *,
    div.st-key-btn_help button * {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    @media (max-width: 768px) {
        div.st-key-btn_help {
            top: 0.35rem !important;
            right: 3.35rem !important;
        }
        div.st-key-btn_theme_toggle {
            top: 0.35rem !important;
            right: 0.75rem !important;
        }
    }

    /* Botão >> (expandir) e Botão << (recolher) com geometria, alinhamento e dimensões idênticas */
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 100 !important;
    }
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stSidebarCollapseButton"] button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 2rem !important;
        width: 2rem !important;
        min-height: 2rem !important;
        min-width: 2rem !important;
        padding: 0 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stExpandSidebarButton"] button svg,
    [data-testid="stSidebarCollapseButton"] button svg {
        width: 1.25rem !important;
        height: 1.25rem !important;
    }

    /* Header da Sidebar: alinhado verticalmente na mesma linha exata do header principal */
    [data-testid="stSidebarHeader"] {
        height: 2.75rem !important;
        min-height: 2.75rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 0 0.85rem !important;
        margin: 0 !important;
    }
    [data-testid="stSidebarHeader"]::before {
        content: "RADAR ELEITORAL" !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        line-height: 1 !important;
        margin-left: 0.15rem !important;
    }

    /* Conteúdo principal: respiro superior suficiente para o título NÃO encavalar com o botão >> */
    .block-container {
        padding-top: 2.75rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }
    h1 {
        padding-top: 0.2rem !important;
        margin-top: 0rem !important;
        font-size: 2.0rem !important;
    }
    .stCaption {
        margin-top: -0.2rem !important;
        margin-bottom: 0.8rem !important;
    }

    /* Conteúdo interno da barra lateral */
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {
        padding-top: 0.2rem !important;
    }
    [data-testid="stSidebar"] h2 {
        margin-top: 0.2rem !important;
        padding-top: 0rem !important;
        margin-bottom: 0.45rem !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
    }

    /* Compactação vertical da barra lateral */
    [data-testid="stSidebar"] [data-testid="stElementContainer"] {
        margin-bottom: 0.35rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        margin-bottom: 0.12rem !important;
        min-height: auto !important;
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        font-size: 0.84rem !important;
        margin-bottom: 0 !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="input"] > div {
        min-height: 2.15rem !important;
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label span {
        font-size: 0.84rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.84rem !important;
        margin-top: 0.35rem !important;
        margin-bottom: 0.15rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        margin-top: 0.2rem !important;
        margin-bottom: 0.35rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        padding-top: 0.35rem !important;
        padding-bottom: 0.35rem !important;
    }

    /* Alinha o icone de ajuda (?) do checkbox a extrema direita, identico aos selectboxes */
    [data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stCheckbox"]),
    [data-testid="stSidebar"] .stElementContainer:has(.stCheckbox) {
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stCheckbox,
    [data-testid="stSidebar"] [data-testid="stCheckbox"],
    .stCheckbox,
    [data-testid="stCheckbox"] {
        width: 100% !important;
        align-self: stretch !important;
    }
    [data-testid="stSidebar"] [data-testid="stCheckbox"] > label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebar"] [data-testid="stCheckbox"] [data-testid="stWidgetLabel"],
    [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
    }
    [data-testid="stSidebar"] [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] > :last-child,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] [data-testid="stTooltipHoverTarget"],
    [data-testid="stSidebar"] [data-testid="stCheckbox"] [data-testid="stTooltipIcon"],
    [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] > :last-child,
    [data-testid="stCheckbox"] [data-testid="stTooltipHoverTarget"] {
        margin-left: auto !important;
    }

    /* Espaçamento coerente e legível para listas numeradas com sub-itens/parágrafos (ex: LGPD) */
    .stApp ol > li:has(> ul),
    .stApp ol > li:has(> p) {
        margin-bottom: 1.25rem !important;
    }
    .stApp ol > li > ul {
        margin-top: 0.35rem !important;
        margin-bottom: 0.6rem !important;
    }

    /* Equaliza a altura de todos os cards de métrica e alinha perfeitamente labels e valores */
    [data-testid="stMetric"] {
        min-height: 125px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        padding: 10px 14px !important;
        box-sizing: border-box !important;
    }
    [data-testid="stMetricLabel"] {
        display: flex !important;
        align-items: flex-start !important;
        justify-content: space-between !important;
        width: 100% !important;
        min-height: 2.5rem !important;
        margin-bottom: 0.15rem !important;
    }
    [data-testid="stMetricLabel"] > div {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }
    [data-testid="stMetricLabel"] [data-testid="stMarkdownContainer"] {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        white-space: normal !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
        margin-bottom: 0 !important;
    }
    [data-testid="stMetricLabel"] .stTooltipIcon,
    [data-testid="stMetricLabel"] [data-testid="stTooltipIcon"] {
        margin-left: 4px !important;
        margin-top: 1px !important;
        flex-shrink: 0 !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        line-height: 1.15 !important;
        letter-spacing: -0.02em !important;
        white-space: nowrap !important;
        overflow: visible !important;
    }
    [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {
        font-size: 0.92rem !important;
        font-weight: 600 !important;
    }

    /* ========================================================
       RESPONSIVIDADE DOS CARDS DE KPI (MÉTRICAS DO CABEÇALHO)
       ======================================================== */
    div.st-key-kpi_metrics [data-testid="stHorizontalBlock"],
    div.st-key-kpi_metrics .stHorizontalBlock {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 0.65rem !important;
        align-items: stretch !important;
    }

    div.st-key-kpi_metrics [data-testid="stColumn"],
    div.st-key-kpi_metrics .stColumn {
        display: flex !important;
        flex-direction: column !important;
    }

    div.st-key-kpi_metrics [data-testid="stColumn"] > div,
    div.st-key-kpi_metrics [data-testid="stColumn"] [data-testid="stElementContainer"],
    div.st-key-kpi_metrics [data-testid="stColumn"] [data-testid="stMetric"] {
        flex: 1 1 auto !important;
        height: 100% !important;
    }

    /* Padrão (Desktop): 5 colunas simétricas de largura rigorosamente idêntica */
    div.st-key-kpi_metrics [data-testid="stColumn"],
    div.st-key-kpi_metrics [data-testid="column"],
    div.st-key-kpi_metrics .stColumn {
        flex: 0 0 calc(20% - 0.55rem) !important;
        max-width: calc(20% - 0.55rem) !important;
        min-width: 0px !important;
        box-sizing: border-box !important;
    }

    /* Tablets e telas médias (entre 768px e 1150px): 3 colunas simétricas (sem esticar a última linha) */
    @media (max-width: 1150px) and (min-width: 768px) {
        div.st-key-kpi_metrics [data-testid="stColumn"],
        div.st-key-kpi_metrics [data-testid="column"],
        div.st-key-kpi_metrics .stColumn {
            flex: 0 0 calc(33.333% - 0.45rem) !important;
            max-width: calc(33.333% - 0.45rem) !important;
            min-width: 0px !important;
        }
    }

    /* Celulares e telas estreitas (entre 420px e 767px): grid simétrica de 2 colunas */
    @media (max-width: 767px) and (min-width: 420px) {
        div.st-key-kpi_metrics [data-testid="stColumn"],
        div.st-key-kpi_metrics [data-testid="column"],
        div.st-key-kpi_metrics .stColumn {
            flex: 0 0 calc(50% - 0.35rem) !important;
            max-width: calc(50% - 0.35rem) !important;
            min-width: 0px !important;
        }
        [data-testid="stMetric"] {
            min-height: 118px !important;
            padding: 8px 10px !important;
        }
        [data-testid="stMetricLabel"] {
            min-height: 2.2rem !important;
        }
        [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
            font-size: 1.30rem !important;
        }
        [data-testid="stMetricLabel"] p {
            font-size: 0.82rem !important;
            line-height: 1.15 !important;
        }
        [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {
            font-size: 0.80rem !important;
        }
    }

    /* Celulares muito estreitos (< 420px): 1 coluna por linha */
    @media (max-width: 419px) {
        div.st-key-kpi_metrics [data-testid="stColumn"],
        div.st-key-kpi_metrics [data-testid="column"],
        div.st-key-kpi_metrics .stColumn {
            flex: 0 0 100% !important;
            max-width: 100% !important;
            min-width: 100% !important;
        }
        [data-testid="stMetric"] {
            min-height: 118px !important;
            padding: 8px 10px !important;
        }
    }

    /* ========================================================
       RESPONSIVIDADE DOS GRÁFICOS (EM TELAS MENORES FICAM 1 POR LINHA)
       ======================================================== */
    div.st-key-graficos_container [data-testid="stHorizontalBlock"],
    div.st-key-graficos_container .stHorizontalBlock {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 1rem !important;
    }

    div.st-key-graficos_container [data-testid="stColumn"],
    div.st-key-graficos_container [data-testid="column"],
    div.st-key-graficos_container .stColumn {
        flex: 1 1 calc(50% - 0.5rem) !important;
        min-width: 320px !important;
    }

    @media (max-width: 850px) {
        div.st-key-graficos_container [data-testid="stColumn"],
        div.st-key-graficos_container [data-testid="column"],
        div.st-key-graficos_container .stColumn {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }

    /* Centralização Dinâmica do Spinner ("Processando, aguarde...") no centro geométrico da tela */
    [data-testid="stElementContainer"]:has([data-testid="stSpinner"]) {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        z-index: 999999 !important;
        width: auto !important;
        height: auto !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none !important;
    }
    [data-testid="stSpinner"],
    .stSpinner {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        z-index: 999999 !important;
        display: inline-flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        width: auto !important;
        max-width: 90vw !important;
        padding: 0.55rem 1.05rem !important;
        border-radius: 9999px !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        white-space: nowrap !important;
        animation: spinnerFadeInScale 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
        pointer-events: auto !important;
        box-sizing: border-box !important;
    }
    [data-testid="stSpinner"] > div,
    .stSpinner > div {
        display: inline-flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.55rem !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: nowrap !important;
    }
    [data-testid="stSpinner"] [data-testid="stMarkdownContainer"],
    .stSpinner [data-testid="stMarkdownContainer"],
    [data-testid="stSpinner"] div[role="status"],
    .stSpinner div[role="status"],
    [data-testid="stSpinner"] div.e1dfnxdh2,
    .stSpinner div.e1dfnxdh2 {
        display: inline-flex !important;
        align-items: center !important;
        white-space: nowrap !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stSpinnerIcon"],
    [data-testid="stSpinner"] span,
    .stSpinner span {
        flex-shrink: 0 !important;
        margin: 0 !important;
        vertical-align: middle !important;
    }
    [data-testid="stSpinner"] p,
    .stSpinner p {
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
        display: inline-block !important;
    }
    @keyframes spinnerFadeInScale {
        from {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.92);
        }
        to {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
    }

    /* Fórmulas Matemáticas (KaTeX): isolamento, respiro e responsividade sem encavalar */
    .stApp .katex-display {
        display: block !important;
        margin: 1.4rem auto !important;
        padding: 0.85rem 1.25rem !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        text-align: center !important;
        line-height: normal !important;
        background-color: rgba(125, 125, 125, 0.04) !important;
        border: 1px solid rgba(125, 125, 125, 0.15) !important;
        border-radius: 8px !important;
    }
    .stApp .katex {
        font-size: 1.12rem !important;
        line-height: normal !important;
    }

    /* ========================================================
       SKELETON SCREEN (ESTRUTURA, RESPONSIVIDADE E ANIMAÇÃO SHIMMER DO YOUTUBE)
       ======================================================== */
    @keyframes youtubeShimmer {
        0% {
            transform: translateX(-100%);
        }
        100% {
            transform: translateX(100%);
        }
    }
    @keyframes fadeInSkeleton {
        from {
            opacity: 0;
            transform: translateY(4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    [data-testid="stHtml"],
    div[data-testid="stHtml"] {
        width: 100% !important;
    }
    .skeleton-container {
        width: 100% !important;
        margin-top: 0.5rem !important;
        animation: fadeInSkeleton 0.25s ease-in-out !important;
    }
    .skeleton-card {
        border-radius: 8px !important;
        position: relative !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
    }
    .skeleton-line {
        border-radius: 4px !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .skeleton-tab-pill {
        border-radius: 6px !important;
        position: relative !important;
        overflow: hidden !important;
    }

    /* Onda de luz do YouTube (Shimmer Wave contínua via GPU transform: translateX) */
    .skeleton-card::after,
    .skeleton-line::after,
    .skeleton-tab-pill::after {
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        transform: translateX(-100%);
        animation: youtubeShimmer 1.5s infinite linear !important;
        pointer-events: none !important;
        z-index: 5 !important;
    }

    /* Grid de KPIs do Skeleton (5 colunas simétricas idênticas aos cards reais) */
    .skeleton-grid-kpi {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 0.65rem !important;
        width: 100% !important;
        margin-bottom: 1.25rem !important;
    }
    .skeleton-kpi {
        flex: 0 0 calc(20% - 0.55rem) !important;
        max-width: calc(20% - 0.55rem) !important;
        min-width: 0px !important;
        min-height: 125px !important;
        height: 125px !important;
        padding: 12px 14px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
    }
    @media (max-width: 1150px) and (min-width: 768px) {
        .skeleton-kpi {
            flex: 0 0 calc(33.333% - 0.45rem) !important;
            max-width: calc(33.333% - 0.45rem) !important;
        }
    }
    @media (max-width: 767px) and (min-width: 420px) {
        .skeleton-kpi {
            flex: 0 0 calc(50% - 0.35rem) !important;
            max-width: calc(50% - 0.35rem) !important;
            min-height: 118px !important;
            height: 118px !important;
            padding: 8px 10px !important;
        }
    }
    @media (max-width: 419px) {
        .skeleton-kpi {
            flex: 0 0 100% !important;
            max-width: 100% !important;
        }
    }

    /* Barra de Navegação do Skeleton (Segmented Control Placeholder) */
    .skeleton-nav-bar {
        width: 100% !important;
        height: 42px !important;
        padding: 4px 6px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        margin-bottom: 1.25rem !important;
    }
    .skeleton-tab-pill {
        height: 32px !important;
        border-radius: 6px !important;
    }

    /* Grid de Gráficos do Skeleton (2 colunas lado a lado idênticas) */
    .skeleton-grid-charts {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 1rem !important;
        width: 100% !important;
    }
    .skeleton-chart-box {
        flex: 1 1 calc(50% - 0.5rem) !important;
        min-width: 320px !important;
        height: 380px !important;
        padding: 18px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 12px !important;
    }
    @media (max-width: 850px) {
        .skeleton-chart-box {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }
"""

st.markdown(f"<style>\n{css_global}\n{css_tema}\n</style>", unsafe_allow_html=True)

# Botões circulares minimalistas no topo direito: Ajuda/Governança (?) e Alternância de Tema
if "exibir_governanca" not in st.session_state:
    st.session_state["exibir_governanca"] = False

# Sincronização canônica via URL caso acesse ?ferramenta=governanca
if st.query_params.get("ferramenta", "").lower() == "governanca":
    st.session_state["exibir_governanca"] = True

is_gov = st.session_state.get("exibir_governanca", False)
btn_help_label = "✕" if is_gov else "?"
btn_help_tooltip = "Fechar Governança e voltar à ferramenta" if is_gov else "Governança Pública, Termos da LGPD, Criptografia e Histórico de Versões"

if st.button(btn_help_label, key="btn_help", help=btn_help_tooltip):
    st.session_state["exibir_governanca"] = not is_gov
    if not st.session_state["exibir_governanca"] and "ferramenta" in st.query_params:
        del st.query_params["ferramenta"]
    elif st.session_state["exibir_governanca"]:
        st.query_params["ferramenta"] = "governanca"
    st.rerun()

if st.button("🌙" if not modo_escuro else "☀️", key="btn_theme_toggle", help="Alternar tema claro / escuro"):
    st.session_state["modo_escuro"] = not modo_escuro
    st.query_params["tema"] = "escuro" if st.session_state["modo_escuro"] else "claro"
    st.rerun()

def fmt_int_br(val) -> str:
    """Formata inteiros com separador de milhar brasileiro (ponto). Ex: 497.895"""
    try:
        return f"{int(val):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(val)

def fmt_float_br(val, decimals=1, force_sign=False) -> str:
    """Formata decimais com padrão brasileiro (milhar com ponto, decimal com vírgula). Ex: 1.234,5"""
    try:
        f_val = float(val)
        sign = "+" if (force_sign and f_val > 0) else ""
        parts = f"{f_val:,.{decimals}f}".split(".")
        int_part = parts[0].replace(",", ".")
        dec_part = parts[1] if len(parts) > 1 else ""
        res = f"{int_part},{dec_part}" if dec_part else int_part
        return f"{sign}{res}"
    except (ValueError, TypeError):
        return str(val)


@st.cache_data(show_spinner=False)
def carregar_dados() -> pd.DataFrame:
    return obter_dados_analiticos()


@st.cache_data(show_spinner=False)
def carregar_locais() -> pd.DataFrame:
    return obter_locais_votacao()


@st.cache_data(show_spinner=False)
def carregar_secoes_locais() -> pd.DataFrame:
    return obter_secoes_mapeadas()



def gerar_skeleton_html() -> str:
    """Gera a marcação HTML do esqueleto visual (Skeleton Screen) com efeito Shimmer."""
    return (
        '<div class="skeleton-container">'
        '<div class="skeleton-card skeleton-nav-bar">'
        '<div class="skeleton-line skeleton-tab-pill" style="flex: 1; height: 32px;"></div>'
        '<div class="skeleton-line skeleton-tab-pill" style="flex: 1; height: 32px;"></div>'
        '</div>'
        '<div class="skeleton-grid-kpi">'
        '<div class="skeleton-card skeleton-kpi">'
        '<div class="skeleton-line" style="width: 60%; height: 14px;"></div>'
        '<div class="skeleton-line" style="width: 45%; height: 32px; margin: 8px 0;"></div>'
        '<div class="skeleton-line" style="width: 75%; height: 12px;"></div>'
        '</div>'
        '<div class="skeleton-card skeleton-kpi">'
        '<div class="skeleton-line" style="width: 65%; height: 14px;"></div>'
        '<div class="skeleton-line" style="width: 50%; height: 32px; margin: 8px 0;"></div>'
        '<div class="skeleton-line" style="width: 70%; height: 12px;"></div>'
        '</div>'
        '<div class="skeleton-card skeleton-kpi">'
        '<div class="skeleton-line" style="width: 70%; height: 14px;"></div>'
        '<div class="skeleton-line" style="width: 40%; height: 32px; margin: 8px 0;"></div>'
        '<div class="skeleton-line" style="width: 65%; height: 12px;"></div>'
        '</div>'
        '<div class="skeleton-card skeleton-kpi">'
        '<div class="skeleton-line" style="width: 55%; height: 14px;"></div>'
        '<div class="skeleton-line" style="width: 48%; height: 32px; margin: 8px 0;"></div>'
        '<div class="skeleton-line" style="width: 80%; height: 12px;"></div>'
        '</div>'
        '<div class="skeleton-card skeleton-kpi">'
        '<div class="skeleton-line" style="width: 65%; height: 14px;"></div>'
        '<div class="skeleton-line" style="width: 35%; height: 32px; margin: 8px 0;"></div>'
        '<div class="skeleton-line" style="width: 60%; height: 12px;"></div>'
        '</div>'
        '</div>'
        '<div class="skeleton-grid-charts">'
        '<div class="skeleton-card skeleton-chart-box">'
        '<div class="skeleton-line" style="width: 42%; height: 18px;"></div>'
        '<div class="skeleton-line" style="width: 68%; height: 12px;"></div>'
        '<div class="skeleton-line" style="flex: 1; width: 100%; border-radius: 6px; margin-top: 6px;"></div>'
        '</div>'
        '<div class="skeleton-card skeleton-chart-box">'
        '<div class="skeleton-line" style="width: 38%; height: 18px;"></div>'
        '<div class="skeleton-line" style="width: 62%; height: 12px;"></div>'
        '<div class="skeleton-line" style="flex: 1; width: 100%; border-radius: 6px; margin-top: 6px;"></div>'
        '</div>'
        '</div>'
        '</div>'
    )


def gerar_skeleton_sidebar_html() -> str:
    """Gera a marcação HTML do esqueleto visual da barra lateral (Sidebar Ghost)."""
    return (
        '<div class="skeleton-container" style="padding-top: 0.2rem;">'
        '<div class="skeleton-card" style="width: 100%; height: 38px; border-radius: 6px; margin-bottom: 1.1rem; display: flex; align-items: center; padding: 0 10px;">'
        '<div class="skeleton-line" style="width: 55%; height: 16px;"></div>'
        '</div>'
        '<div class="skeleton-line" style="width: 35%; height: 18px; margin-bottom: 0.85rem; border-radius: 4px;"></div>'
        '<div style="display: flex; gap: 8px; margin-bottom: 0.75rem;">'
        '<div style="flex: 3;"><div class="skeleton-line" style="width: 60%; height: 12px; margin-bottom: 5px;"></div><div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div></div>'
        '<div style="flex: 2;"><div class="skeleton-line" style="width: 60%; height: 12px; margin-bottom: 5px;"></div><div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div></div>'
        '</div>'
        '<div style="margin-bottom: 0.75rem;">'
        '<div class="skeleton-line" style="width: 45%; height: 12px; margin-bottom: 5px;"></div>'
        '<div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div>'
        '</div>'
        '<div style="display: flex; gap: 8px; margin-bottom: 0.75rem;">'
        '<div style="flex: 1;"><div class="skeleton-line" style="width: 50%; height: 12px; margin-bottom: 5px;"></div><div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div></div>'
        '<div style="flex: 1;"><div class="skeleton-line" style="width: 50%; height: 12px; margin-bottom: 5px;"></div><div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div></div>'
        '</div>'
        '<div style="margin-bottom: 0.75rem;">'
        '<div class="skeleton-line" style="width: 50%; height: 12px; margin-bottom: 5px;"></div>'
        '<div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div>'
        '</div>'
        '<div style="margin-bottom: 0.75rem;">'
        '<div class="skeleton-line" style="width: 40%; height: 12px; margin-bottom: 5px;"></div>'
        '<div class="skeleton-card" style="height: 36px; border-radius: 6px;"></div>'
        '</div>'
        '<div style="display: flex; align-items: center; gap: 8px; margin-top: 0.9rem;">'
        '<div class="skeleton-card" style="width: 18px; height: 18px; min-width: 18px; border-radius: 4px;"></div>'
        '<div class="skeleton-line" style="width: 65%; height: 13px;"></div>'
        '</div>'
        '</div>'
    )


MAPA_FERRAMENTAS = {
    "🗳️ Auditoria de Urnas": {
        "titulo": "📡 Radar Eleitoral - Auditoria de Urnas",
        "caption": f"Plataforma Independente de Análise Estatística e Auditoria Eleitoral • Base Oficial TSE • **{VERSAO_DISPLAY}**",
    },
    "📉 Análise de Abstenção": {
        "titulo": "📡 Radar Eleitoral - Análise de Abstenção",
        "caption": f"Plataforma Independente de Análise Estatística e Comparecimento Eleitoral • Base Oficial TSE • **{VERSAO_DISPLAY}**",
    },
    "🗺️ Mapa de Fiscais & Seções": {
        "titulo": "📡 Radar Eleitoral - Mapa de Fiscais & Seções",
        "caption": f"Mapeamento Geoespacial de Prédios de Votação e Seções Prioritárias • Base Oficial TSE • **{VERSAO_DISPLAY}**",
    },
}


def obter_cabecalho_ferramenta(nome_ferramenta: str) -> dict:
    if nome_ferramenta in MAPA_FERRAMENTAS:
        return MAPA_FERRAMENTAS[nome_ferramenta]
    nome_limpo = nome_ferramenta
    for emoji in ["🗳️", "📉", "📊", "📡", "🔍", "🗺️"]:
        nome_limpo = nome_limpo.replace(emoji, "").strip()
    return {
        "titulo": f"📡 Radar Eleitoral - {nome_limpo}",
        "caption": f"Plataforma Independente de Ciência e Inteligência de Dados Eleitorais • Base Oficial TSE • **{VERSAO_DISPLAY}**",
    }


# Cabeçalho dinâmico sincronizado com a ferramenta ativa
placeholder_titulo = st.empty()
placeholder_caption = st.empty()

# Estimativa preliminar para Cold Start (preserva coerência visual antes de montar a barra lateral)
if st.session_state.get("exibir_governanca", False):
    placeholder_titulo.title("📡 Radar Eleitoral - Governança Pública & LGPD")
    placeholder_caption.caption(f"Diretrizes Institucionais, Conformidade Legal e Histórico de Versões • **{VERSAO_DISPLAY}**")
else:
    ferramenta_inicial = "🗳️ Auditoria de Urnas"
    qp_f = st.query_params.get("ferramenta", "").lower()
    if qp_f == "abstencao":
        ferramenta_inicial = "📉 Análise de Abstenção"
    elif qp_f == "mapa":
        ferramenta_inicial = "🗺️ Mapa de Fiscais & Seções"
    elif st.session_state.get("ferramenta_ativa") == "📉 Análise de Abstenção":
        ferramenta_inicial = "📉 Análise de Abstenção"
    elif st.session_state.get("ferramenta_ativa") == "🗺️ Mapa de Fiscais & Seções":
        ferramenta_inicial = "🗺️ Mapa de Fiscais & Seções"

    cabecalho_inicial = obter_cabecalho_ferramenta(ferramenta_inicial)
    placeholder_titulo.title(cabecalho_inicial["titulo"])
    placeholder_caption.caption(cabecalho_inicial["caption"])

# Exibe o Skeleton Screen visual (central + lateral) apenas no primeiro carregamento da sessão (Cold Start)
skeleton_placeholder = None
skeleton_sidebar_placeholder = None
is_cold_start = not st.session_state.get("primeira_carga_concluida", False)
if is_cold_start:
    skeleton_placeholder = st.empty()
    skeleton_placeholder.markdown(gerar_skeleton_html(), unsafe_allow_html=True)
    skeleton_sidebar_placeholder = st.sidebar.empty()
    skeleton_sidebar_placeholder.markdown(gerar_skeleton_sidebar_html(), unsafe_allow_html=True)

df = carregar_dados()

if skeleton_placeholder is not None:
    skeleton_placeholder.empty()
if skeleton_sidebar_placeholder is not None:
    skeleton_sidebar_placeholder.empty()

if df.empty:
    st.warning("⚠️ A base de dados analítica está temporariamente em sincronização.")
    st.info("Por favor, tente novamente em instantes ou selecione outro pleito.")
    st.stop()

# Garante coluna de região como categoria leve
if "regiao" not in df.columns:
    df["regiao"] = df["uf"].map(MAPA_REGIOES).fillna("Outra").astype("category")

# ==========================================
# SELETOR DE FERRAMENTA (SIDEBAR)
# ==========================================
st.sidebar.markdown(
    """
    <div style="display: flex; align-items: center; gap: 0.35rem; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 0.35rem;">
        <span style="font-size: 0.95em; line-height: 1;">📊</span>
        <span>Ferramenta</span>
    </div>
    """,
    unsafe_allow_html=True
)

opcoes_ferramenta = [
    "🗳️ Auditoria de Urnas",
    "📉 Análise de Abstenção",
    "🗺️ Mapa de Fiscais & Seções"
]

idx_ferramenta_inicial = 0
qp_f = st.query_params.get("ferramenta", "").lower()
if qp_f == "abstencao":
    idx_ferramenta_inicial = 1
elif qp_f == "mapa":
    idx_ferramenta_inicial = 2
elif st.session_state.get("ferramenta_ativa") in opcoes_ferramenta:
    idx_ferramenta_inicial = opcoes_ferramenta.index(st.session_state["ferramenta_ativa"])

def ao_mudar_ferramenta():
    st.session_state["exibir_governanca"] = False
    sel = st.session_state.get("ferramenta_ativa")
    if sel == "📉 Análise de Abstenção":
        st.query_params["ferramenta"] = "abstencao"
    elif sel == "🗺️ Mapa de Fiscais & Seções":
        st.query_params["ferramenta"] = "mapa"
    else:
        st.query_params["ferramenta"] = "auditoria"

ferramenta_ativa = st.sidebar.selectbox(
    "Ferramenta:",
    options=opcoes_ferramenta,
    index=idx_ferramenta_inicial,
    label_visibility="collapsed",
    key="ferramenta_ativa",
    on_change=ao_mudar_ferramenta,
    help="Selecione a ferramenta desejada."
)

# Sincroniza o cabeçalho dinâmico com a ferramenta ativa ou com o modo de governança
if st.session_state.get("exibir_governanca", False):
    placeholder_titulo.title("📡 Radar Eleitoral - Governança Pública & LGPD")
    placeholder_caption.caption(f"Diretrizes Institucionais, Conformidade Legal e Histórico de Versões • **{VERSAO_DISPLAY}**")
else:
    cabecalho_ativo = obter_cabecalho_ferramenta(ferramenta_ativa)
    placeholder_titulo.title(cabecalho_ativo["titulo"])
    placeholder_caption.caption(cabecalho_ativo["caption"])


# ==========================================
# SELETOR DE ELEIÇÃO & TURNO (SIDEBAR)
# ==========================================
if ferramenta_ativa != "🗺️ Mapa de Fiscais & Seções":
    st.sidebar.markdown(
        """
        <div style="display: flex; align-items: center; gap: 0.35rem; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-top: 0.65rem; margin-bottom: 0.35rem;">
            <span style="font-size: 0.95em; line-height: 1;">🗳️</span>
            <span>Eleição & Turno</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_ano, col_turno = st.sidebar.columns([1, 1])
    with col_ano:
        eleicao_ativa = st.selectbox(
            "Ano:",
            options=["2026"],
            index=0,
            label_visibility="collapsed",
            key="seletor_ano"
        )
    with col_turno:
        turno_ativo = st.selectbox(
            "Turno:",
            options=["1º Turno", "2º Turno"],
            index=0,
            label_visibility="collapsed",
            key="seletor_turno"
        )

    if turno_ativo == "2º Turno":
        if "turno" in df.columns and (df["turno"] == 2).any():
            df = df[df["turno"] == 2]
        else:
            st.info("🗳️ **2º Turno — Aguardando Apuração Oficial do TSE**\n\nOs dados de votação e boletins de urna do segundo turno serão integrados e disponibilizados para auditoria forense e análise estatística assim que os pacotes oficiais forem homologados e publicados pelo Tribunal Superior Eleitoral.")
            st.stop()
    else:
        if "turno" in df.columns:
            df = df[df["turno"] == 1]

plataforma = ferramenta_ativa
if st.session_state.get("exibir_governanca", False):
    renderizar_governanca(modo_escuro, plotly_theme)
elif ferramenta_ativa == "📉 Análise de Abstenção":
    renderizar_abstencao(df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)
elif ferramenta_ativa == "🗺️ Mapa de Fiscais & Seções":
    df_locais = carregar_locais()
    df_secoes_locais = carregar_secoes_locais()
    renderizar_mapa(df_locais, df_secoes_locais, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)
else:
    renderizar_auditoria(df, modo_escuro, plotly_theme, fmt_int_br, fmt_float_br)

st.session_state["primeira_carga_concluida"] = True
