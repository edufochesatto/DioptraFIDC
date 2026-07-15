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
        for col in df.columns:
            if col.strip().upper() == nome.upper():
                return col
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
    print(f"   [DEBUG] Colunas ({len(df.columns)}): {list(df.columns)}")
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
    # ── TAB I ──
    col_cnpj = _encontrar_coluna(
        tab_i,
        'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CNPJ_CLASSE',
        'CD_CNPJ_FUNDO', 'CD_FUNDO'
    )
    if col_cnpj is None:
        print(f"\n❌ CNPJ não encontrada. Colunas: {list(tab_i.columns)}")
        raise KeyError("Coluna de identificação do fundo não encontrada na TAB_I")
    print(f"   [DEBUG] CNPJ encontrada como: '{col_cnpj}'")
    tab_i = tab_i.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_i = tratar_numericos(tab_i)

    col_classe = _encontrar_coluna(
        tab_i, 'CLASSE', 'CLASSE_FUNDO', 'NM_CLASSE', 'DS_CLASSE', 'TP_CLASSE'
    )
    if col_classe:
        tab_i = tab_i.rename(columns={col_classe: 'CLASSE'})
        mask = tab_i['CLASSE'].str.upper().str.contains('DUPLICATA|PME', na=False)
        tab_i = tab_i[mask].copy()
    else:
        print("   [AVISO] CLASSE não encontrada. Usando todos os fundos.")

    tab_i['CNPJ_FUNDO'] = tab_i['CNPJ_FUNDO'].astype(str).str.strip()

    # ── TAB II — Sacados ──
    col_cnpj = _encontrar_coluna(
        tab_ii, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj:
        tab_ii = tab_ii.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_ii = tratar_numericos(tab_ii)
    tab_ii['CNPJ_FUNDO'] = tab_ii['CNPJ_FUNDO'].astype(str).str.strip()

    col_sac = _encontrar_coluna(
        tab_ii, 'CNPJ_SACADO', 'CNPJ_CPF_SACADO', 'CD_SACADO', 'CNPJ_DO_SACADO'
    )
    if col_sac:
        tab_ii = tab_ii.rename(columns={col_sac: 'CNPJ_SACADO'})
    col_vl = _encontrar_coluna(
        tab_ii, 'VL_ATIVO', 'VL_ATIVO_FINANCEIRO', 'VL_DIREITO_CREDITORIO',
        'VL_ATIVO_CARTEIRA', 'VL_CARTEIRA'
    )
    if col_vl:
        tab_ii = tab_ii.rename(columns={col_vl: 'VL_ATIVO'})

    if 'CNPJ_SACADO' in tab_ii.columns and 'VL_ATIVO' in tab_ii.columns:
        tab_ii['VL_ATIVO'] = pd.to_numeric(tab_ii['VL_ATIVO'], errors='coerce').fillna(0)
        conc_sac = tab_ii.groupby('CNPJ_FUNDO').agg(
            NUM_SACADOS=('CNPJ_SACADO', 'nunique'),
            CONC_TOP5_SACADOS=('VL_ATIVO', lambda x: round(
                x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
        ).reset_index()
    else:
        print("   [AVISO] TAB_II sem dados. Pulando sacados.")
        conc_sac = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB III — Recompra ──
    col_cnpj = _encontrar_coluna(
        tab_iii, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj:
        tab_iii = tab_iii.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_iii = tratar_numericos(tab_iii)
    tab_iii['CNPJ_FUNDO'] = tab_iii['CNPJ_FUNDO'].astype(str).str.strip()

    col_rec = _encontrar_coluna(
        tab_iii, 'VL_DICRED_ALIEN_CONTAB', 'VL_DICRED_ALIEN', 'VL_RECOMPRA',
        'VL_DIREITO_CREDITORIO_ALIENADO', 'VL_CREDITO_ALIENADO'
    )
    if col_rec:
        tab_iii = tab_iii.rename(columns={col_rec: 'VL_DICRED_ALIEN_CONTAB'})

    if 'VL_DICRED_ALIEN_CONTAB' in tab_iii.columns:
        tab_iii['VL_DICRED_ALIEN_CONTAB'] = pd.to_numeric(
            tab_iii['VL_DICRED_ALIEN_CONTAB'], errors='coerce').fillna(0)
        recompra = tab_iii.groupby('CNPJ_FUNDO').agg(
            INDICE_RECOMPRA=('VL_DICRED_ALIEN_CONTAB', 'sum')
        ).reset_index()
    else:
        print("   [AVISO] TAB_III sem recompra. Pulando.")
        recompra = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB V — PDD ──
    col_cnpj = _encontrar_coluna(
        tab_v, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj:
        tab_v = tab_v.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_v = tratar_numericos(tab_v)
    tab_v['CNPJ_FUNDO'] = tab_v['CNPJ_FUNDO'].astype(str).str.strip()

    col_pdd = _encontrar_coluna(
        tab_v, 'VL_PDD', 'VL_PROVISAO', 'VL_PDD_CONTABIL',
        'VL_PROVISAO_PDD', 'VL_PROVISAO_DEVEDORES_DUVIDOSOS'
    )
    if col_pdd:
        tab_v = tab_v.rename(columns={col_pdd: 'PDD'})

    col_pdd_val = 'PDD' if col_pdd else ('VL_PDD' if 'VL_PDD' in tab_v.columns else None)
    if col_pdd_val:
        tab_v[col_pdd_val] = pd.to_numeric(tab_v[col_pdd_val], errors='coerce').fillna(0)
        pdd = tab_v.groupby('CNPJ_FUNDO').agg(PDD=(col_pdd_val, 'sum')).reset_index()
    else:
        print("   [AVISO] TAB_V sem PDD. Pulando.")
        pdd = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB VI — Prazo Médio ──
    col_cnpj = _encontrar_coluna(
        tab_vi, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj:
        tab_vi = tab_vi.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_vi = tratar_numericos(tab_vi)
    tab_vi['CNPJ_FUNDO'] = tab_vi['CNPJ_FUNDO'].astype(str).str.strip()

    col_prazo = _encontrar_coluna(
        tab_vi, 'PRAZO_MEDIO', 'PRAZO_MEDIO_DIAS', 'PRAZO',
        'PRAZO_MEDIO_CARTEIRA', 'PRAZO_MEDIO_DIAS_CORRIDOS'
    )
    if col_prazo:
        tab_vi = tab_vi.rename(columns={col_prazo: 'PRAZO_MEDIO'})

    if 'PRAZO_MEDIO' in tab_vi.columns:
        tab_vi['PRAZO_MEDIO'] = pd.to_numeric(tab_vi['PRAZO_MEDIO'], errors='coerce').fillna(0)
        prazo = tab_vi.groupby('CNPJ_FUNDO').agg(PRAZO_MEDIO=('PRAZO_MEDIO', 'mean')).reset_index()
    else:
        print("   [AVISO] TAB_VI sem prazo médio. Pulando.")
        prazo = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB VII — Liquidez ──
    col_cnpj = _encontrar_coluna(
        tab_vii, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj:
        tab_vii = tab_vii.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_vii = tratar_numericos(tab_vii)
    tab_vii['CNPJ_FUNDO'] = tab_vii['CNPJ_FUNDO'].astype(str).str.strip()

    col_liq = _encontrar_coluna(
        tab_vii, 'VL_LIQ', 'VL_DISPONIBILIDADES', 'VL_CAIXA',
        'VL_DISPONIVEL', 'VL_DISPONIBILIDADE'
    )
    if col_liq:
        tab_vii = tab_vii.rename(columns={col_liq: 'VL_LIQ'})
    col_tp = _encontrar_coluna(
        tab_vii, 'VL_TIT_PUBLICO', 'VL_TITULOS_PUBLICOS', 'VL_TITULOS',
        'VL_TITULO_PUBLICO', 'VL_APLICACAO_TITULOS'
    )
    if col_tp:
        tab_vii = tab_vii.rename(columns={col_tp: 'VL_TIT_PUBLICO'})

    agg_liq = {}
    if 'VL_LIQ' in tab_vii.columns:
        tab_vii['VL_LIQ'] = pd.to_numeric(tab_vii['VL_LIQ'], errors='coerce').fillna(0)
        agg_liq['VL_LIQ'] = 'sum'
    if 'VL_TIT_PUBLICO' in tab_vii.columns:
        tab_vii['VL_TIT_PUBLICO'] = pd.to_numeric(tab_vii['VL_TIT_PUBLICO'], errors='coerce').fillna(0)
        agg_liq['VL_TIT_PUBLICO'] = 'sum'
    if agg_liq:
        liq = tab_vii.groupby('CNPJ_FUNDO').agg(agg_liq).reset_index()
    else:
        print("   [AVISO] TAB_VII sem liquidez. Pulando.")
        liq = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── TAB IX — Cedentes ──
    col_cnpj = _encontrar_coluna(
        tab_ix, 'CNPJ_FUNDO', 'CNPJ_DO_FUNDO', 'CNPJ_FUNDO_',
        'CNPJ_FUNDO_CLASSE', 'CD_CNPJ_FUNDO'
    )
    if col_cnpj:
        tab_ix = tab_ix.rename(columns={col_cnpj: 'CNPJ_FUNDO'})
    tab_ix = tratar_numericos(tab_ix)
    tab_ix['CNPJ_FUNDO'] = tab_ix['CNPJ_FUNDO'].astype(str).str.strip()

    col_ced = _encontrar_coluna(
        tab_ix, 'CNPJ_CEDENTE', 'CNPJ_CPF_CEDENTE', 'CD_CEDENTE',
        'CNPJ_DO_CEDENTE', 'CNPJ_ORIGINADOR'
    )
    if col_ced:
        tab_ix = tab_ix.rename(columns={col_ced: 'CNPJ_CEDENTE'})
    col_vl_ix = _encontrar_coluna(
        tab_ix, 'VL_ATIVO', 'VL_ATIVO_FINANCEIRO', 'VL_DIREITO_CREDITORIO',
        'VL_ATIVO_CARTEIRA', 'VL_CARTEIRA'
    )
    if col_vl_ix:
        tab_ix = tab_ix.rename(columns={col_vl_ix: 'VL_ATIVO'})

    if 'CNPJ_CEDENTE' in tab_ix.columns and 'VL_ATIVO' in tab_ix.columns:
        tab_ix['VL_ATIVO'] = pd.to_numeric(tab_ix['VL_ATIVO'], errors='coerce').fillna(0)
        conc_ced = tab_ix.groupby('CNPJ_FUNDO').agg(
            NUM_CEDENTES=('CNPJ_CEDENTE', 'nunique'),
            CONC_TOP5_CEDENTES=('VL_ATIVO', lambda x: round(
                x.nlargest(5).sum() / x.sum() * 100, 2) if x.sum() > 0 else 0)
        ).reset_index()
    else:
        print("   [AVISO] TAB_IX sem cedentes. Pulando.")
        conc_ced = pd.DataFrame({'CNPJ_FUNDO': tab_i['CNPJ_FUNDO'].unique()})

    # ── MERGE ──
    dfs = [tab_i, conc_sac, recompra, pdd, prazo, liq, conc_ced]
    df = dfs[0]
    for d in dfs[1:]:
        if 'CNPJ_FUNDO' in d.columns:
            df = df.merge(d, on='CNPJ_FUNDO', how='left')

    # ── Métricas derivadas ──
    if 'VL_TOTAL_ATIVO' in df.columns and 'VL_PL' in df.columns:
        df['VL_TOTAL_ATIVO'] = pd.to_numeric(df['VL_TOTAL_ATIVO'], errors='coerce').fillna(0)
        df['OVERCOLLATERALIZATION'] = round(
            df['VL_TOTAL_ATIVO'] / df['VL_PL'].replace(0, np.nan), 2
        )
    else:
        print("   [AVISO] OVERCOLLATERALIZATION não calculada (falta VL_TOTAL_ATIVO).")

    if 'VL_LIQ' in df.columns and 'VL_PL' in df.columns:
        df['PCT_LIQUIDEZ'] = round(
            df['VL_LIQ'] / df['VL_PL'].replace(0, np.nan) * 100, 2
        )

    if 'PDD' in df.columns and 'VL_PL' in df.columns:
        df['PDD_PCT'] = round(
            df['PDD'] / df['VL_PL'].replace(0, np.nan) * 100, 2
        )
    elif 'VL_PDD' in df.columns and 'VL_PL' in df.columns:
        df['VL_PDD'] = pd.to_numeric(df['VL_PDD'], errors='coerce').fillna(0)
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
