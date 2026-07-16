"""
data_processor.py — v3.0
Adaptado ao schema CVM 202606 (TAB_IV sem coluna de classificação)
"""
import pandas as pd
import numpy as np
from pathlib import Path

def _encontrar_coluna(df, *candidatos):
    """Busca coluna por nome exato → case-insensitive → substring."""
    for nome in candidatos:
        if nome in df.columns:
            return nome
        for col in df.columns:
            if col.strip().upper() == nome.upper():
                return col
    upper = [n.upper() for n in candidatos]
    for col in df.columns:
        cu = col.strip().upper()
        for n in upper:
            if n in cu or cu in n:
                return col
    return None

def carregar_tabela(data_dir, nome_exato):
    """Carrega CSV usando padrão exato _NOME_."""
    data_dir = Path(data_dir)
    matches = sorted(data_dir.glob(f"inf_mensal_fidc_tab_{nome_exato}_*.csv"))
    if not matches:
        matches = sorted(data_dir.glob(f"*_tab_{nome_exato}_*.csv"))
    if not matches:
        return None
    arquivo = matches[0]
    print(f"   [LOAD] {arquivo.name}")
    try:
        df = pd.read_csv(arquivo, sep=';', encoding='latin1', decimal=',')
        print(f"   [OK] {len(df)} linhas, {len(df.columns)} colunas")
        return df
    except Exception as e:
        print(f"   [ERRO] {e}")
        return None

def tratar_numericos(df):
    """Converte colunas para float."""
    for col in df.columns:
        if df[col].dtype == object:
            tentativa = pd.to_numeric(
                df[col].astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False),
                errors='coerce'
            )
            if tentativa.notna().sum() > 0:
                df[col] = tentativa.fillna(0)
    return df

def processar_duplicatas_pme(data_dir):
    """
    Pipeline completo adaptado ao schema CVM 202606.
    OBS: A TAB_IV não tem mais coluna de classificação (CLASSE).
    Processamos todos os fundos disponíveis.
    """
    # ── 1. Fundos — TAB_IV ──
    tab_iv = carregar_tabela(data_dir, "IV")
    if tab_iv is None or tab_iv.empty:
        raise FileNotFoundError("TAB_IV (fundos) não encontrada.")

    # Mostra valores únicos de TP_FUNDO_CLASSE para debug
    if 'TP_FUNDO_CLASSE' in tab_iv.columns:
        valores = tab_iv['TP_FUNDO_CLASSE'].dropna().unique().tolist()
        print(f"   [DEBUG] TP_FUNDO_CLASSE: {valores}")

    # Filtra apenas linhas com TP_FUNDO_CLASSE = 'Fundo' (dados individuais)
    # e descarta linhas agregadas 'Classe'
    if 'TP_FUNDO_CLASSE' in tab_iv.columns:
        tab_iv = tab_iv[tab_iv['TP_FUNDO_CLASSE'].astype(str).str.upper() == 'FUNDO'].copy()
        print(f"   → {len(tab_iv)} fundos individuais (excluindo agregados 'Classe')")
    else:
        print("   [AVISO] Coluna TP_FUNDO_CLASSE não encontrada. Usando todos.")

    if tab_iv.empty:
        print("   [AVISO] Nenhum fundo individual encontrado.")
        return tab_iv, {}

    # Renomeia colunas
    rename = {
        'CNPJ_FUNDO_CLASSE': 'CNPJ_FUNDO',
        'DENOM_SOCIAL': 'DENOMINACAO_SOCIAL',
        'TAB_IV_A_VL_PL': 'VL_PL',
    }
    tab_iv = tab_iv.rename(columns={k: v for k, v in rename.items() if k in tab_iv.columns})

    col_cnpj = _encontrar_coluna(tab_iv, 'CNPJ_FUNDO', 'CNPJ_FUNDO_CLASSE')
    if col_cnpj and col_cnpj != 'CNPJ_FUNDO':
        tab_iv = tab_iv.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    if 'CNPJ_FUNDO' not in tab_iv.columns:
        raise KeyError("CNPJ não encontrado.")

    tab_iv = tratar_numericos(tab_iv)
    tab_iv['CNPJ_FUNDO'] = tab_iv['CNPJ_FUNDO'].astype(str).str.strip()

    print(f"   → {len(tab_iv)} fundos disponíveis")

    df = tab_iv[['CNPJ_FUNDO']].copy()

    # ── 2. Prazo Médio — TAB_VI ──
    tab_vi = carregar_tabela(data_dir, "VI")
    prazo_df = None
    if tab_vi is not None and not tab_vi.empty:
        col_cnpj_vi = _encontrar_coluna(tab_vi, 'CNPJ_FUNDO', 'CNPJ_FUNDO_CLASSE')
        if col_cnpj_vi:
            if col_cnpj_vi != 'CNPJ_FUNDO':
                tab_vi = tab_vi.rename(columns={col_cnpj_vi: 'CNPJ_FUNDO'})
            tab_vi['CNPJ_FUNDO'] = tab_vi['CNPJ_FUNDO'].astype(str).str.strip()
            tab_vi = tratar_numericos(tab_vi)

            # Filtra apenas linhas de fundo individual
            if 'TP_FUNDO_CLASSE' in tab_vi.columns:
                tab_vi = tab_vi[tab_vi['TP_FUNDO_CLASSE'].astype(str).str.upper() == 'FUNDO'].copy()

            dias_por_coluna = {
                'TAB_VI_A1_VL_PRAZO_VENC_30': 15,
                'TAB_VI_A2_VL_PRAZO_VENC_60': 45,
                'TAB_VI_A3_VL_PRAZO_VENC_90': 75,
                'TAB_VI_A4_VL_PRAZO_VENC_120': 105,
                'TAB_VI_A5_VL_PRAZO_VENC_150': 135,
                'TAB_VI_A6_VL_PRAZO_VENC_180': 165,
                'TAB_VI_A7_VL_PRAZO_VENC_360': 270,
                'TAB_VI_A8_VL_PRAZO_VENC_720': 540,
                'TAB_VI_A9_VL_PRAZO_VENC_1080': 900,
                'TAB_VI_A10_VL_PRAZO_VENC_MAIOR_1080': 1200,
            }
            resultados = []
            for cnpj, grupo in tab_vi.groupby('CNPJ_FUNDO'):
                sp = 0.0
                peso = 0.0
                for col, dias in dias_por_coluna.items():
                    if col in grupo.columns:
                        v = pd.to_numeric(grupo[col], errors='coerce').sum()
                        if v > 0:
                            sp += v * dias
                            peso += v
                prazo = round(sp / peso, 1) if peso > 0 else 0
                resultados.append({'CNPJ_FUNDO': cnpj, 'PRAZO_MEDIO': prazo})
            prazo_df = pd.DataFrame(resultados)

    # ── 3. Recompra e Cedentes — TAB_VII ──
    tab_vii = carregar_tabela(data_dir, "VII")
    recompra_df = None
    cedentes_df = None
    if tab_vii is not None and not tab_vii.empty:
        col_cnpj_vii = _encontrar_coluna(tab_vii, 'CNPJ_FUNDO', 'CNPJ_FUNDO_CLASSE')
        if col_cnpj_vii:
            if col_cnpj_vii != 'CNPJ_FUNDO':
                tab_vii = tab_vii.rename(columns={col_cnpj_vii: 'CNPJ_FUNDO'})
            tab_vii['CNPJ_FUNDO'] = tab_vii['CNPJ_FUNDO'].astype(str).str.strip()
            tab_vii = tratar_numericos(tab_vii)

            # Filtra apenas fundos individuais
            if 'TP_FUNDO_CLASSE' in tab_vii.columns:
                tab_vii = tab_vii[tab_vii['TP_FUNDO_CLASSE'].astype(str).str.upper() == 'FUNDO'].copy()

            col_rec = _encontrar_coluna(tab_vii, 'TAB_VII_D_2_VL_RECOMPRA', 'TAB_VII_D_3_VL_CONTAB_RECOMPRA')
            if col_rec:
                recompra_df = tab_vii.groupby('CNPJ_FUNDO').agg(
                    INDICE_RECOMPRA=(col_rec, 'sum')
                ).reset_index()

            col_qt_ced = _encontrar_coluna(tab_vii, 'TAB_VII_B1_1_QT_CEDENTE')
            if col_qt_ced:
                cedentes_df = tab_vii.groupby('CNPJ_FUNDO').agg(
                    NUM_CEDENTES=(col_qt_ced, 'sum')
                ).reset_index()

    # ── 4. PDD — TAB_V ──
    tab_v = carregar_tabela(data_dir, "V")
    pdd_df = None
    if tab_v is not None and not tab_v.empty:
        col_cnpj_v = _encontrar_coluna(tab_v, 'CNPJ_FUNDO', 'CNPJ_FUNDO_CLASSE')
        if col_cnpj_v:
            if col_cnpj_v != 'CNPJ_FUNDO':
                tab_v = tab_v.rename(columns={col_cnpj_v: 'CNPJ_FUNDO'})
            tab_v['CNPJ_FUNDO'] = tab_v['CNPJ_FUNDO'].astype(str).str.strip()
            tab_v = tratar_numericos(tab_v)

            # Filtra apenas fundos individuais
            if 'TP_FUNDO_CLASSE' in tab_v.columns:
                tab_v = tab_v[tab_v['TP_FUNDO_CLASSE'].astype(str).str.upper() == 'FUNDO'].copy()

            col_pdd = _encontrar_coluna(tab_v, 'VL_PDD', 'VL_PROVISAO')
            if col_pdd:
                pdd_df = tab_v.groupby('CNPJ_FUNDO').agg(PDD=(col_pdd, 'sum')).reset_index()

    # ── Merge ──
    merges = [
        ('PL', tab_iv[['CNPJ_FUNDO', 'VL_PL']] if 'VL_PL' in tab_iv.columns and not tab_iv.empty else None),
        ('Prazo', prazo_df),
        ('Recompra', recompra_df),
        ('PDD', pdd_df),
        ('Cedentes', cedentes_df),
    ]
    for nome, tbl in merges:
        if tbl is not None and not tbl.empty:
            cols = [c for c in tbl.columns if c != 'CNPJ_FUNDO']
            if cols:
                df = df.merge(tbl[['CNPJ_FUNDO'] + cols], on='CNPJ_FUNDO', how='left')

    # ── Métricas derivadas ──
    if 'VL_PL' in df.columns:
        df['VL_PL'] = pd.to_numeric(df['VL_PL'], errors='coerce').fillna(0)
        if 'PDD' in df.columns:
            df['PDD_PCT'] = round(df['PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2)
        if 'INDICE_RECOMPRA' in df.columns:
            df['RECOMPRA_PCT'] = round(df['INDICE_RECOMPRA'] / df['VL_PL'].replace(0, np.nan) * 100, 2)

    # ── Métricas de governança ──
    metricas = {}
    cols_metricas = {
        'VL_PL': 'PL', 'PRAZO_MEDIO': 'Prazo Médio',
        'PDD_PCT': 'PDD %PL', 'RECOMPRA_PCT': 'Recompra %PL',
        'NUM_CEDENTES': 'Nº Cedentes',
    }
    for col, nome in cols_metricas.items():
        if col in df.columns and df[col].notna().sum() > 0:
            v = df[col].dropna()
            if len(v) > 0:
                metricas[col] = {
                    'media': round(v.mean(), 2),
                    'mediana': round(v.median(), 2),
                    'desvio_padrao': round(v.std(), 2),
                    'min': round(v.min(), 2),
                    'max': round(v.max(), 2),
                    'p25': round(v.quantile(0.25), 2),
                    'p75': round(v.quantile(0.75), 2),
                }

    return df, metricas
