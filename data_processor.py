"""
data_processor.py — Lê o CSV tab_I do FIDC baixado da CVM.
"""
import pandas as pd
from pathlib import Path

COLUNAS_CVM = {
    'CNPJ_FUNDO': 'CNPJ_FUNDO',
    'DENOM_SOCIAL': 'DENOMINACAO_SOCIAL',
    'VL_PAT_LIQ': 'VL_PL',
    'VL_PL': 'VL_PL',
    'PRAZO_MEDIO': 'PRAZO_MEDIO',
    'PRAZO_MED': 'PRAZO_MEDIO',
    'VL_RENTAB': 'RENTABILIDADE',
    'VL_PDD': 'PDD_PCT',
    'PDD_PCT': 'PDD_PCT',
    'VL_RECOMPRA': 'RECOMPRA_PCT',
    'RECOMPRA_PCT': 'RECOMPRA_PCT',
    'QUANTIDADE_CEDENTES': 'NUM_CEDENTES',
    'NUM_CEDENTES': 'NUM_CEDENTES',
    'QUANTIDADE_SACADOS': 'NUM_SACADOS',
    'NUM_SACADOS': 'NUM_SACADOS',
    'CLASSE': 'CLASSE',
    'CLASSE_UNICA': 'CLASSE',
}

def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def processar_dados_cvm(raw_dir):
    """Lê o arquivo tab_I e retorna DataFrame padronizado."""
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        print(f"  ⚠ Pasta {raw_path} não encontrada!")
        return pd.DataFrame()

    arquivos = list(raw_path.glob("*tab_I*"))
    if not arquivos:
        print(f"  ⚠ Nenhum arquivo tab_I encontrado em {raw_path}")
        print(f"  Arquivos encontrados: {[f.name for f in raw_path.glob('*')]}")
        return pd.DataFrame()

    arquivo = arquivos[0]
    print(f"  Lendo {arquivo.name}...")

    try:
        df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)

    print(f"  → {len(df)} linhas, {len(df.columns)} colunas")
    print(f"  Colunas: {list(df.columns[:20])}")

    rename_map = {}
    for col in df.columns:
        col_upper = col.strip().upper()
        if col_upper in COLUNAS_CVM:
            rename_map[col] = COLUNAS_CVM[col_upper]

    if rename_map:
        df = df.rename(columns=rename_map)
        print(f"  Colunas mapeadas: {rename_map}")

    for col in ['VL_PL', 'PRAZO_MEDIO', 'RENTABILIDADE', 'PDD_PCT', 'RECOMPRA_PCT', 'NUM_CEDENTES', 'NUM_SACADOS']:
        if col in df.columns:
            df[col] = df[col].apply(limpar_valor)

    if 'CNPJ_FUNDO' in df.columns:
        df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')

    if 'VL_PL' in df.columns:
        df = df.sort_values('VL_PL', ascending=False)

    print(f"  ✅ {len(df)} fundos processados")
    return df
