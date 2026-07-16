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

def processar_dados_cvm(data_dir):
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"  Pasta {data_path} nao encontrada!")
        return pd.DataFrame()

    # Procura arquivo tab_I na pasta data/
    arquivos = list(data_path.glob("*tab_I*"))
    if not arquivos:
        print(f"  Nenhum arquivo tab_I encontrado em {data_path}")
        return pd.DataFrame()

    arquivo = arquivos[0]
    print(f"  Lendo {arquivo.name}...")

    try:
        df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)

    print(f"  {len(df)} linhas, {len(df.columns)} colunas")

    rename_map = {}
    for col in df.columns:
        c = col.strip().upper()
        if c == 'CNPJ_FUNDO_CLASSE':
            rename_map[col] = 'CNPJ_FUNDO'
        elif c == 'DENOM_SOCIAL':
            rename_map[col] = 'DENOMINACAO_SOCIAL'
        elif c == 'TAB_I_VL_ATIVO':
            rename_map[col] = 'VL_ATIVO'

    df = df.rename(columns=rename_map)

    if 'VL_ATIVO' in df.columns:
        df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    else:
        df['VL_PL'] = 0.0

    if 'CNPJ_FUNDO' in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
        print(f"  Removidas {antes - len(df)} duplicatas")

    df['PDD_PCT'] = 0.0
    df['RECOMPRA_PCT'] = 0.0
    df['RENTABILIDADE'] = 0.0
    df['NUM_SACADOS'] = 0
    df['NUM_CEDENTES'] = 0

    if 'VL_PL' in df.columns:
        df = df.sort_values('VL_PL', ascending=False)

    print(f"  {len(df)} fundos processados")
    return df
