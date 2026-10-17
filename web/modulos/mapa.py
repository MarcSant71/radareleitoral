"""
Módulo de Mapa Interativo de Locais de Votação e Seções Prioritárias.
Visualização geoespacial com Leaflet + MarkerCluster, busca por endereço/escola e lista com exportação CSV.
"""

import json
import numpy as np
import pandas as pd
import streamlit as st
from dados.carregador import MAPA_REGIOES


OPCOES_MODO_MAPA = [
    "🗺️ Mapa Interativo",
    "📋 Lista de Locais & Seções",
    "📖 Metodologia & Critérios"
]

NIVEIS_ROTULO = {
    "alta": "🔴 Alta Prioridade",
    "media": "🟠 Média Prioridade",
    "baixa": "🟡 Baixa Prioridade",
    "logs": "🔵 Alerta de Log"
}


def renderizar_metodologia_mapa():
    """Renderiza a documentação institucional e critérios do mapa."""
    st.markdown("""
    ### 📖 Metodologia & Critérios de Mapeamento Georreferenciado

    > 🏛️ **Declaração de Finalidade Institucional:**  
    > A presença de um prédio ou seção neste mapa **não constitui acusação de fraude ou irregularidade**.  
    > Este mapa é uma ferramenta de **otimização de logística cívica e alocação de fiscais independentes**, priorizando locais que apresentaram comportamentos estatísticos incomuns ou ocorrências operacionais documentadas nas urnas.

    ---

    #### 🎯 1. Como os Prédios São Sinalizados?

    Os pontos no mapa resultam da convergência de duas grandes fontes primárias oficiais do TSE:

    1. **Critérios Históricos do Boletim de Urna (BU):**  
       Modelos que identificam votações unânimes anômalas, divergências superiores a 3 sigmas ($\sigma$) em relação às seções vizinhas da mesma zona, comparecimento atípico e seções com encerramento tardio após as 17h.
    2. **Sinais Operacionais dos Logs das Urnas (`logd`):**  
       Registros segundo a segundo gravados pela máquina: desvios na taxa de identificação biométrica (liberação manual em lote por mesário), tempos de votação extremos, quedas de energia com uso de bateria interna e conferências de integridade do arquivo.

    ---

    #### 🚦 2. Classificação de Prioridade

    * **🔴 Prioridade Alta:** Seções com pontuação cumulativa máxima em múltiplos critérios históricos e discrepâncias acentuadas contra a média da zona eleitoral.
    * **🟠 Prioridade Média:** Seções com anomalias estatísticas moderadas ou histórico de substituição de urna e encerramento tardio.
    * **🟡 Baixa Prioridade:** Seções com sinalizações leves (ex: local isolado com 3 ou mais seções atípicas).
    * **🔵 Alertas de Log:** Seções cuja apuração foi normal no boletim, mas cujo arquivo de log indicou ocorrências operacionais relevantes (ex: alta dispensa biométrica sem justificativa registrada).

    ---

    #### 🛡️ 3. O Que o Fiscal Deve Fazer na Seção?

    O papel soberano do fiscal de votação consiste em:
    1. **Chegar Cedo:** Acompanhar a emissão da **Zerésima** antes das 08h00 para atestar que a máquina iniciou zerada.
    2. **Observar o Fluxo:** Garantir que o mesário realize as 4 tentativas biométricas obrigatórias antes de liberar o voto manualmente com o código de contingência.
    3. **Conferir o Encerramento:** Às 17h00, fotografar o **Boletim de Urna (BU)** impresso colado na porta da seção e confrontar imediatamente os totais com os dados publicados no portal do TSE.
    """)


def renderizar_mapa(
    df_locais: pd.DataFrame,
    df_secoes: pd.DataFrame,
    modo_escuro: bool = True,
    plotly_theme: str = "plotly_dark",
    fmt_int_br=lambda x: str(x),
    fmt_float_br=lambda x: str(x)
):
    """
    Renderiza o módulo completo do Mapa de Fiscais e Seções Prioritárias.
    """
    if df_locais.empty:
        st.warning("⚠️ O catálogo de locais de votação ainda não foi carregado. Execute `python pipeline/ingestao_locais.py` para sincronizar os dados.")
        st.stop()

    # ==========================================
    # SELETOR DE MODO SUPERIOR (SEGMENTED CONTROL)
    # ==========================================
    if "aba_mapa" in st.query_params:
        qp_m = st.query_params["aba_mapa"].lower()
        if qp_m in ["lista", "tabela", "secoes"]:
            st.session_state["aba_ativa_mapa"] = OPCOES_MODO_MAPA[1]
        elif qp_m in ["sobre", "metodologia", "criterios"]:
            st.session_state["aba_ativa_mapa"] = OPCOES_MODO_MAPA[2]
        else:
            st.session_state["aba_ativa_mapa"] = OPCOES_MODO_MAPA[0]
    elif "aba_ativa_mapa" not in st.session_state:
        st.session_state["aba_ativa_mapa"] = OPCOES_MODO_MAPA[0]

    modo_ativo = st.segmented_control(
        "Navegação do Mapa",
        options=OPCOES_MODO_MAPA,
        key="aba_ativa_mapa",
        selection_mode="single",
        required=True,
        label_visibility="collapsed",
        width="stretch"
    )
    if not modo_ativo:
        modo_ativo = OPCOES_MODO_MAPA[0]

    # Se estiver na Metodologia, renderiza imediatamente sem poluir a barra lateral nem montar filtros
    if modo_ativo == OPCOES_MODO_MAPA[2]:
        renderizar_metodologia_mapa()
        return

    # ==========================================
    # FILTROS LATERAIS (SIDEBAR)
    # ==========================================
    st.sidebar.markdown(
        """
        <div style="display: flex; align-items: center; gap: 0.35rem; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-top: 0.65rem; margin-bottom: 0.35rem;">
            <span style="font-size: 0.95em; line-height: 1;">🔍</span>
            <span>Filtros do Mapa</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Filtro de Estado (UF)
    ufs_disponiveis = ["Todas (Brasil)"] + sorted([u for u in df_locais["uf"].dropna().unique() if u != "ZZ"])
    if "ZZ" in df_locais["uf"].values:
        ufs_disponiveis.append("ZZ (Exterior)")

    uf_salva = st.session_state.get("mapa_uf_salva", "Todas (Brasil)")
    uf_idx = ufs_disponiveis.index(uf_salva) if uf_salva in ufs_disponiveis else 0
    uf_selecionada = st.sidebar.selectbox("Estado (UF):", ufs_disponiveis, index=uf_idx, key="mapa_uf")
    st.session_state["mapa_uf_salva"] = uf_selecionada

    # Recorte por UF
    df_l = df_locais.copy()
    if uf_selecionada != "Todas (Brasil)":
        uf_pura = uf_selecionada.split(" ")[0]
        df_l = df_l[df_l["uf"] == uf_pura]

    # 2. Filtro de Município
    municipios_disponiveis = ["Todos os Municípios"]
    if not df_l.empty:
        municipios_disponiveis += sorted(df_l["municipio"].dropna().unique().tolist())

    mun_salvo = st.session_state.get("mapa_mun_salvo", "Todos os Municípios")
    mun_idx = municipios_disponiveis.index(mun_salvo) if mun_salvo in municipios_disponiveis else 0
    mun_selecionado = st.sidebar.selectbox("Município:", municipios_disponiveis, index=mun_idx, key="mapa_mun")
    st.session_state["mapa_mun_salvo"] = mun_selecionado

    if mun_selecionado != "Todos os Municípios":
        df_l = df_l[df_l["municipio"] == mun_selecionado]

    # 3. Filtro de Zona Eleitoral
    zonas_disponiveis = ["Todas as Zonas"]
    if not df_l.empty:
        zonas_disponiveis += sorted([str(int(z)) for z in df_l["zona"].dropna().unique()])

    zona_salva = st.session_state.get("mapa_zona_salva", "Todas as Zonas")
    zona_idx = zonas_disponiveis.index(zona_salva) if zona_salva in zonas_disponiveis else 0
    zona_selecionada = st.sidebar.selectbox("Zona Eleitoral:", zonas_disponiveis, index=zona_idx, key="mapa_zona")
    st.session_state["mapa_zona_salva"] = zona_selecionada

    if zona_selecionada != "Todas as Zonas":
        df_l = df_l[df_l["zona"] == int(zona_selecionada)]

    # 4. Filtro de Prioridade / Risco
    opcoes_risco = ["Todas as Prioridades", "Prioridade Alta", "Prioridade Média", "Prioridade Baixa"]
    risco_sel = st.sidebar.selectbox("Nível de Prioridade:", opcoes_risco, index=0, key="mapa_risco")

    if risco_sel == "Prioridade Alta":
        df_l = df_l[df_l["risco"] == "alto"]
    elif risco_sel == "Prioridade Média":
        df_l = df_l[df_l["risco"] == "medio"]
    elif risco_sel == "Prioridade Baixa":
        df_l = df_l[df_l["risco"] == "baixo"]

    # 5. Busca Textual por Escola ou Endereço
    busca_texto = st.sidebar.text_input(
        "Buscar Colégio, Rua ou Bairro:",
        value=st.session_state.get("mapa_busca_txt", ""),
        placeholder="Ex: CIEP, Escola Municipal, Centro...",
        key="mapa_busca_input"
    ).strip()
    st.session_state["mapa_busca_txt"] = busca_texto

    if busca_texto:
        termo = busca_texto.upper()
        mascara = (
            df_l["local"].fillna("").str.upper().str.contains(termo, regex=False) |
            df_l["endereco"].fillna("").str.upper().str.contains(termo, regex=False) |
            df_l["bairro"].fillna("").str.upper().str.contains(termo, regex=False) |
            df_l["cep"].fillna("").str.contains(termo, regex=False)
        )
        df_l = df_l[mascara]

    # Relaciona com seções mapeadas filtradas
    ids_locais_filtrados = set(df_l["id"].dropna().unique())
    df_s = df_secoes[df_secoes["local_id"].isin(ids_locais_filtrados)] if not df_secoes.empty else pd.DataFrame()

    # ==========================================
    # CARDS KPIS NO TOPO
    # ==========================================
    total_locais = len(df_l)
    total_secoes_mapeadas = len(df_s)
    total_aptos = int(df_l["aptos_total"].sum()) if not df_l.empty else 0
    secoes_alta_media = int(df_s["nivel"].isin(["alta", "media"]).sum()) if not df_s.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏫 Prédios de Votação", fmt_int_br(total_locais), help="Total de escolas e locais de votação com seções sinalizadas no recorte.")
    c2.metric("🗳️ Seções Sinalizadas", fmt_int_br(total_secoes_mapeadas), help="Seções eleitorais que demandam fiscal atento com base nos critérios oficiais.")
    c3.metric("🚨 Prioridade Alta / Média", fmt_int_br(secoes_alta_media), help="Seções nos níveis críticos de atipicidade ou discrepância estatística.")
    c4.metric("👥 Eleitores Abrangidos", fmt_int_br(total_aptos), help="Soma total do eleitorado apto alocado nestes prédios.")

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # RENDERIZAÇÃO: MODO 1 (MAPA) OU MODO 2 (LISTA)
    # ----------------------------------------------------
    if modo_ativo == "🗺️ Mapa Interativo":
        df_geo = df_l[df_l["lat"].notna() & df_l["lon"].notna()].copy()

        if df_geo.empty:
            st.info("ℹ️ Nenhum local com coordenadas válidas encontrado para os filtros selecionados.")
            return

        # Amostragem defensiva para visão nacional (evita estourar memória do navegador)
        aviso_amostragem = False
        limite_pontos = 6000
        total_pontos_validos = len(df_geo)
        if total_pontos_validos > limite_pontos:
            # Prioriza colégios de alto risco primeiro
            ordem_risco = {"alto": 0, "medio": 1, "baixo": 2}
            df_geo["_ordem"] = df_geo["risco"].astype(str).map(ordem_risco).fillna(3).astype(int)
            df_geo = df_geo.sort_values("_ordem").head(limite_pontos)
            aviso_amostragem = True

        if aviso_amostragem:
            st.warning(
                f"⚡ **Visualização Nacional Otimizada:** Exibindo os {limite_pontos:,} prédios mais prioritários de um total de {total_pontos_validos:,} no país. "
                "Para visualizar 100% dos locais de um município ou bairro, selecione o **Estado (UF)** no menu lateral."
            )

        # Cálculo do centro e zoom ideal do mapa
        lat_centro = float(df_geo["lat"].median())
        lon_centro = float(df_geo["lon"].median())

        if mun_selecionado != "Todos os Municípios":
            zoom_inicial = 13
        elif uf_selecionada != "Todas (Brasil)":
            zoom_inicial = 7
        else:
            lat_centro = -14.2350
            lon_centro = -51.9253
            zoom_inicial = 4

        # Prepara registros leves para injeção no JavaScript
        colunas_export = ["id", "local", "endereco", "bairro", "cep", "municipio", "uf", "zona", "lat", "lon", "risco", "secoes_total"]
        if "aptos_total" in df_geo.columns:
            colunas_export.append("aptos_total")

        registros_pontos = []
        for row in df_geo[colunas_export].itertuples(index=False):
            registros_pontos.append({
                "id": str(row.id),
                "nome": str(row.local or "Local de Votação"),
                "end": f"{row.endereco or ''} - {row.bairro or ''}".strip(" -"),
                "cep": str(row.cep or ""),
                "mun": f"{row.municipio} - {row.uf}",
                "zona": int(row.zona) if pd.notna(row.zona) else 0,
                "lat": round(float(row.lat), 5),
                "lon": round(float(row.lon), 5),
                "risco": str(row.risco or "baixo").lower(),
                "secoes": int(row.secoes_total) if pd.notna(row.secoes_total) else 1,
                "aptos": int(getattr(row, "aptos_total", 0)) if pd.notna(getattr(row, "aptos_total", 0)) else 0
            })

        dados_json = json.dumps(registros_pontos, ensure_ascii=False)

        # Mapeia seções por local_id para injeção ultrarrápida na gaveta lateral
        secoes_por_local = {}
        if not df_s.empty:
            ids_geo = set(df_geo["id"].dropna().unique())
            colunas_secoes = ["local_id", "secao", "nivel", "criterios", "explicacao", "aptos", "comparecimento", "flavio_pct", "lula_pct", "logs"]
            cols_disp = [c for c in colunas_secoes if c in df_s.columns]
            df_s_geo = df_s[df_s["local_id"].isin(ids_geo)][cols_disp]

            for sec in df_s_geo.itertuples(index=False):
                loc_id = str(sec.local_id)
                secao_num = int(sec.secao) if hasattr(sec, "secao") and pd.notna(sec.secao) else 0
                nivel_str = str(getattr(sec, "nivel", "baixa") or "baixa").lower()
                criterios_str = str(getattr(sec, "criterios", "") or "—")
                explicacao_str = str(getattr(sec, "explicacao", "") or "")
                aptos_val = int(sec.aptos) if hasattr(sec, "aptos") and pd.notna(sec.aptos) else 0
                comp_val = int(sec.comparecimento) if hasattr(sec, "comparecimento") and pd.notna(sec.comparecimento) else 0
                flavio_v = getattr(sec, "flavio_pct", None)
                lula_v = getattr(sec, "lula_pct", None)
                flavio_str = f"{round(float(flavio_v), 1)}%" if pd.notna(flavio_v) else "—"
                lula_str = f"{round(float(lula_v), 1)}%" if pd.notna(lula_v) else "—"
                logs_str = str(getattr(sec, "logs", "") or "").strip()

                pct_comp = round((comp_val / aptos_val * 100), 1) if aptos_val > 0 else 0

                secoes_por_local.setdefault(loc_id, []).append({
                    "secao": secao_num,
                    "nivel": nivel_str,
                    "criterios": criterios_str,
                    "explicacao": explicacao_str,
                    "aptos": aptos_val,
                    "comp": comp_val,
                    "pct_comp": pct_comp,
                    "flavio": flavio_str,
                    "lula": lula_str,
                    "logs": logs_str
                })

        secoes_json = json.dumps(secoes_por_local, ensure_ascii=False)

        # Configura tema visual Dark / Light
        if modo_escuro:
            bg_color = "#0e1117"
            text_color = "#f0f2f6"
            card_bg = "#161b22"
            card_bg_alt = "#0d1117"
            card_border = "#30363d"
            text_muted = "#8b949e"
            accent_color = "#58a6ff"
        else:
            bg_color = "#ffffff"
            text_color = "#0f172a"
            card_bg = "#ffffff"
            card_bg_alt = "#f8fafc"
            card_border = "#e2e8f0"
            text_muted = "#64748b"
            accent_color = "#2563eb"

        # HTML autônomo com Leaflet 1.9.4, MarkerCluster 1.5.3 e Gaveta Lateral Flutuante
        html_mapa = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.css" />
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.css" />
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                    background-color: {bg_color};
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                }}
                #map-container {{
                    position: relative;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                }}
                #map {{
                    width: 100%;
                    height: 100%;
                    min-height: 650px;
                    border-radius: 8px;
                    border: 1px solid {card_border};
                }}

                /* Custom MarkerCluster Styles */
                .marker-cluster-small {{ background-color: rgba(234, 179, 8, 0.6) !important; }}
                .marker-cluster-small div {{ background-color: rgba(234, 179, 8, 0.9) !important; color: #000 !important; font-weight: 700 !important; }}
                .marker-cluster-medium {{ background-color: rgba(249, 115, 22, 0.6) !important; }}
                .marker-cluster-medium div {{ background-color: rgba(249, 115, 22, 0.9) !important; color: #fff !important; font-weight: 700 !important; }}
                .marker-cluster-large {{ background-color: rgba(239, 68, 68, 0.6) !important; }}
                .marker-cluster-large div {{ background-color: rgba(239, 68, 68, 0.9) !important; color: #fff !important; font-weight: 700 !important; }}

                /* Seletor de Camadas (BaseMaps) */
                .leaflet-control-layers {{
                    background: {card_bg} !important;
                    color: {text_color} !important;
                    border: 1px solid {card_border} !important;
                    border-radius: 6px !important;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
                    font-size: 0.80rem !important;
                    padding: 6px 10px !important;
                }}
                .leaflet-control-layers label {{
                    color: {text_color} !important;
                    margin-bottom: 3px !important;
                    cursor: pointer !important;
                }}

                /* ===================================================
                   GAVETA LATERAL FLUTUANTE (SIDE DRAWER IN-MAP)
                   =================================================== */
                .drawer {{
                    position: absolute;
                    top: 0;
                    right: 0;
                    bottom: 0;
                    width: 420px;
                    max-width: 90vw;
                    background: {card_bg};
                    color: {text_color};
                    border-left: 1px solid {card_border};
                    z-index: 2000;
                    display: flex;
                    flex-direction: column;
                    box-shadow: -8px 0 30px rgba(0, 0, 0, 0.45);
                    transform: translateX(100%);
                    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
                    pointer-events: none;
                    visibility: hidden;
                }}
                .drawer.open {{
                    transform: translateX(0);
                    pointer-events: auto;
                    visibility: visible;
                }}

                .drawer-header {{
                    padding: 14px 16px;
                    background: {card_bg_alt};
                    border-bottom: 1px solid {card_border};
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 12px;
                    flex-shrink: 0;
                }}
                .drawer-title {{
                    margin: 6px 0 0 0;
                    font-size: 1.05rem;
                    font-weight: 700;
                    line-height: 1.3;
                    color: {accent_color};
                    word-break: break-word;
                }}
                .drawer-close-btn {{
                    background: transparent;
                    border: 1px solid {card_border};
                    border-radius: 6px;
                    color: {text_color};
                    font-size: 1.3rem;
                    line-height: 1;
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    flex-shrink: 0;
                    transition: all 0.15s ease;
                }}
                .drawer-close-btn:hover {{
                    background: rgba(239, 68, 68, 0.15);
                    color: #ef4444;
                    border-color: #ef4444;
                }}

                .drawer-content {{
                    flex: 1;
                    overflow-y: auto;
                    padding: 14px 16px;
                }}
                .drawer-content::-webkit-scrollbar {{
                    width: 6px;
                }}
                .drawer-content::-webkit-scrollbar-track {{
                    background: transparent;
                }}
                .drawer-content::-webkit-scrollbar-thumb {{
                    background: {card_border};
                    border-radius: 3px;
                }}
                .drawer-content::-webkit-scrollbar-thumb:hover {{
                    background: {text_muted};
                }}

                .drawer-card-meta {{
                    background: {card_bg_alt};
                    border: 1px solid {card_border};
                    border-radius: 6px;
                    padding: 12px;
                    font-size: 0.82rem;
                    line-height: 1.45;
                    margin-bottom: 14px;
                }}
                .meta-item {{
                    margin-bottom: 5px;
                }}
                .meta-row {{
                    display: flex;
                    justify-content: space-between;
                    gap: 8px;
                    margin-bottom: 5px;
                    font-size: 0.78rem;
                }}
                .btn-maps {{
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 6px 12px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: {accent_color};
                    background: rgba(56, 189, 248, 0.1);
                    border: 1px solid rgba(56, 189, 248, 0.3);
                    border-radius: 4px;
                    text-decoration: none;
                    transition: background 0.15s;
                    margin-top: 6px;
                }}
                .btn-maps:hover {{
                    background: rgba(56, 189, 248, 0.2);
                }}

                .drawer-secoes-header {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    font-size: 0.86rem;
                    font-weight: 700;
                    margin-bottom: 10px;
                    color: {text_color};
                }}
                .badge-qtd {{
                    background: {card_border};
                    color: {text_color};
                    font-size: 0.72rem;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-weight: 600;
                }}

                .secao-card {{
                    background: {card_bg_alt};
                    border: 1px solid {card_border};
                    border-radius: 6px;
                    padding: 10px 12px;
                    margin-bottom: 10px;
                    transition: border-color 0.2s;
                }}
                .secao-card:hover {{
                    border-color: {accent_color};
                }}
                .secao-topo {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 8px;
                }}
                .secao-titulo {{
                    font-size: 0.88rem;
                    font-weight: 700;
                    color: {text_color};
                }}
                .secao-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 6px;
                    margin-bottom: 8px;
                }}
                .stat-box {{
                    background: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 4px;
                    padding: 4px 6px;
                    text-align: center;
                }}
                .stat-lbl {{
                    font-size: 0.65rem;
                    color: {text_muted};
                    text-transform: uppercase;
                    font-weight: 600;
                }}
                .stat-val {{
                    font-size: 0.80rem;
                    font-weight: 700;
                    color: {text_color};
                    margin-top: 2px;
                }}
                .secao-criterios {{
                    font-size: 0.76rem;
                    color: {text_color};
                    margin-bottom: 4px;
                    line-height: 1.35;
                }}
                .secao-diag {{
                    font-size: 0.74rem;
                    color: {text_muted};
                    line-height: 1.35;
                    margin-bottom: 4px;
                }}
                .secao-logs {{
                    background: rgba(239, 68, 68, 0.1);
                    border: 1px solid rgba(239, 68, 68, 0.25);
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 0.72rem;
                    color: #f87171;
                    margin-top: 6px;
                }}
                .secao-vazia {{
                    padding: 20px;
                    text-align: center;
                    color: {text_muted};
                    font-size: 0.82rem;
                }}

                /* Badges de Risco */
                .badge {{
                    display: inline-block;
                    font-size: 0.68rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    padding: 2px 7px;
                    border-radius: 4px;
                }}
                .badge-alto {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
                .badge-medio {{ background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid #f97316; }}
                .badge-baixo {{ background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid #eab308; }}
                .badge-logs {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }}
            </style>
        </head>
        <body>
            <div id="map-container">
                <div id="map"></div>
                
                <!-- Gaveta Lateral Flutuante -->
                <div id="drawer" class="drawer" role="dialog" aria-modal="true" aria-hidden="true">
                    <div class="drawer-header">
                        <div style="flex: 1; min-width: 0;">
                            <div id="drawer-badge-container"></div>
                            <h3 id="drawer-title" class="drawer-title"></h3>
                        </div>
                        <button id="drawer-close" class="drawer-close-btn" title="Fechar painel (Esc)">&times;</button>
                    </div>
                    <div id="drawer-content" class="drawer-content">
                        <div id="drawer-meta" class="drawer-card-meta"></div>
                        
                        <div class="drawer-secoes-header">
                            <span>🗳️ Seções Prioritárias no Prédio</span>
                            <span id="drawer-badge-qtd" class="badge-qtd">0</span>
                        </div>
                        
                        <div id="drawer-secoes-list" class="drawer-secoes-list"></div>
                    </div>
                </div>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.js"></script>
            <script>
                const dados = {dados_json};
                const secoesData = {secoes_json};
                const map = L.map('map', {{
                    center: [{lat_centro}, {lon_centro}],
                    zoom: {zoom_inicial},
                    maxZoom: 18,
                    minZoom: 3
                }});

                // Camadas de Mapa 100% Livres (Sem Chave de API / Sem Watermark)
                const camadaOSM = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> colaboradores'
                }});

                const camadaEsriDark = L.layerGroup([
                    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        maxZoom: 16,
                        attribution: '&copy; Esri, HERE, Garmin, OpenStreetMap'
                    }}),
                    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        maxZoom: 16
                    }})
                ]);

                const camadaEsriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                    maxZoom: 19,
                    attribution: '&copy; Esri, Maxar, Earthstar Geographics'
                }});

                // Força OpenStreetMap como camada ativa por padrão ao carregar
                camadaOSM.addTo(map);

                // Controle no canto superior direito para alternar visão (OSM como 1ª opção)
                const baseMaps = {{
                    "🗺️ Padrão (OSM)": camadaOSM,
                    "🌙 Escuro": camadaEsriDark,
                    "🛰️ Satélite": camadaEsriSat
                }};
                L.control.layers(baseMaps, null, {{ position: 'topright' }}).addTo(map);

                const markers = L.markerClusterGroup({{
                    chunkedLoading: true,
                    spiderfyOnMaxZoom: true,
                    showCoverageOnHover: false,
                    zoomToBoundsOnClick: true,
                    maxClusterRadius: 45
                }});

                function corPino(risco) {{
                    if (risco === 'alto') return '#ef4444';
                    if (risco === 'medio') return '#f97316';
                    return '#eab308';
                }}

                let activeMarker = null;

                function fecharPainel() {{
                    const drawer = document.getElementById('drawer');
                    if (drawer) {{
                        drawer.classList.remove('open');
                        drawer.setAttribute('aria-hidden', 'true');
                    }}
                    if (activeMarker) {{
                        activeMarker.setStyle({{
                            radius: 6,
                            weight: 1.2,
                            color: '#ffffff'
                        }});
                        activeMarker = null;
                    }}
                }}

                function abrirPainel(p, marker) {{
                    if (activeMarker && activeMarker !== marker) {{
                        activeMarker.setStyle({{
                            radius: 6,
                            weight: 1.2,
                            color: '#ffffff'
                        }});
                    }}
                    activeMarker = marker;
                    marker.setStyle({{
                        radius: 9,
                        weight: 3,
                        color: '#38bdf8'
                    }});
                    marker.bringToFront();

                    // Atualiza cabeçalho da gaveta
                    const badgeClass = p.risco === 'alto' ? 'badge-alto' : (p.risco === 'medio' ? 'badge-medio' : 'badge-baixo');
                    const badgeRotulo = p.risco === 'alto' ? '🔴 Prioridade Alta' : (p.risco === 'medio' ? '🟠 Prioridade Média' : '🟡 Baixa Prioridade');
                    document.getElementById('drawer-badge-container').innerHTML = `<span class="badge ${{badgeClass}}">${{badgeRotulo}}</span>`;
                    document.getElementById('drawer-title').textContent = p.nome;

                    // Atualiza Metadados
                    const aptosStr = (p.aptos || 0).toLocaleString('pt-BR');
                    document.getElementById('drawer-meta').innerHTML = `
                        <div class="meta-item">📍 <b>Endereço:</b> ${{p.end || 'Não informado'}}</div>
                        <div class="meta-row">
                            <div>📮 <b>CEP:</b> ${{p.cep || '—'}}</div>
                            <div>🏛️ <b>Zona:</b> ${{p.zona}} (${{p.mun}})</div>
                        </div>
                        <div class="meta-row">
                            <div>🗳️ <b>Seções no Prédio:</b> ${{p.secoes}}</div>
                            <div>👥 <b>Eleitores Aptos:</b> ${{aptosStr}}</div>
                        </div>
                        <div>
                            <a href="https://www.google.com/maps/search/?api=1&query=${{p.lat}},${{p.lon}}" target="_blank" class="btn-maps">
                                📍 Navegar no Google Maps ↗
                            </a>
                        </div>
                    `;

                    // Renderiza Seções
                    const secoes = secoesData[p.id] || [];
                    document.getElementById('drawer-badge-qtd').textContent = secoes.length;
                    const listContainer = document.getElementById('drawer-secoes-list');

                    if (secoes.length === 0) {{
                        listContainer.innerHTML = `
                            <div class="secao-vazia">
                                ℹ️ Nenhuma seção individual com atipicidade grave catalogada neste prédio.
                            </div>
                        `;
                    }} else {{
                        let htmlSec = '';
                        secoes.forEach(s => {{
                            const sBadgeClass = s.nivel === 'alta' ? 'badge-alto' : (s.nivel === 'media' ? 'badge-medio' : (s.nivel === 'logs' ? 'badge-logs' : 'badge-baixo'));
                            const sBadgeRotulo = s.nivel === 'alta' ? '🔴 Alta' : (s.nivel === 'media' ? '🟠 Média' : (s.nivel === 'logs' ? '🔵 Log' : '🟡 Baixa'));
                            
                            let logHtml = '';
                            if (s.logs && s.logs !== '—' && s.logs.trim() !== '') {{
                                logHtml = `<div class="secao-logs"><b>⚠️ Logs da Urna:</b> ${{s.logs}}</div>`;
                            }}

                            htmlSec += `
                                <div class="secao-card">
                                    <div class="secao-topo">
                                        <span class="secao-titulo">🗳️ Seção ${{s.secao}}</span>
                                        <span class="badge ${{sBadgeClass}}">${{sBadgeRotulo}}</span>
                                    </div>
                                    <div class="secao-grid">
                                        <div class="stat-box">
                                            <div class="stat-lbl">Comparec.</div>
                                            <div class="stat-val">${{s.comp}} (${{s.pct_comp}}%)</div>
                                        </div>
                                        <div class="stat-box">
                                            <div class="stat-lbl">Cand. 1</div>
                                            <div class="stat-val">${{s.flavio}}</div>
                                        </div>
                                        <div class="stat-box">
                                            <div class="stat-lbl">Cand. 2</div>
                                            <div class="stat-val">${{s.lula}}</div>
                                        </div>
                                    </div>
                                    <div class="secao-criterios">
                                        <b>Critérios:</b> ${{s.criterios}}
                                    </div>
                                    ${{s.explicacao ? `<div class="secao-diag"><b>Diagnóstico:</b> ${{s.explicacao}}</div>` : ''}}
                                    ${{logHtml}}
                                </div>
                            `;
                        }});
                        listContainer.innerHTML = htmlSec;
                    }}

                    const drawer = document.getElementById('drawer');
                    if (drawer) {{
                        drawer.classList.add('open');
                        drawer.setAttribute('aria-hidden', 'false');
                    }}

                    // Pan suave compensando a largura da gaveta à direita
                    if (window.innerWidth > 600) {{
                        const targetPt = map.project([p.lat, p.lon], map.getZoom()).add([140, 0]);
                        const targetLatLng = map.unproject(targetPt, map.getZoom());
                        map.panTo(targetLatLng, {{ animate: true, duration: 0.3 }});
                    }} else {{
                        map.panTo([p.lat, p.lon], {{ animate: true, duration: 0.3 }});
                    }}
                }}

                // Listeners de Fechamento da Gaveta
                const btnFechar = document.getElementById('drawer-close');
                if (btnFechar) {{
                    btnFechar.addEventListener('click', (e) => {{
                        e.stopPropagation();
                        fecharPainel();
                    }});
                }}

                document.addEventListener('keydown', (e) => {{
                    if (e.key === 'Escape') fecharPainel();
                }});

                map.on('click', () => {{
                    fecharPainel();
                }});

                dados.forEach(p => {{
                    const cor = corPino(p.risco);
                    const marker = L.circleMarker([p.lat, p.lon], {{
                        radius: 6,
                        fillColor: cor,
                        color: '#ffffff',
                        weight: 1.2,
                        opacity: 0.9,
                        fillOpacity: 0.85
                    }});

                    marker.bindTooltip(`<b>${{p.nome}}</b><br><span style="font-size:0.75rem;">${{p.end}}</span>`, {{
                        direction: 'top',
                        offset: [0, -4],
                        opacity: 0.95
                    }});

                    marker.on('click', (e) => {{
                        L.DomEvent.stopPropagation(e);
                        abrirPainel(p, marker);
                    }});

                    markers.addLayer(marker);
                }});
                map.addLayer(markers);
            </script>
        </body>
        </html>
        """

        if hasattr(st, "iframe"):
            st.iframe(html_mapa, height=670, width="stretch")
        else:
            st.components.v1.html(html_mapa, height=670, scrolling=False)

    # ----------------------------------------------------
    # MODO 2: LISTA DE LOCAIS & EXPORTAÇÃO CSV
    # ----------------------------------------------------
    else:
        st.markdown("### 📋 Tabela Analítica dos Locais de Votação")

        col_esq, col_dir = st.columns([3, 1])
        with col_esq:
            st.caption(f"Exibindo **{len(df_l):,} prédios** de votação contendo **{len(df_s):,} seções sinalizadas** no filtro ativo.")
        with col_dir:
            # Botão de Exportação CSV Sob Demanda
            csv_data = df_l[[
                "uf", "municipio", "zona", "local", "endereco", "bairro", "cep", "risco", "secoes_total", "aptos_total"
            ]].to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 Exportar Prédios (CSV)",
                data=csv_data,
                file_name=f"radar_locais_{uf_selecionada.split(' ')[0]}.csv",
                mime="text/csv",
                width="stretch"
            )

        # Exibição tabulada dos prédios
        df_tabela = df_l[[
            "uf", "municipio", "zona", "local", "bairro", "cep", "risco", "secoes_total", "aptos_total"
        ]].rename(columns={
            "uf": "UF",
            "municipio": "Município",
            "zona": "Zona",
            "local": "Colégio / Prédio",
            "bairro": "Bairro",
            "cep": "CEP",
            "risco": "Prioridade",
            "secoes_total": "Total Seções",
            "aptos_total": "Aptos"
        })

        evento_tabela = st.dataframe(
            df_tabela,
            width="stretch",
            hide_index=True,
            height=380,
            on_select="rerun",
            selection_mode="single-row",
            key="tabela_locais_votacao"
        )

        st.markdown("---")
        st.markdown("#### 🔍 Ficha Detalhada do Prédio de Votação")

        # Identifica se o usuário clicou em uma linha da tabela analítica
        local_id_selecionado = st.session_state.get("mapa_local_id_ativo")

        if evento_tabela:
            sel_rows = None
            if hasattr(evento_tabela, "selection") and hasattr(evento_tabela.selection, "rows"):
                sel_rows = evento_tabela.selection.rows
            elif isinstance(evento_tabela, dict) and "selection" in evento_tabela:
                sel_rows = evento_tabela["selection"].get("rows")

            if sel_rows and len(sel_rows) > 0:
                idx_clicado = sel_rows[0]
                if 0 <= idx_clicado < len(df_l):
                    local_id_selecionado = df_l.iloc[idx_clicado]["id"]
                    st.session_state["mapa_local_id_ativo"] = local_id_selecionado

        # Opções do seletor abrangendo todos os prédios filtrados
        locais_opcoes = {"(Clique em uma linha da tabela acima ou selecione um prédio aqui...)": None}
        labels_por_id = {}
        if not df_l.empty:
            for row in df_l.itertuples():
                rotulo = f"{row.local} — {row.bairro} ({row.municipio}/{row.uf})"
                if rotulo in locais_opcoes:
                    rotulo = f"{row.local} — Zona {row.zona} — {row.bairro} ({row.municipio}/{row.uf})"
                locais_opcoes[rotulo] = row.id
                labels_por_id[row.id] = rotulo

        lista_rotulos = list(locais_opcoes.keys())
        idx_inicial = 0
        if local_id_selecionado in labels_por_id:
            label_alvo = labels_por_id[local_id_selecionado]
            if label_alvo in lista_rotulos:
                idx_inicial = lista_rotulos.index(label_alvo)

        col_escolhido = st.selectbox(
            "Escolha um prédio para abrir o raio-x:",
            lista_rotulos,
            index=idx_inicial,
            key="seletor_predio_raiox",
            help="Clique diretamente em qualquer linha da tabela de prédios para carregar suas seções aqui."
        )
        id_do_selectbox = locais_opcoes.get(col_escolhido)

        # Prioriza o colégio ativo (seja por clique na tabela ou seleção no dropdown)
        local_id_final = id_do_selectbox if id_do_selectbox is not None else local_id_selecionado

        if local_id_final is not None:
            local_match = df_l[df_l["id"] == local_id_final]
            if not local_match.empty:
                local_row = local_match.iloc[0]
                secoes_do_local = df_secoes[df_secoes["local_id"] == local_id_final] if not df_secoes.empty else pd.DataFrame()

            c_info1, c_info2 = st.columns([2, 1])
            with c_info1:
                st.markdown(f"**🏫 Prédio:** {local_row['local']}")
                st.markdown(f"**📍 Endereço:** {local_row['endereco']} — Bairro {local_row['bairro']} (CEP: {local_row['cep']})")
                st.markdown(f"**🏛️ Zona Eleitoral:** {local_row['zona']} • Município: {local_row['municipio']} - {local_row['uf']}")
            with c_info2:
                risco_rotulo = NIVEIS_ROTULO.get(local_row["risco"], local_row["risco"])
                st.markdown(f"**Grau de Atenção:** {risco_rotulo}")
                st.markdown(f"**Total de Seções no Local:** {local_row['secoes_total']}")
                st.markdown(f"**Eleitores Aptos:** {fmt_int_br(local_row['aptos_total'])}")

            st.markdown("##### Seções Sinalizadas Neste Prédio:")
            if not secoes_do_local.empty:
                df_sec_show = secoes_do_local[[
                    "secao", "nivel", "criterios", "explicacao", "aptos", "comparecimento", "flavio_pct", "lula_pct", "logs"
                ]].rename(columns={
                    "secao": "Seção",
                    "nivel": "Nível",
                    "criterios": "Critérios",
                    "explicacao": "Diagnóstico",
                    "aptos": "Aptos",
                    "comparecimento": "Votantes",
                    "flavio_pct": "% Candidato 1",
                    "lula_pct": "% Candidato 2",
                    "logs": "Alertas no Log"
                })
                st.dataframe(df_sec_show, width="stretch", hide_index=True)
            else:
                st.info("Nenhuma seção com atipicidade grave catalogada para este local.")
        else:
            st.info("👆 **Dica de Navegação:** Clique em qualquer linha da tabela de colégios acima para abrir seu raio-x completo e inspecionar as seções sinalizadas.")

