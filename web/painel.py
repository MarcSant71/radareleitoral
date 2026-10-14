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

_source_dir = Path(__file__).resolve().parent
if str(_source_dir) not in sys.path:
    sys.path.insert(0, str(_source_dir))

from db import DB_PATH
from estatistica import aplicar_motor_estatistico

st.set_page_config(
    page_title="Auditoria Eleições 2026 - Análise de Votos por Horário",
    page_icon="🗳️",
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

    /* 1. SELECTBOXES (DROPDOWNS) */
    div[data-baseweb="select"] > div {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: #f0f2f6 !important;
    }
    div[data-baseweb="select"] * {
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

    /* 5. CHECKBOX */
    [data-testid="stCheckbox"] label * {
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

    /* 7. BOTÃO CIRCULAR DE TEMA (MODO ESCURO -> ÍCONE SOL) */
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"],
    div.st-key-btn_theme_toggle button {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
        color: #f0f2f6 !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_theme_toggle button:hover {
        background-color: #21262d !important;
        border-color: #58a6ff !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.6) !important;
        color: #58a6ff !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:focus,
    div.st-key-btn_theme_toggle button:focus {
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

    /* 1. SELECTBOXES (DROPDOWNS) */
    div[data-baseweb="select"] > div {
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    div[data-baseweb="select"] * {
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

    /* 5. CHECKBOX */
    [data-testid="stCheckbox"] label * {
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
    }
    .stApp .stTooltipIcon svg *,
    .stApp .stTooltipHoverTarget svg *,
    .stApp [data-testid="stTooltipIcon"] svg * {
        stroke: #475569 !important;
        fill: none !important;
    }
    /* Conteúdo flutuante do tooltip */
    [data-testid="stTooltipContent"],
    .stTooltipContent {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border-radius: 6px !important;
    }
    [data-testid="stTooltipContent"] *,
    .stTooltipContent * {
        color: #f8fafc !important;
    }

    /* 8. BOTÃO CIRCULAR DE TEMA (MODO CLARO -> ÍCONE LUA) */
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"],
    div.st-key-btn_theme_toggle button {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        color: #0f172a !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:hover,
    div.st-key-btn_theme_toggle button:hover {
        background-color: #f1f5f9 !important;
        border-color: #94a3b8 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
        color: #0284c7 !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:focus,
    div.st-key-btn_theme_toggle button:focus {
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

    /* Botão Circular Minimalista de Alternância de Tema (Estilo 12axes / Vercel / GitHub) */
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
    div.st-key-btn_theme_toggle button {
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
    div.st-key-btn_theme_toggle button:hover {
        transform: scale(1.08) !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"]:active,
    div.st-key-btn_theme_toggle button:active {
        transform: scale(0.94) !important;
    }
    div.st-key-btn_theme_toggle [data-testid="stBaseButton-secondary"] *,
    div.st-key-btn_theme_toggle button * {
        font-size: 1.15rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    @media (max-width: 768px) {
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
        justify-content: flex-end !important;
        padding: 0 0.75rem !important;
        margin: 0 !important;
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
        margin-bottom: 0.5rem !important;
        font-size: 1.4rem !important;
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
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        min-height: 2.15rem !important;
        padding-top: 2px !important;
        padding-bottom: 2px !important;
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
        padding: 0.85rem 1.65rem !important;
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
        gap: 0.75rem !important;
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
"""

st.markdown(f"<style>\n{css_global}\n{css_tema}\n</style>", unsafe_allow_html=True)

# Botão circular minimalista de alternância de tema no topo direito (estilo 12axes / Vercel / GitHub)
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

@st.cache_data(show_spinner="Processando, aguarde...")
def carregar_dados():
    if not DB_PATH.exists():
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        s.uf,
        s.municipio,
        coalesce(s.municipio_nome, m.nome, s.municipio) AS municipio_nome,
        coalesce(s.municipio_nome, m.nome, s.municipio) || ' (' || s.municipio || ')' AS municipio_display,
        s.zona,
        s.secao,
        a.total_votos_log,
        a.votos_antes_17h,
        a.votos_apos_17h,
        a.pct_apos_17h,
        a.primeiro_voto,
        a.ultimo_voto,
        ROUND(CAST(substr(a.ultimo_voto, 1, 2) AS REAL) + CAST(substr(a.ultimo_voto, 4, 2) AS REAL)/60.0 + CAST(substr(a.ultimo_voto, 7, 2) AS REAL)/3600.0, 2) AS hora_ult_dec,
        a.hora_encerramento,
        a.maior_ociosidade_antes_17h_min,
        a.minutos_sem_voto_antes_17h,
        a.biometria_sucesso_total,
        a.habilitacao_manual_total,
        a.biometria_sucesso_pos17h,
        a.habilitacao_manual_pos17h,
        a.pct_manual_pos17h,
        a.tempo_medio_pos17h_segundos,
        a.votos_ultrarapidos_pos17h,
        a.score_suspeicao,
        a.motivos_alerta,
        r.pres_total_validos,
        r.pres_venc_num,
        r.pres_venc_votos,
        r.pres_venc_pct,
        r.pres_seg_num,
        r.pres_seg_votos,
        r.pres_seg_pct,
        r.votos_cand_13,
        r.votos_cand_22,
        r.gov_venc_num,
        r.gov_venc_votos,
        r.gov_venc_pct,
        z.pct_13_zona,
        z.pct_22_zona,
        ROUND(r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END), 1) AS delta_venc_zona,
        ROUND((r.votos_cand_13 * 100.0 / NULLIF(r.pres_total_validos, 0)) - z.pct_13_zona, 1) AS delta_13_zona,
        ROUND((r.votos_cand_22 * 100.0 / NULLIF(r.pres_total_validos, 0)) - z.pct_22_zona, 1) AS delta_22_zona,
        CASE 
            WHEN r.pres_venc_num = 13 THEN 'Lula (13) (' || printf('%.1f', r.pres_venc_pct) || '%)'
            WHEN r.pres_venc_num = 22 THEN 'Flávio Bolsonaro (22) (' || printf('%.1f', r.pres_venc_pct) || '%)'
            WHEN r.pres_venc_num IS NOT NULL THEN 'Nº ' || r.pres_venc_num || ' (' || printf('%.1f', r.pres_venc_pct) || '%)'
            ELSE '-'
        END AS vencedor_display,
        CASE 
            WHEN (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END)) > 0 
                THEN '+' || printf('%.1f', (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END))) || ' pp'
            WHEN (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END)) IS NOT NULL 
                THEN printf('%.1f', (r.pres_venc_pct - (CASE WHEN r.pres_venc_num = 13 THEN z.pct_13_zona WHEN r.pres_venc_num = 22 THEN z.pct_22_zona ELSE 0 END))) || ' pp'
            ELSE '-'
        END AS delta_display
    FROM auditoria_horarios a
    JOIN secoes s ON s.id = a.secao_id
    LEFT JOIN municipios m ON m.codigo_tse = s.municipio
    LEFT JOIN resultados_eleicao r ON r.secao_id = s.id
    LEFT JOIN zonas_totais z ON z.uf = s.uf AND z.zona = s.zona
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Aplicação do Motor Estatístico Rigoroso (Spiegelhalter 2005)
    df = aplicar_motor_estatistico(df)

    # Otimização de consumo de memória RAM (downcasting de inteiros/floats e categorias)
    df["uf"] = df["uf"].astype("category")
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")

    import gc
    gc.collect()

    return df

st.title("🗳️ Auditoria Eleições 2026: Análise Estatística Forense")
st.caption("Sistema de Fiscalização Estatística e Detecção de Anomalias de Urna Eletrônica • Base Oficial TSE • **Versão 2.2.0**")

MAPA_REGIOES = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul"
}

df = carregar_dados()

if df.empty:
    st.warning("⚠️ O banco de dados local (eleicoes2026.db) ainda não possui dados auditados ou está vazio.")
    st.info("Execute o arquivo `atualizar_dados.cmd` para sincronizar os dados brutos e consolidar o banco.")
    st.stop()

# Adiciona coluna de região como categoria leve
df["regiao"] = df["uf"].map(MAPA_REGIOES).fillna("Outra").astype("category")

OPCOES_NAV = [
    "📊 Painel de Auditoria & Ranking Forense",
    "ℹ️ Sobre este Site (Metodologia e Aviso Legal)"
]

if "aba" in st.query_params:
    if st.query_params["aba"].lower() in ["sobre", "metodologia", "aviso"]:
        st.session_state["aba_ativa"] = OPCOES_NAV[1]
    else:
        st.session_state["aba_ativa"] = OPCOES_NAV[0]
elif "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = OPCOES_NAV[0]

def ir_para_resultados():
    st.session_state["aba_ativa"] = OPCOES_NAV[0]

# ==========================================
# FILTROS LATERAIS (SIDEBAR)
# ==========================================
st.sidebar.header("🔍 Filtros")

col_reg, col_uf = st.sidebar.columns([3, 2])
regioes_disponiveis = ["Todas", "Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]
regiao_selecionada = col_reg.selectbox("Região:", regioes_disponiveis, on_change=ir_para_resultados)

df_filtrado = df.copy()
if regiao_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["regiao"] == regiao_selecionada]

# Filtro Estado (UF) em cascata da região
ufs_disponiveis = ["Todas"] + sorted(df_filtrado["uf"].unique().tolist())
uf_selecionada = col_uf.selectbox("UF:", ufs_disponiveis, on_change=ir_para_resultados)
if uf_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["uf"] == uf_selecionada]

# Filtro Município com Nome Real
municipios_disponiveis = ["Todos"] + sorted(df_filtrado["municipio_display"].unique().tolist())
municipio_selecionado = st.sidebar.selectbox("Município:", municipios_disponiveis, on_change=ir_para_resultados)
if municipio_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["municipio_display"] == municipio_selecionado]

# Filtro Zona e Seção lado a lado
col_zona, col_secao = st.sidebar.columns(2)
zonas_disponiveis = ["Todas"] + sorted(df_filtrado["zona"].unique().tolist())
zona_selecionada = col_zona.selectbox("Zona:", zonas_disponiveis, on_change=ir_para_resultados)
if zona_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["zona"] == zona_selecionada]

secoes_disponiveis = ["Todas"] + sorted(df_filtrado["secao"].unique().tolist())
secao_selecionada = col_secao.selectbox("Seção:", secoes_disponiveis, on_change=ir_para_resultados)
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


# ==========================================
# NAVEGAÇÃO PRINCIPAL (CONTROLADA POR ESTADO)
# ==========================================
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
    st.markdown("<p style='margin-top: -1.1rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Versão 2.2.0</p>", unsafe_allow_html=True)

# ==========================================
# ABA: SOBRE ESTE SITE & METODOLOGIA FORENSE
# ==========================================
else:
    st.markdown(r"""
    ## 🏛️ Sobre este Site: Metodologia, Aviso Legal e Rigor Matemático

    > ⚖️ **Declaração de Neutralidade e Transparência:**  
    > Este site é um instrumento independente de transparência pública fundado no **Art. 5º, inciso XXXIII e Art. 37 da Constituição Federal do Brasil**, bem como na **Lei de Acesso à Informação (Lei nº 12.527/2011)** e nas resoluções de auditoria do **Tribunal Superior Eleitoral (TSE)**.  
    > **Nenhum dado exibido aqui foi adulterado, editado ou manipulado.** Não apoiamos candidatos ou partidos políticos. Todo o sistema se baseia exclusivamente em **ciência de dados, estatística descritiva e matemática determinística**.

    ---

    ### 📦 1. De Onde Vêm os Dados e Como Foram Obtidos?

    Todos os dados apresentados neste painel foram extraídos dos repositórios públicos oficiais do **Tribunal Superior Eleitoral (TSE)**:

    1. **Fonte Primária:** Repositório Oficial de Dados Abertos do TSE ([dadosabertos.tse.jus.br](https://dadosabertos.tse.jus.br/)) e Portal de Resultados e Boletins de Urna da Justiça Eleitoral.
    2. **Resoluções Aplicáveis:** Resolução TSE nº 23.673/2021, que regulamenta os procedimentos de fiscalização e auditoria do sistema eletrônico de votação.
    3. **Volume Auditado:** **497.895 seções eleitorais** auditadas em todas as 27 Unidades da Federação (100% dos pacotes oficiais disponibilizados).

    Para cada uma das seções, dois tipos de arquivos oficiais brutos gerados pela própria Urna Eletrônica foram lidos e processados:

    * **1. Arquivo de Log de Eventos (`logd.dat` / `*.logd`):**  
      Registro cronológico gravado pela urna em tempo real segundo a segundo. Cada eleitor que comparece gera registros operacionais no log: a inicialização dos sistemas, o teste de hardware, a chegada do eleitor à mesa receptora, a tentativa de leitura biométrica (ou dispensa manual com código pelo mesário), o tempo despendido na cabine e a emissão do comprovante.  
      *Nota Constitucional:* O log de eventos protege estritamente o sigilo constitucional do voto (Art. 14, caput, da CF/88). O log **não** registra e nem pode registrar em quem o eleitor votou; ele registra apenas o fluxo operacional e temporal da urna.
    
    * **2. Arquivo de Boletim de Urna (`bu.dat` / `*.bu`):**  
      Documento digital oficial gerado pela urna ao encerrar a votação, formatado na especificação internacional aberta **ASN.1 (Abstract Syntax Notation One - ISO/IEC 8824)**. O BU contém a totalização estática dos votos nominais por candidato, votos em branco, votos nulos, comparecimento e abstenção daquela seção específica.

    ---

    ### 🔐 2. Como Podemos Garantir que os Dados Não Foram Manipulados?

    A integridade de cada número exibido neste painel é garantida por três pilares tecnológicos irrefutáveis:

    1. **Assinatura Digital Criptográfica do TSE:**  
       Cada arquivo emitido pela urna eletrônica (`.bu` e `.logd`) contém um par de chaves e um resumo criptográfico (**Hash SHA-512**) assinado digitalmente com o certificado emitido pela Autoridade Certificadora da Justiça Eleitoral durante a Cerimônia Pública de Lacração dos Sistemas.  
       *Qualquer alteração* — de um único caractere, voto ou milissegundo — romperia a assinatura digital oficial, tornando o arquivo inválido.
    2. **Código Determinístico e Auditável:**  
       O processamento é feito por rotinas escritas em Python utilizando bibliotecas canônicas da indústria (`asn1crypto`, `sqlite3`, `pandas`). Não há inteligência artificial com alucinações, não há modelos obscuros, não há adivinhações. O sistema apenas processa eventos reais gravados na memória da urna:
    """)

    st.code("""
[Evento: Voto registrado às 18h32]          --> Incrementa contador de votos pós-17h
[Evento: Habilitação com código do mesário] --> Incrementa contador de dispensa biométrica manual
    """, language="text")

    st.markdown(r"""
    3. **Reprodutibilidade Científica 100% Pública:**  
       Qualquer perito forense, universidade pública, partido político ou cidadão comum pode baixar os pacotes brutos diretamente dos servidores do TSE e rodar os scripts de conferência. Os números consolidados na nossa base `eleicoes2026.db` baterão exatamente, voto por voto, evento por evento.

    ---

    ### 📐 3. Metodologia Estatística e Rigor Científico (Modelo de Spiegelhalter, 2005)

    A partir da **Versão 2.1.0**, este painel abandonou qualquer regra de pontuação arbitrária ou pesos aditivos empíricos. Todas as métricas de anomalia operam segundo o **Modelo de Efeitos Aleatórios e Controle Estatístico de Processos de David Spiegelhalter (2005)** — padrão acadêmico internacional utilizado em auditorias populacionais e epidemiológicas complexas.

    #### A. Taxa Esperada Contextual via Técnica *Leave-One-Out*
    Cada seção eleitoral é confrontada contra o comportamento esperado do seu **próprio município** (ou UF, quando o município possui menos de 5 seções).  
    Para evitar que uma seção atípica de grande porte contamine e distorça a própria média pela qual será julgada, adota-se a técnica matemática estrita de **Leave-One-Out**: a taxa esperada municipal exclui a própria seção da amostra:

    $$p_{\text{mun}} = \frac{\sum_{i \in \text{mun}} \text{Votos}_{i} - \text{Votos}_{\text{seção}}}{\sum_{i \in \text{mun}} \text{Total}_{i} - \text{Total}_{\text{seção}}}$$

    #### B. Z-Score Ajustado com Superdispersão Residual ($\tau^2$ Robusto via MAD)
    Em auditoria eleitoral, a variância binomial simples $p(1-p)/N$ tende a subestimar a variação natural legítima entre bairros, zonas rurais e capitais, gerando falsos positivos. O modelo de Spiegelhalter incorpora um termo de variância entre seções ($\tau^2$), estimado por Unidade da Federação de forma robusta via **MAD (Median Absolute Deviation)**:

    $$z_{\text{ajustado}} = \frac{\text{Taxa Observada} - p}{\sqrt{\frac{p(1-p)}{N} + \tau^2}}$$

    Onde $\tau^2 = \max\left(\left(1{,}4826 \cdot \text{MAD}(\text{Resíduos})\right)^2 - \text{Mediana}(\text{Variância Acaso}),\, 0\right)$.  
    Graças a essa modelagem, seções rurais pequenas não são penalizadas pelo acaso amostral e seções com desvio $|z| \ge 3{,}0\sigma$ representam eventos **genuinamente raros** ($< 0{,}13\%$ sob normalidade).

    #### C. Desvio Multivariado Composto (Norma Euclidiana L2)
    Para mensurar a gravidade confluente de uma seção que apresenta múltiplos desvios simultâneos (fechamento tardio pós-17h, dispensa biométrica manual atípica e extensão da hora do último voto), o sistema calcula a **Distância Euclidiana L2 dos Desvios Positivos**:

    $$Z_{\text{composto}} = \sqrt{\max(z_{\text{pós17}}, 0)^2 + \max(z_{\text{manual}}, 0)^2 + \max(z_{\text{horário}}, 0)^2}$$

    #### D. Régua Padronizada de Significância Estatística
    * **Padrão Normal ($Z < 2{,}0\sigma$):** Seção perfeitamente compreendida dentro do intervalo de confiança de 95% do seu município.
    * **🟡 Atenção ($2{,}0\sigma \le Z < 3{,}0\sigma$):** Desvio moderado em relação à linha de base local (percentil $\approx 97{,}7\%$).
    * **🟠 Atipicidade Alta ($3{,}0\sigma \le Z < 4{,}5\sigma$):** Desvio severo em relação ao comportamento padrão do município (percentil $\approx 99{,}87\%$).
    * **🔴 Atipicidade Extrema ($Z \ge 4{,}5\sigma$):** Confluência crítica de desvios simultâneos de horário, fluxo e habilitação.

    ---

    ### 🔍 4. Como Interpretar os Alertas?

    Um desvio estatístico padronizado ($Z \ge 3{,}0\sigma$) **não constitui prova de fraude**. Ele constitui uma **sinalização objetiva de atipicidade operacional e matemática**.  
    Explicações legítimas comuns incluem:
    * Fila física no encerramento decorrente de chuvas severas ou falta pontual de energia na região.
    * Urna eletrônica com leitor biométrico desgastado ou seção com concentração atípica de eleitores idosos (com perda de relevo papilar).
    * Comunidades de acesso complexo (seções em áreas ribeirinhas, indígenas ou rurais).

    **O passo forense correto:** Peritos, auditores e cidadãos devem confrontar o número da seção com a **Ata da Mesa Receptora** arquivada no Cartório Eleitoral e com o espelho do Boletim de Urna (BU) para checar as justificativas anotadas pelos mesários.

    ---

    ### 🛡️ 5. Privacidade, Proteção de Dados (LGPD) e Cookies de Navegação

    Este site segue com rigor as diretrizes da **Lei Geral de Proteção de Dados Pessoais (LGPD - Lei Federal nº 13.709/2018)** e as normas constitucionais de publicidade e transparência da administração pública:

    1. **Natureza dos Dados Eleitorais Exibidos:**  
       * Todos os dados de votação, seções, horários e urnas são **dados estritamente públicos de livre acesso**, obtidos no repositório oficial de dados abertos do TSE em cumprimento à **Lei de Acesso à Informação (Lei nº 12.527/2011)** e ao **Art. 7º, § 4º da LGPD**.
       * **Sigilo Constitucional do Voto:** Conforme preconizado no Art. 14, *caput*, da Constituição Federal de 1988, os registros operacionais das urnas (`.logd`) e os boletins de urna (`.bu`) **não contêm e não vinculam** a identidade do eleitor ao seu voto. Nenhum dado pessoal sensível individualizado é tratado, armazenado ou inferido por este sistema.

    2. **Métricas de Acesso e Telemetria (Google Analytics):**  
       * Para fins exclusivos de dimensionamento de capacidade dos servidores, controle de tráfego, garantia de estabilidade e análise agregada de audiência, este site utiliza ou poderá utilizar ferramentas de telemetria estatística, como o **Google Analytics**.
       * **Anonimização e Pseudonimização:** O Google Analytics coleta métricas técnicas e de audiência agregada (como volume de acessos simultâneos, páginas e filtros mais consultados, tipo de dispositivo, navegador e localização aproximada por cidade/região). A funcionalidade de **anonimização de endereço IP** é empregada, de forma que o IP completo do visitante não é armazenado em bases identificáveis.
       * **Finalidade e Não Compartilhamento:** Os dados de navegação **jamais serão vendidos, alugados, compartilhados com terceiros ou utilizados para fins publicitários, comerciais ou de direcionamento político-partidário**.

    3. **Uso de Cookies e Gestão pelo Usuário:**  
       * Cookies estritamente técnicos são utilizados pela aplicação para preservar o estado de navegação (como a escolha do tema Claro/Escuro e filtros em sessão). Cookies analíticos registram métricas agregadas de visitação.
       * **Direito de Recusa (Opt-Out):** O usuário pode, a qualquer tempo, bloquear, desativar ou apagar os cookies de rastreamento por meio das configurações de privacidade do seu navegador ou utilizando a extensão oficial [Google Analytics Opt-out Add-on](https://tools.google.com/dlpage/gaoptout). O bloqueio de cookies analíticos **não impede nem limita** o acesso completo a nenhuma das consultas ou ferramentas de auditoria disponíveis nesta página.

    4. **Canal de Transparência e Exercício de Direitos:**  
       * Em observância ao Art. 18 da LGPD, o titular de dados que desejar esclarecimentos adicionais sobre o tratamento de informações técnicas de navegação ou governança deste site pode entrar em contato diretamente pelo e-mail: [contato@dominiodigital.dev.br](mailto:contato@dominiodigital.dev.br).

    ---
    """)

    st.subheader("🏷️ 6. Histórico de Versões e Changelog Técnico")
    st.markdown("""
| Versão | Data | Principais Mudanças e Evolução Metodológica |
| :--- | :---: | :--- |
| **v2.2.0** | **14/10/2026** | **Experiência Analítica Dual & Calibração Visual:**<br>• Nova visualização de distribuição em modo duplo: *Faixas de Risco Forense* (visão intuitiva com contagens e percentuais por categoria) e *Histograma Contínuo* (visão técnica detalhada até 12σ) com seletor e ajuda contextual explicativa (?).<br>• *Viewport* dinâmico inteligente no gráfico de dispersão multivariada (calibrado no 99,5º percentil), eliminando a aglomeração causada por seções com horários extremos.<br>• Desacoplamento geométrico das anotações de significância (+2σ e +3σ), eliminando sobreposições de texto.<br>• Sincronização do manifesto de módulos dinâmicos e conformidade com diretrizes de governança e LGPD. |
| **v2.1.0** | **14/10/2026** | **Implementação do Motor Estatístico de Spiegelhalter (2005):**<br>• Substituição de regras heurísticas e pesos arbitrários por inferência estatística baseada em desvios padronizados (*z*-scores em sigmas σ).<br>• Adoção da técnica *Leave-One-Out* municipal para eliminação de viés e falsos alarmes.<br>• Estimativa robusta da superdispersão τ² intra-UF via MAD.<br>• Métricas multivariadas compostas (Norma Euclidiana L2) e novos diagnósticos objetivos de alerta.<br>• Identificação formal de versionamento em toda a plataforma. |
| **v2.0.0** | **13/10/2026** | **Auditoria Nacional Consolidada (27 UFs):**<br>• Processamento paralelo e decodificação ASN.1 dos 497.895 BUs e logs de eventos do TSE em escala nacional.<br>• Arquitetura SQLite WAL de alta performance com baixo consumo de memória RAM.<br>• Suporte nativo a Tema Claro/Escuro instantâneo e layout responsivo. |
| **v1.0.0** | **11/10/2026** | Protótipo inicial de extração de dados abertos do TSE e ranking exploratório. |
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='margin-top: -1.1rem; font-size: 0.82rem; font-style: italic; opacity: 0.75;'>Desenvolvido com ❤️ por Dominio Digital © 2026 • Versão 2.2.0</p>", unsafe_allow_html=True)

