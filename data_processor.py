"""
data_processor.py — Lê o CSV tab_I do FIDC baixado da CVM.
Usa as colunas exatas do layout CVM.
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
    """Le o arquivo tab_I e retorna DataFrame padronizado."""
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        print(f"  Pasta {raw_path} nao encontrada!")
        return pd.DataFrame()

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

    # Mapeia as colunas do layout CVM para o padrao
    rename_map = {}
    for col in df.columns:
        col_clean = col.strip().upper()
        if col_clean == 'CNPJ_FUNDO_CLASSE':
            rename_map[col] = 'CNPJ_FUNDO'
        elif col_clean == 'DENOM_SOCIAL':
            rename_map[col] = 'DENOMINACAO_SOCIAL'
        elif col_clean == 'TAB_I_VL_ATIVO':
            rename_map[col] = 'VL_ATIVO'

    df = df.rename(columns=rename_map)
    print(f"  Colunas mapeadas: {list(rename_map.keys())}")

    # Converte TAB_I_VL_ATIVO para numero (vai servir como PL)
    if 'VL_ATIVO' in df.columns:
        df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    else:
        df['VL_PL'] = 0.0

    # Remove duplicatas de CNPJ
    if 'CNPJ_FUNDO' in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
        print(f"  Removidas {antes - len(df)} duplicatas de CNPJ")

    # Inicializa colunas que nao estao no tab_I
    for col in ['PDD_PCT', 'RECOMPRA_PCT', 'RENTABILIDADE']:
        df[col] = 0.0
    for col in ['NUM_SACADOS', 'NUM_CEDENTES']:
        df[col] = 0

    # Ordena por PL decrescente
    if 'VL_PL' in df.columns:
        df = df.sort_values('VL_PL', ascending=False)

    print(f"  {len(df)} fundos processados")
    return df
