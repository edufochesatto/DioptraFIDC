"""
data_processor.py — Lê o CSV tab_I do FIDC baixado da CVM.
Usa as colunas reais do layout CVM.
"""
import pandas as pd
from pathlib import Path

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
        print(f"  Pasta {raw_path} nao encontrada!")
        return pd.DataFrame()

    # Procura arquivo tab_I
    arquivos = list(raw_path.glob("*tab_I*"))
    if not arquivos:
        print(f"  Nenhum arquivo tab_I encontrado em {raw_path}")
        return pd.DataFrame()

    arquivo = arquivos[0]
    print(f"  Lendo {arquivo.name}...")

    try:
        df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)

    print(f"  {len(df)} linhas, {len(df.columns)} colunas")
    print(f"  Primeiras colunas: {list(df.columns[:15])}")

    # Renomeia colunas do layout CVM para o padrao
    rename_map = {}
    for col in df.columns:
        col_upper = col.strip().upper().replace(' ', '_')
        if col_upper == 'CNPJ_FUNDO_CLASSE':
            rename_map[col] = 'CNPJ_FUNDO'
        elif col_upper == 'DENOM_SOCIAL':
            rename_map[col] = 'DENOMINACAO_SOCIAL'
        elif col_upper == 'TAB_I_VL_ATIVO':
            rename_map[col] = 'VL_ATIVO'
        elif col_upper in ['CLASSE', 'CLASSE_UNICA']:
            rename_map[col] = 'CLASSE'

    df = df.rename(columns=rename_map)

    # Converte TAB_I_VL_ATIVO para numerico (vai servir como PL)
    if 'VL_ATIVO' in df.columns:
        df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    else:
        df['VL_PL'] = 0.0

    # Remove duplicatas de CNPJ
    if 'CNPJ_FUNDO' in df.columns:
        df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')

    # Colunas que nao temos no tab_I (inicializa como 0)
    df['PDD_PCT'] = 0.0
    df['RECOMPRA_PCT'] = 0.0
    df['RENTABILIDADE'] = 0.0
    df['NUM_SACADOS'] = 0
    df['NUM_CEDENTES'] = 0

    # Ordena por PL decrescente
    if 'VL_PL' in df.columns:
        df = df.sort_values('VL_PL', ascending=False)

    print(f"  {len(df)} fundos processados")
    return df
