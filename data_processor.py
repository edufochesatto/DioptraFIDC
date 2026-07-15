"""
Módulo de processamento e análise dos dados de FIDCs.
Filtra por duplicatas/PME e calcula métricas de governança.
"""
import pandas as pd
import numpy as np
from pathlib import Path

COLUNAS_TAB_I = [
    'CNPJ_FUNDO', 'DENOMINACAO_SOCIAL', 'CLASSE',
    'VL_PL', 'VL_TOTAL_ATIVO',
    'VL_COTA_SENIOR', 'VL_COTA_SUBORDINADA',
    'CLASSE_UNICA'
]
COLUNAS_TAB_II = ['CNPJ_FUNDO', 'CNPJ_SACADO', 'NM_SACADO', 'VL_ATIVO', 'QT_ATIVO']
COLUNAS_TAB_III = ['CNPJ_FUNDO', 'QT_DICRED_ALIEN', 'VL_DICRED_ALIEN', 'VL_DICRED_ALIEN_CONTAB']
COLUNAS_TAB_V = ['CNPJ_FUNDO', 'VL_PDD']
COLUNAS_TAB_VI = ['CNPJ_FUNDO', 'PRAZO_MEDIO']
COLUNAS_TAB_VII = ['CNPJ_FUNDO', 'VL_LIQ', 'VL_TIT_PUBLICO']
COLUNAS_TAB_IX = ['CNPJ_FUNDO', 'CNPJ_CEDENTE', 'NM_CEDENTE', 'VL_ATIVO', 'QT_ATIVO']

def carregar_tabela(data_dir, nome_arquivo, colunas=None):
    data_dir = Path(data_dir)
    arquivo = data_dir / nome_arquivo
    if not arquivo.exists():
        matches = list(data_dir.glob(f"*{nome_arquivo}*"))
        if not matches:
            raise FileNotFoundError(f"{nome_arquivo} não encontrado em {data_dir}")
        arquivo = matches[0]
    try:
        df = pd.read_csv(arquivo, sep=';', encoding='latin1', decimal=',', usecols=colunas)
    except (ValueError, TypeError):
        df = pd.read_csv(arquivo, sep=';', encoding='latin1', decimal=',')
        if colunas:
            existentes = [c for c in colunas if c in df.columns]
            df = df[existentes]
    return df

def tratar_numericos(df):
    for col in df.columns:
        if col.startswith('VL_') or col.startswith('QT_') or col == 'PRAZO_MEDIO':
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def filtrar_duplicatas_pme(tab_i, tab_ii, tab_iii, tab_v, tab_vi, tab_vii, tab_ix):
    tab_i = tratar_numericos(tab_i)
    if 'CLASSE' in tab_i.columns:
        tab_i = tab_i[tab_i['CLASSE'].str.upper().str.contains('DUPLICATA|PME', na=False)].copy()
    tab_i['CNPJ_FUNDO'] = tab_i['CNPJ_FUNDO'].astype(str).str.strip()

    tab_ii = tratar_numericos(tab_ii)
    tab_ii['CNPJ_FUNDO'] = tab_ii['CNPJ_FUNDO'].astype(str).str.strip()
    conc_sac = tab_ii.groupby('CNPJ_FUNDO').agg(
        NUM_SACADOS=('CNPJ_SACADO', 'nunique'),
        CONC_TOP5_SACADOS=('VL_ATIVO', lambda x: round(x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
    ).reset_index()

    tab_iii = tratar_numericos(tab_iii)
    tab_iii['CNPJ_FUNDO'] = tab_iii['CNPJ_FUNDO'].astype(str).str.strip()
    recompra = tab_iii.groupby('CNPJ_FUNDO').agg(INDICE_RECOMPRA=('VL_DICRED_ALIEN_CONTAB', 'sum')).reset_index()

    tab_v = tratar_numericos(tab_v)
    tab_v['CNPJ_FUNDO'] = tab_v['CNPJ_FUNDO'].astype(str).str.strip()
    pdd = tab_v.groupby('CNPJ_FUNDO').agg(PDD=('VL_PDD', 'sum')).reset_index()

    tab_vi = tratar_numericos(tab_vi)
    tab_vi['CNPJ_FUNDO'] = tab_vi['CNPJ_FUNDO'].astype(str).str.strip()
    prazo = tab_vi.groupby('CNPJ_FUNDO').agg(PRAZO_MEDIO=('PRAZO_MEDIO', 'mean')).reset_index()

    tab_vii = tratar_numericos(tab_vii)
    tab_vii['CNPJ_FUNDO'] = tab_vii['CNPJ_FUNDO'].astype(str).str.strip()
    liq = tab_vii.groupby('CNPJ_FUNDO').agg(VL_LIQ=('VL_LIQ', 'sum'), VL_TIT_PUBLICO=('VL_TIT_PUBLICO', 'sum')).reset_index()

    tab_ix = tratar_numericos(tab_ix)
    tab_ix['CNPJ_FUNDO'] = tab_ix['CNPJ_FUNDO'].astype(str).str.strip()
    conc_ced = tab_ix.groupby('CNPJ_FUNDO').agg(
        NUM_CEDENTES=('CNPJ_CEDENTE', 'nunique'),
        CONC_TOP5_CEDENTES=('VL_ATIVO', lambda x: round(x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
    ).reset_index()

    dfs = [tab_i, conc_sac, recompra, pdd, prazo, liq, conc_ced]
    df = dfs[0]
    for d in dfs[1:]:
        df = df.merge(d, on='CNPJ_FUNDO', how='left')

    if 'VL_TOTAL_ATIVO' in df.columns and 'VL_PL' in df.columns:
        df['OVERCOLLATERALIZATION'] = round(df['VL_TOTAL_ATIVO'] / df['VL_PL'].replace(0, np.nan), 2)
    if 'VL_LIQ' in df.columns and 'VL_PL' in df.columns:
        df['PCT_LIQUIDEZ'] = round(df['VL_LIQ'] / df['VL_PL'].replace(0, np.nan) * 100, 2)
    if 'PDD' in df.columns and 'VL_PL' in df.columns:
        df['PDD_PCT'] = round(df['PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2)
    if 'INDICE_RECOMPRA' in df.columns and 'VL_PL' in df.columns:
        df['RECOMPRA_PCT'] = round(df['INDICE_RECOMPRA'] / df['VL_PL'].replace(0, np.nan) * 100, 2)

    return df

def calcular_metricas_governanca(df):
    colunas = ['VL_PL', 'PRAZO_MEDIO', 'PDD_PCT', 'RECOMPRA_PCT',
               'CONC_TOP5_SACADOS', 'CONC_TOP5_CEDENTES', 'NUM_SACADOS',
               'NUM_CEDENTES', 'OVERCOLLATERALIZATION', 'PCT_LIQUIDEZ']
    validas = [c for c in colunas if c in df.columns]
    resumo = {}
    for col in validas:
        v = df[col].dropna()
        if len(v) == 0:
            continue
        resumo[col] = {
            'media': round(v.mean(), 2),
            'mediana': round(v.median(), 2),
            'desvio_padrao': round(v.std(), 2),
            'min': round(v.min(), 2),
            'max': round(v.max(), 2),
            'p25': round(v.quantile(0.25), 2),
            'p75': round(v.quantile(0.75), 2),
        }
    return resumo
