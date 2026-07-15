"""
Módulo de processamento e análise dos dados de FIDCs.
Filtra por duplicatas/PME e calcula métricas de governança.

ATUALIZADO: 15/07/2026 — Suporte ao novo schema da CVM (CNPJ_FUNDO_CLASSE)
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
    # Se não achou por nome exato, tenta substring
    nome_upper = [n.upper() for n in nomes_candidatos]
    for col in df.columns:
        col_upper = col.strip().upper()
        for n in nome_upper:
            if n in col_upper or col_upper in n:
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
    print(f"   [DEBUG] Colunas encontradas ({len(df.columns)}): {list(df.columns)}")

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
    # ── TAB_I ──
    # Tenta vários nomes possíveis para a coluna CNPJ
    col_cnpj = _encontrar_coluna(
        tab_i,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CNPJ_CLASSE',
        'CD_CNPJ_FUNDO', 'CD_FUNDO'
    )
    if col_cnpj is None:
        print(f"\n❌ Coluna CNPJ não encontrada. Colunas disponíveis: {list(tab_i.columns)}")
        raise KeyError("Coluna de identificação do fundo não encontrada na tabela TAB_I")

    print(f"   [DEBUG] Coluna CNPJ encontrada como: '{col_cnpj}'")
    tab_i = tab_i.rename(columns={col_cnpj: 'CNPJ_FUNDO'})

    tab_i = tratar_numericos(tab_i)

    # Tenta encontrar coluna CLASSE
    col_classe = _encontrar_coluna(
        tab_i,
        'CLASSE', 'CLASSE_FUNDO', 'NM_CLASSE',
        'DS_CLASSE', 'TP_CLASSE'
    )
    if col_classe:
        tab_i = tab_i.rename(columns={col_classe: 'CLASSE'})
        tab_i = tab_i[tab_i['CLASSE'].str.upper().str.contains('DUPLICATA|PME', na=False)].copy()
    else:
        print("   [AVISO] Coluna CLASSE não encontrada. Usando todos os fundos.")

    tab_i['CNPJ_FUNDO'] = tab_i['CNPJ_FUNDO'].astype(str).str.strip()

    # ── TAB_II — Sacados ──
    col_cnpj_ii = _encontrar_coluna(
        tab_ii,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj_ii:
        tab_ii = tab_ii.rename(columns={col_cnpj_ii: 'CNPJ_FUNDO'})

    tab_ii = tratar_numericos(tab_ii)
    tab_ii['CNPJ_FUNDO'] = tab_ii['CNPJ_FUNDO'].astype(str).str.strip()

    col_sacado = _encontrar_coluna(tab_ii, 'CNPJ_SACADO', 'CNPJ_CPF_SACADO', 'CD_SACADO', 'CNPJ_DO_SACADO')
    if col_sacado:
        tab_ii = tab_ii.rename(columns={col_sacado: 'CNPJ_SACADO'})

    col_vl_ativo_ii = _encontrar_coluna(
        tab_ii,
        'VL_ATIVO', 'VL_ATIVO_FINANCEIRO', 'VL_DIREITO_CREDITORIO',
        'VL_ATIVO_CARTEIRA', 'VL_CARTEIRA'
    )
    if col_vl_ativo_ii:
        tab_ii = tab_ii.rename(columns={col_vl_ativo_ii: 'VL_ATIVO'})

    if 'CNPJ_SACADO' in tab_ii.columns and 'VL_ATIVO' in tab_ii.columns:
        conc_sac = tab_ii.groupby('CNPJ_FUNDO').agg(
            NUM_SACADOS=('CNPJ_SACADO', 'nunique'),
            CONC_TOP5_SACADOS=('VL_ATIVO', lambda x: round(
                x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
        ).reset_index()
    else:
        print("   [AVISO] TAB_II sem dados suficientes. Pulando concentração de sacados.")
        conc_sac = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB_III — Recompra ──
    col_cnpj_iii = _encontrar_coluna(
        tab_iii,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj_iii:
        tab_iii = tab_iii.rename(columns={col_cnpj_iii: 'CNPJ_FUNDO'})

    tab_iii = tratar_numericos(tab_iii)
    tab_iii['CNPJ_FUNDO'] = tab_iii['CNPJ_FUNDO'].astype(str).str.strip()

    col_recompra = _encontrar_coluna(
        tab_iii,
        'VL_DICRED_ALIEN_CONTAB', 'VL_DICRED_ALIEN', 'VL_RECOMPRA',
        'VL_DIREITO_CREDITORIO_ALIENADO', 'VL_CREDITO_ALIENADO'
    )
    if col_recompra:
        tab_iii = tab_iii.rename(columns={col_recompra: 'VL_DICRED_ALIEN_CONTAB'})

    if 'VL_DICRED_ALIEN_CONTAB' in tab_iii.columns:
        recompra = tab_iii.groupby('CNPJ_FUNDO').agg(
            INDICE_RECOMPRA=('VL_DICRED_ALIEN_CONTAB', 'sum')
        ).reset_index()
    else:
        print("   [AVISO] TAB_III sem dados de recompra. Pulando.")
        recompra = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB_V — PDD ──
    col_cnpj_v = _encontrar_coluna(
        tab_v,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj_v:
        tab_v = tab_v.rename(columns={col_cnpj_v: 'CNPJ_FUNDO'})

    tab_v = tratar_numericos(tab_v)
    tab_v['CNPJ_FUNDO'] = tab_v['CNPJ_FUNDO'].astype(str).str.strip()

    col_pdd = _encontrar_coluna(
        tab_v,
        'VL_PDD', 'VL_PROVISAO', 'VL_PDD_CONTABIL',
        'VL_PROVISAO_PDD', 'VL_PROVISAO_DEVEDORES_DUVIDOSOS'
    )
    if col_pdd:
        tab_v = tab_v.rename(columns={col_pdd: 'PDD'})

    if 'PDD' in tab_v.columns:
        pdd = tab_v.groupby('CNPJ_FUNDO').agg(PDD=('PDD', 'sum')).reset_index()
    elif 'VL_PDD' in tab_v.columns:
        pdd = tab_v.groupby('CNPJ_FUNDO').agg(PDD=('VL_PDD', 'sum')).reset_index()
    else:
        print("   [AVISO] TAB_V sem dados de PDD. Pulando.")
        pdd = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB_VI — Prazo Médio ──
    col_cnpj_vi = _encontrar_coluna(
        tab_vi,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj_vi:
        tab_vi = tab_vi.rename(columns={col_cnpj_vi: 'CNPJ_FUNDO'})

    tab_vi = tratar_numericos(tab_vi)
    tab_vi['CNPJ_FUNDO'] = tab_vi['CNPJ_FUNDO'].astype(str).str.strip()

    col_prazo = _encontrar_coluna(
        tab_vi,
        'PRAZO_MEDIO', 'PRAZO_MEDIO_DIAS', 'PRAZO',
        'PRAZO_MEDIO_CARTEIRA', 'PRAZO_MEDIO_DIAS_CORRIDOS'
    )
    if col_prazo:
        tab_vi = tab_vi.rename(columns={col_prazo: 'PRAZO_MEDIO'})

    if 'PRAZO_MEDIO' in tab_vi.columns:
        prazo = tab_vi.groupby('CNPJ_FUNDO').agg(PRAZO_MEDIO=('PRAZO_MEDIO', 'mean')).reset_index()
    else:
        print("   [AVISO] TAB_VI sem prazo médio. Pulando.")
        prazo = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB_VII — Liquidez ──
    col_cnpj_vii = _encontrar_coluna(
        tab_vii,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj_vii:
        tab_vii = tab_vii.rename(columns={col_cnpj_vii: 'CNPJ_FUNDO'})

    tab_vii = tratar_numericos(tab_vii)
    tab_vii['CNPJ_FUNDO'] = tab_vii['CNPJ_FUNDO'].astype(str).str.strip()

    col_liq = _encontrar_coluna(
        tab_vii,
        'VL_LIQ', 'VL_DISPONIBILIDADES', 'VL_CAIXA',
        'VL_DISPONIVEL', 'VL_DISPONIBILIDADE'
    )
    if col_liq:
        tab_vii = tab_vii.rename(columns={col_liq: 'VL_LIQ'})

    col_tp = _encontrar_coluna(
        tab_vii,
        'VL_TIT_PUBLICO', 'VL_TITULOS_PUBLICOS', 'VL_TITULOS',
        'VL_TITULO_PUBLICO', 'VL_APLICACAO_TITULOS'
    )
    if col_tp:
        tab_vii = tab_vii.rename(columns={col_tp: 'VL_TIT_PUBLICO'})

    if 'VL_LIQ' in tab_vii.columns or 'VL_TIT_PUBLICO' in tab_vii.columns:
        cols_liq = {}
        if 'VL_LIQ' in tab_vii.columns:
            cols_liq['VL_LIQ'] = 'sum'
        if 'VL_TIT_PUBLICO' in tab_vii.columns:
            cols_liq['VL_TIT_PUBLICO'] = 'sum'
        liq = tab_vii.groupby('CNPJ_FUNDO').agg(cols_liq).reset_index()
    else:
        print("   [AVISO] TAB_VII sem dados de liquidez. Pulando.")
        liq = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB_IX — Cedentes ──
    col_cnpj_ix = _encontrar_coluna(
        tab_ix,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj_ix:
        tab_ix = tab_ix.rename(columns={col_cnpj_ix: 'CNPJ_FUNDO'})

    tab_ix = tratar_numericos(tab_ix)
    tab_ix['CNPJ_FUNDO'] = tab_ix['CNPJ_FUNDO'].astype(str).str.strip()

    col_cedente = _encontrar_coluna(
        tab_ix,
        'CNPJ_CEDENTE', 'CNPJ_CPF_CEDENTE', 'CD_CEDENTE',
        'CNPJ_DO_CEDENTE', 'CNPJ_ORIGINADOR'
    )
    if col_cedente:
        tab_ix = tab_ix.rename(columns={col_cedente: 'CNPJ_CEDENTE'})

    col_vl_ix = _encontrar_coluna(
        tab_ix,
        'VL_ATIVO', 'VL_ATIVO_FINANCEIRO', 'VL_DIREITO_CREDITORIO',
        'VL_ATIVO_CARTEIRA', 'VL_CARTEIRA'
    )
    if col_vl_ix:
        tab_ix = tab_ix.rename(columns={col_vl_ix: 'VL_ATIVO'})

    if 'CNPJ_CEDENTE' in tab_ix.columns and 'VL_ATIVO' in tab_ix.columns:
        conc_ced = tab_ix.groupby('CNPJ_FUNDO').agg(
            NUM_CEDENTES=('CNPJ_CEDENTE', 'nunique'),
            CONC_TOP5_CEDENTES=('VL_ATIVO', lambda x: round(
                x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
        ).reset_index()
    else:
        print("   [AVISO] TAB_IX sem dados de cedentes. Pulando.")
        conc_ced = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── MERGE ──
    dfs = [tab_i, conc_sac, recompra, pdd, prazo, liq, conc_ced]
    df = dfs[0]
    for d in dfs[1:]:
        if 'CNPJ_FUNDO' in d.columns:
            df = df.merge(d, on='CNPJ_FUNDO', how='left')

    # ── Métricas derivadas ──
    if 'VL_TOTAL_ATIVO' in df.columns and 'VL_PL' in df.columns:
        df['OVERCOLLATERALIZATION'] = round(
            df['VL_TOTAL_ATIVO'] / df['VL_PL'].replace(0, np.nan), 2
        )
    elif 'VL_PL' in df.columns:
        print("   [AVISO] VL_TOTAL_ATIVO não encontrada. Overcollateralization não calculada.")

    if 'VL_LIQ' in df.columns and 'VL_PL' in df.columns:
        df['PCT_LIQUIDEZ'] = round(
            df['VL_LIQ'] / df['VL_PL'].replace(0, np.nan) * 100, 2
        )

    if 'PDD' in df.columns and 'VL_PL' in df.columns:
        df['PDD_PCT'] = round(
            df['PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2
        )
    elif 'VL_PDD' in df.columns and 'VL_PL' in df.columns:
        df['PDD_PCT'] = round(
            df['VL_PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2
        )

    if 'INDICE_RECOMPRA' in df.columns and 'VL_PL' in df.columns:
        df['RECOMPRA_PCT'] = round(
            df['INDICE_RECOMPRA'] / df['VL_PL'].replace(0, np.nan) * 100, 2
        )

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
