"""
Módulo de processamento e análise dos dados de FIDCs.
Filtra por duplicatas/PME e calcula métricas de governança.
"""
import pandas as pd
import numpy as np
from pathlib import Path

def _encontrar_coluna(df, *nomes_candidatos):
    """
    Procura uma coluna no DataFrame por vários nomes possíveis.
    Retorna o nome real encontrado ou None.
    """
    for nome in nomes_candidatos:
        if nome in df.columns:
            return nome
        # Busca case-insensitive
        for col in df.columns:
            if col.strip().upper() == nome.upper():
                return col
    return None

def carregar_tabela(data_dir, nome_arquivo, colunas=None):
    data_dir = Path(data_dir)
    arquivo = data_dir / nome_arquivo
    if not arquivo.exists():
        matches = list(data_dir.glob(f"*{nome_arquivo}*"))
        if not matches:
            raise FileNotFoundError(f"{nome_arquivo} não encontrado em {data_dir}")
        arquivo = matches[0]

    print(f"   [DEBUG] Carregando {arquivo.name}...")
    df = pd.read_csv(arquivo, sep=';', encoding='latin1', decimal=',')
    print(f"   [DEBUG] Colunas encontradas: {list(df.columns)}")

    if colunas:
        existentes = [c for c in colunas if c in df.columns]
        if existentes:
            df = df[existentes]

    return df

def tratar_numericos(df):
    for col in df.columns:
        if col.startswith('VL_') or col.startswith('QT_') or col == 'PRAZO_MEDIO':
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def filtrar_duplicatas_pme(tab_i, tab_ii, tab_iii, tab_v, tab_vi, tab_vii, tab_ix):
    # Descobre o nome real da coluna CNPJ_FUNDO
    col_cnpj = _encontrar_coluna(tab_i, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_')
    if col_cnpj is None:
        print(f"\n❌ Coluna CNPJ não encontrada. Colunas disponíveis: {list(tab_i.columns)}")
        raise KeyError("Coluna CNPJ_FUNDO não encontrada na tabela TAB_I")

    print(f"   [DEBUG] Coluna CNPJ encontrada como: '{col_cnpj}'")

    # Renomeia para um padrão
    tab_i = tab_i.rename(columns={col_cnpj: 'CNPJ_FUNDO'})

    tab_i = tratar_numericos(tab_i)

    if 'CLASSE' in tab_i.columns:
        tab_i = tab_i[tab_i['CLASSE'].str.upper().str.contains('DUPLICATA|PME', na=False)].copy()
    else:
        # Tenta encontrar classe por nome alternativo
        col_classe = _encontrar_coluna(tab_i, 'CLASSE', 'CLASSE_FUNDO', 'NM_CLASSE')
        if col_classe:
            tab_i = tab_i.rename(columns={col_classe: 'CLASSE'})
            tab_i = tab_i[tab_i['CLASSE'].str.upper().str.contains('DUPLICATA|PME', na=False)].copy()
        else:
            print("   [AVISO] Coluna CLASSE não encontrada. Usando todos os fundos.")

    tab_i['CNPJ_FUNDO'] = tab_i['CNPJ_FUNDO'].astype(str).str.strip()

    # TAB_II — Sacados
    col_cnpj_ii = _encontrar_coluna(tab_ii, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO')
    if col_cnpj_ii:
        tab_ii = tab_ii.rename(columns={col_cnpj_ii: 'CNPJ_FUNDO'})
    tab_ii = tratar_numericos(tab_ii)
    tab_ii['CNPJ_FUNDO'] = tab_ii['CNPJ_FUNDO'].astype(str).str.strip()

    col_sacado = _encontrar_coluna(tab_ii, 'CNPJ_SACADO', 'CNPJ_CPF_SACADO')
    if col_sacado:
        tab_ii = tab_ii.rename(columns={col_sacado: 'CNPJ_SACADO'})

    col_vl_ativo_ii = _encontrar_coluna(tab_ii, 'VL_ATIVO', 'VL_ATIVO_FINANCEIRO', 'VL_DIREITO_CREDITORIO')
    if col_vl_ativo_ii:
        tab_ii = tab_ii.rename(columns={col_vl_ativo_ii: 'VL_ATIVO'})

    conc_sac = tab_ii.groupby('CNPJ_FUNDO').agg(
        NUM_SACADOS=('CNPJ_SACADO', 'nunique'),
        CONC_TOP5_SACADOS=('VL_ATIVO', lambda x: round(x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
    ).reset_index()

    # TAB_III — Recompra
    col_cnpj_iii = _encontrar_coluna(tab_iii, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO')
    if col_cnpj_iii:
        tab_iii = tab_iii.rename(columns={col_cnpj_iii: 'CNPJ_FUNDO'})
    tab_iii = tratar_numericos(tab_iii)
    tab_iii['CNPJ_FUNDO'] = tab_iii['CNPJ_FUNDO'].astype(str).str.strip()

    col_recompra = _encontrar_coluna(tab_iii, 'VL_DICRED_ALIEN_CONTAB', 'VL_DICRED_ALIEN', 'VL_RECOMPRA')
    if col_recompra:
        tab_iii = tab_iii.rename(columns={col_recompra: 'VL_DICRED_ALIEN_CONTAB'})

    recompra = tab_iii.groupby('CNPJ_FUNDO').agg(
        INDICE_RECOMPRA=('VL_DICRED_ALIEN_CONTAB', 'sum')
    ).reset_index()

    # TAB_V — PDD
    col_cnpj_v = _encontrar_coluna(tab_v, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO')
    if col_cnpj_v:
        tab_v = tab_v.rename(columns={col_cnpj_v: 'CNPJ_FUNDO'})
    tab_v = tratar_numericos(tab_v)
    tab_v['CNPJ_FUNDO'] = tab_v['CNPJ_FUNDO'].astype(str).str.strip()

    col_pdd = _encontrar_coluna(tab_v, 'VL_PDD', 'VL_PROVISAO', 'VL_PDD_CONTABIL')
    if col_pdd:
        tab_v = tab_v.rename(columns={col_pdd: 'PDD'})

    pdd = tab_v.groupby('CNPJ_FUNDO').agg(
        PDD=('PDD' if col_pdd else 'VL_PDD', 'sum')
    ).reset_index()
    # Ajusta nome da coluna se necessário
    if 'PDD' not in pdd.columns:
        pdd = tab_v.groupby('CNPJ_FUNDO').agg(PDD=('VL_PDD', 'sum')).reset_index()

    # TAB_VI — Prazo Médio
    col_cnpj_vi = _encontrar_coluna(tab_vi, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO')
    if col_cnpj_vi:
        tab_vi = tab_vi.rename(columns={col_cnpj_vi: 'CNPJ_FUNDO'})
    tab_vi = tratar_numericos(tab_vi)
    tab_vi['CNPJ_FUNDO'] = tab_vi['CNPJ_FUNDO'].astype(str).str.strip()

    col_prazo = _encontrar_coluna(tab_vi, 'PRAZO_MEDIO', 'PRAZO_MEDIO_DIAS', 'PRAZO')
    if col_prazo:
        tab_vi = tab_vi.rename(columns={col_prazo: 'PRAZO_MEDIO'})

    prazo = tab_vi.groupby('CNPJ_FUNDO').agg(PRAZO_MEDIO=('PRAZO_MEDIO', 'mean')).reset_index()

    # TAB_VII — Liquidez
    col_cnpj_vii = _encontrar_coluna(tab_vii, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO')
    if col_cnpj_vii:
        tab_vii = tab_vii.rename(columns={col_cnpj_vii: 'CNPJ_FUNDO'})
    tab_vii = tratar_numericos(tab_vii)
    tab_vii['CNPJ_FUNDO'] = tab_vii['CNPJ_FUNDO'].astype(str).str.strip()

    col_liq = _encontrar_coluna(tab_vii, 'VL_LIQ', 'VL_DISPONIBILIDADES', 'VL_CAIXA')
    if col_liq:
        tab_vii = tab_vii.rename(columns={col_liq: 'VL_LIQ'})
    col_tp = _encontrar_coluna(tab_vii, 'VL_TIT_PUBLICO', 'VL_TITULOS_PUBLICOS', 'VL_TITULOS')
    if col_tp:
        tab_vii = tab_vii.rename(columns={col_tp: 'VL_TIT_PUBLICO'})

    liq = tab_vii.groupby('CNPJ_FUNDO').agg(
        VL_LIQ=('VL_LIQ', 'sum'),
        VL_TIT_PUBLICO=('VL_TIT_PUBLICO', 'sum')
    ).reset_index()

    # TAB_IX — Cedentes
    col_cnpj_ix = _encontrar_coluna(tab_ix, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO')
    if col_cnpj_ix:
        tab_ix = tab_ix.rename(columns={col_cnpj_ix: 'CNPJ_FUNDO'})
    tab_ix = tratar_numericos(tab_ix)
    tab_ix['CNPJ_FUNDO'] = tab_ix['CNPJ_FUNDO'].astype(str).str.strip()

    col_cedente = _encontrar_coluna(tab_ix, 'CNPJ_CEDENTE', 'CNPJ_CPF_CEDENTE')
    if col_cedente:
        tab_ix = tab_ix.rename(columns={col_cedente: 'CNPJ_CEDENTE'})

    col_vl_ix = _encontrar_coluna(tab_ix, 'VL_ATIVO', 'VL_ATIVO_FINANCEIRO', 'VL_DIREITO_CREDITORIO')
    if col_vl_ix:
        tab_ix = tab_ix.rename(columns={col_vl_ix: 'VL_ATIVO'})

    conc_ced = tab_ix.groupby('CNPJ_FUNDO').agg(
        NUM_CEDENTES=('CNPJ_CEDENTE', 'nunique'),
        CONC_TOP5_CEDENTES=('VL_ATIVO', lambda x: round(x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
    ).reset_index()

    # Merge de todas as tabelas
    dfs = [tab_i, conc_sac, recompra, pdd, prazo, liq, conc_ced]
    df = dfs[0]
    for d in dfs[1:]:
        df = df.merge(d, on='CNPJ_FUNDO', how='left')

    # Cálculo de métricas derivadas
    if 'VL_TOTAL_ATIVO' in df.columns and 'VL_PL' in df.columns:
        df['OVERCOLLATERALIZATION'] = round(df['VL_TOTAL_ATIVO'] / df['VL_PL'].replace(0, np.nan), 2)
    elif 'VL_PL' in df.columns:
        # Tenta usar soma de ativos de outra forma
        print("   [AVISO] VL_TOTAL_ATIVO não encontrada. Overcollateralization não calculada.")

    if 'VL_LIQ' in df.columns and 'VL_PL' in df.columns:
        df['PCT_LIQUIDEZ'] = round(df['VL_LIQ'] / df['VL_PL'].replace(0, np.nan) * 100, 2)

    # Ajuste: PDD pode vir com nome diferente
    if 'PDD' in df.columns and 'VL_PL' in df.columns:
        df['PDD_PCT'] = round(df['PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2)
    elif 'VL_PDD' in df.columns and 'VL_PL' in df.columns:
        df['PDD_PCT'] = round(df['VL_PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2)

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
