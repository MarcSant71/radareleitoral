"""
Módulo de Inferência Estatística Forense - Modelo de Efeitos Aleatórios de Spiegelhalter (2005).
Implementa o motor matemático de desvios padronizados (Z-scores ajustados e robustos)
para detecção de anomalias operacionais e temporais nas Eleições 2026.

Fundamentação Teórica:
1. David Spiegelhalter (2005) - "Funnel plots for comparing institutional performance".
2. Normalização relativa por município via técnica Leave-One-Out (a seção não se autoavalia).
3. Superdispersão residual entre seções (tau²) estimada por UF via MAD (Median Absolute Deviation).
4. Padronização robusta de horários de fechamento por mediana e escala MAD local.
"""

from typing import Tuple
import numpy as np
import pandas as pd

MIN_SECOES_MUNICIPIO = 5
PISO_ESCALA_HORARIO = 0.15  # 0.15 horas = 9 minutos (evita z infinito em cidades homogêneas)


def calc_z_proporcao(
    df: pd.DataFrame,
    num_col: str,
    den_col: str,
    min_den: int = 10
) -> Tuple[pd.Series, pd.Series]:
    """
    Calcula o z-score ajustado de Spiegelhalter (2005) para uma proporção amostral (num/den):
    - Compara com a proporção esperada do município (leave-one-out; UF se município < 5 seções).
    - Incorpora variância amostral binomial: p*(1-p)/den.
    - Estima e soma a variação natural entre seções (tau²) por UF de forma robusta via MAD.
    Retorna (z_score, taxa_esperada_pct).
    """
    num = df[num_col].astype(float)
    den = df[den_col].astype(float)
    ok = den >= min_den
    num_f = num.where(ok, np.nan)
    den_f = den.where(ok, np.nan)
    taxa = num_f / den_f

    g_mun = [df["uf"], df["municipio"]]
    n_mun = taxa.groupby(g_mun, observed=True).transform("count")
    s_mun = num_f.groupby(g_mun, observed=True).transform("sum")
    d_mun = den_f.groupby(g_mun, observed=True).transform("sum")
    s_uf = num_f.groupby(df["uf"], observed=True).transform("sum")
    d_uf = den_f.groupby(df["uf"], observed=True).transform("sum")

    # Leave-One-Out: subtrai os dados da própria seção para evitar viés de autocorrelação
    p_mun = (s_mun - num_f) / (d_mun - den_f).replace(0, np.nan)
    p_uf = (s_uf - num_f) / (d_uf - den_f).replace(0, np.nan)

    esperada = pd.Series(np.where(n_mun >= MIN_SECOES_MUNICIPIO, p_mun, p_uf), index=df.index).fillna(p_uf)
    p = esperada.clip(1e-4, 1.0 - 1e-4)
    var_acaso = p * (1.0 - p) / den_f
    resid = taxa - p

    def _tau2_uf(idx: pd.Index) -> float:
        r = resid.loc[idx].dropna()
        if len(r) < 20:
            return 0.0
        v = (1.4826 * (r - r.median()).abs().median()) ** 2
        return max(v - float(var_acaso.loc[r.index].median()), 0.0)

    tau2 = resid.groupby(df["uf"], observed=True).transform(lambda s: _tau2_uf(s.index))
    z = (resid / np.sqrt(var_acaso + tau2)).fillna(0.0)

    return z, (esperada * 100.0).round(1)


def calc_z_horario(df: pd.DataFrame, col_hora: str = "hora_ult_dec", piso: float = PISO_ESCALA_HORARIO) -> pd.Series:
    """
    Calcula z-score robusto de horário do último voto:
    (hora - mediana do município) / (1.4826 * MAD do município), com piso de escala.
    """
    g_mun = [df["uf"], df["municipio"]]
    hora = df[col_hora].astype(float)
    med_mun = hora.groupby(g_mun, observed=True).transform("median")
    mad_mun = (hora - med_mun).abs().groupby(g_mun, observed=True).transform("median") * 1.4826
    z = ((hora - med_mun) / np.maximum(mad_mun, piso)).fillna(0.0)
    return z


def aplicar_motor_estatistico(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executa a calibração estatística completa em memória para as seções eleitorais:
    - Adiciona z_pos17, esp_pos17_pct
    - Adiciona z_manual, esp_manual_pct
    - Adiciona z_horario
    - Adiciona z_composto (Distância Euclidiana L2 dos desvios padronizados positivos)
    - Gera alertas forenses objetivos baseados no desvio sigma real
    """
    if df.empty:
        return df

    df = df.copy()

    # Sanitização e coerção estrita de tipos numéricos do SQLite
    df["pct_apos_17h"] = pd.to_numeric(df.get("pct_apos_17h", 0.0), errors="coerce").fillna(0.0)
    df["total_votos_log"] = pd.to_numeric(df.get("total_votos_log", 0), errors="coerce").fillna(0).astype(int)
    df["votos_apos_17h"] = pd.to_numeric(df.get("votos_apos_17h", 0), errors="coerce").fillna(0).astype(int)
    df["habilitacao_manual_total"] = pd.to_numeric(df.get("habilitacao_manual_total", 0), errors="coerce").fillna(0).astype(int)
    df["hora_ult_dec"] = pd.to_numeric(df.get("hora_ult_dec", 17.0), errors="coerce").fillna(17.0)
    df["maior_ociosidade_antes_17h_min"] = pd.to_numeric(df.get("maior_ociosidade_antes_17h_min", 0.0), errors="coerce").fillna(0.0)
    df["tempo_medio_pos17h_segundos"] = pd.to_numeric(df.get("tempo_medio_pos17h_segundos", 0.0), errors="coerce").fillna(0.0)

    # 1. Z-scores de Proporção (Spiegelhalter 2005)
    z_17, esp_17 = calc_z_proporcao(df, "votos_apos_17h", "total_votos_log")
    z_man, esp_man = calc_z_proporcao(df, "habilitacao_manual_total", "total_votos_log")

    # 2. Z-score Robusto de Horário de Fechamento
    z_hora = calc_z_horario(df, "hora_ult_dec")

    df["z_pos17"] = z_17.round(1)
    df["esp_pos17_pct"] = esp_17
    df["z_manual"] = z_man.round(1)
    df["esp_manual_pct"] = esp_man
    df["z_horario"] = z_hora.round(1)

    # 3. Métrica Composta de Desvio (Norma L2 Euclidiana de Desvios Positivos)
    # sqrt(z_pos17² + z_manual² + z_horario²) para z > 0
    z1 = np.maximum(df["z_pos17"], 0.0)
    z2 = np.maximum(df["z_manual"], 0.0)
    z3 = np.maximum(df["z_horario"], 0.0)
    z_l2 = np.sqrt(z1**2 + z2**2 + z3**2)
    df["z_composto"] = z_l2.round(1)

    # 4. Classificação por Nível de Atipicidade
    condicoes = [
        df["z_composto"] >= 4.5,
        df["z_composto"] >= 3.0,
        df["z_composto"] >= 2.0
    ]
    rotulos = [
        "🔴 Extrema (≥ 4.5σ)",
        "🟠 Alta (3.0σ – 4.4σ)",
        "🟡 Atenção (2.0σ – 2.9σ)"
    ]
    df["nivel_atipicidade"] = np.select(condicoes, rotulos, default="Normal (< 2.0σ)")

    # 5. Geração Vetorizada dos Motivos de Alerta Estatísticos & Forenses
    s_alertas = pd.Series("", index=df.index, dtype=object)

    def _anexar(mask: pd.Series, txt_series: pd.Series):
        nonlocal s_alertas
        m = mask.fillna(False)
        if m.any():
            separador = np.where(s_alertas[m] == "", "", " | ")
            s_alertas[m] = s_alertas[m] + separador + txt_series[m]

    # Alerta A: Votação tardia expressiva
    mask_17 = df["z_pos17"] >= 2.0
    txt_17 = (
        "Pós-17h a +" + df["z_pos17"].astype(str) + "σ do município (obs " +
        df["pct_apos_17h"].round(1).astype(str) + "% vs esp " +
        df["esp_pos17_pct"].round(1).astype(str) + "%)"
    )
    _anexar(mask_17, txt_17)

    # Alerta B: Liberação manual atípica
    mask_man = df["z_manual"] >= 2.0
    pct_man_calc = (df["habilitacao_manual_total"] * 100.0 / np.maximum(df["total_votos_log"], 1)).round(1)
    txt_man = (
        "Manual a +" + df["z_manual"].astype(str) + "σ do município (obs " +
        pct_man_calc.astype(str) + "% vs esp " +
        df["esp_manual_pct"].round(1).astype(str) + "%)"
    )
    _anexar(mask_man, txt_man)

    # Alerta C: Horário do último voto atípico
    mask_hora = df["z_horario"] >= 2.0
    txt_hora = "Fechamento tardio a +" + df["z_horario"].astype(str) + "σ da mediana municipal"
    _anexar(mask_hora, txt_hora)

    # Alerta D: Urna ociosa na última hora antes do encerramento
    mask_ociosa = df["maior_ociosidade_antes_17h_min"] >= 20.0
    txt_ociosa = pd.Series("Urna ociosa ≥20 min antes das 17h", index=df.index)
    _anexar(mask_ociosa, txt_ociosa)

    # Alerta E: Ritmo acelerado
    mask_ritmo = (df["votos_apos_17h"] >= 10) & (df["tempo_medio_pos17h_segundos"] > 0) & (df["tempo_medio_pos17h_segundos"] <= 45.0)
    txt_ritmo = pd.Series("Ritmo ultrarrápido pós-17h (≤45s/voto)", index=df.index)
    _anexar(mask_ritmo, txt_ritmo)

    df["motivos_alerta"] = np.where(s_alertas != "", s_alertas, "Padrão normal (dentro de 95% do município)")

    return df


def aplicar_motor_abstencao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executa a inferência estatística de abstenção e comparecimento:
    - Adiciona pct_abstencao, pct_comparecimento
    - Adiciona z_abstencao, esp_abstencao_pct (Spiegelhalter 2005)
    - Adiciona classificações e alertas objetivos de atipicidade (ex: baixa abstenção anômala)
    """
    if df.empty or "total_aptos" not in df.columns:
        return df

    df = df.copy()

    # Sanitização e coerção estrita de tipos numéricos
    df["total_aptos"] = pd.to_numeric(df.get("total_aptos", 0), errors="coerce").fillna(0).astype(int)
    df["faltosos_bu"] = pd.to_numeric(df.get("faltosos_bu", 0), errors="coerce").fillna(0).astype(int)
    df["comparecimento_bu"] = pd.to_numeric(df.get("comparecimento_bu", 0), errors="coerce").fillna(0).astype(int)

    if "pct_abstencao" in df.columns:
        df["pct_abstencao"] = pd.to_numeric(df["pct_abstencao"], errors="coerce")
    else:
        df["pct_abstencao"] = (df["faltosos_bu"] * 100.0 / np.maximum(df["total_aptos"], 1))
    df["pct_abstencao"] = df["pct_abstencao"].fillna(0.0).round(2)

    if "pct_comparecimento" in df.columns:
        df["pct_comparecimento"] = pd.to_numeric(df["pct_comparecimento"], errors="coerce")
    else:
        df["pct_comparecimento"] = (df["comparecimento_bu"] * 100.0 / np.maximum(df["total_aptos"], 1))
    df["pct_comparecimento"] = df["pct_comparecimento"].fillna(0.0).round(2)

    # Z-scores de Proporção (Spiegelhalter 2005) para Abstenção
    z_abst, esp_abst = calc_z_proporcao(df, "faltosos_bu", "total_aptos")
    df["z_abstencao"] = z_abst.round(1)
    df["esp_abstencao_pct"] = esp_abst

    # Classificação de Atipicidade da Abstenção
    condicoes = [
        df["z_abstencao"] <= -3.0,
        df["z_abstencao"] <= -2.0,
        df["z_abstencao"] >= 3.0,
        df["z_abstencao"] >= 2.0
    ]
    rotulos = [
        "🚨 Baixa Abstenção Extrema (Z ≤ -3.0σ)",
        "🔴 Baixa Abstenção Anômala (Z ≤ -2.0σ)",
        "🟠 Alta Abstenção Extrema (Z ≥ +3.0σ)",
        "🟡 Alta Abstenção Moderada (Z ≥ +2.0σ)"
    ]
    df["nivel_abstencao"] = np.select(condicoes, rotulos, default="Normal (|Z| < 2.0σ)")

    # Alertas Forenses de Abstenção
    s_alertas = pd.Series("", index=df.index, dtype=object)

    def _anexar_abst(mask: pd.Series, txt_series: pd.Series):
        nonlocal s_alertas
        m = mask.fillna(False)
        if m.any():
            separador = np.where(s_alertas[m] == "", "", " | ")
            s_alertas[m] = s_alertas[m] + separador + txt_series[m]

    # Alerta 1: Baixa abstenção extrema (muito menos faltosos do que o esperado)
    mask_baixa = df["z_abstencao"] <= -2.0
    txt_baixa = (
        "Baixa abstenção a " + df["z_abstencao"].astype(str) + "σ do município (obs " +
        df["pct_abstencao"].round(1).astype(str) + "% vs esp " +
        df["esp_abstencao_pct"].round(1).astype(str) + "%)"
    )
    _anexar_abst(mask_baixa, txt_baixa)

    # Alerta 2: Alta abstenção extrema
    mask_alta = df["z_abstencao"] >= 2.0
    txt_alta = (
        "Alta abstenção a +" + df["z_abstencao"].astype(str) + "σ do município (obs " +
        df["pct_abstencao"].round(1).astype(str) + "% vs esp " +
        df["esp_abstencao_pct"].round(1).astype(str) + "%)"
    )
    _anexar_abst(mask_alta, txt_alta)

    # Alerta 3: Abstenção ínfima (≤ 5% em seções com mais de 50 eleitores)
    mask_infima = (df["pct_abstencao"] <= 5.0) & (df["total_aptos"] >= 50)
    txt_infima = pd.Series("Abstenção quase nula (≤ 5% dos aptos)", index=df.index)
    _anexar_abst(mask_infima, txt_infima)

    df["motivos_alerta_abst"] = np.where(s_alertas != "", s_alertas, "Padrão normal de abstenção (dentro de 95% do município)")

    return df
