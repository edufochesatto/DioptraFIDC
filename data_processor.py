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

    arquivos = list(data_path.glob("*tab_I*"))
    if not arquivos:
        print(f"  Nenhum arquivo tab_I encontrado")
        return pd.DataFrame()

    arquivo = arquivos[0]
    print(f"  Lendo {arquivo.name}...")

    # Tenta latin1 primeiro, depois utf-8
    try:
        df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
    except:
        try:
            df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)
        except:
            df = pd.read_csv(arquivo, sep=';', dtype=str, low_memory=False)

    print(f"  {len(df)} linhas, {len(df.columns)} colunas")
    print(f"  Colunas: {[c for c in df.columns[:5]]}")

    # Mapeia colunas (maiusculo ou minusculo)
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
    print(f"  Mapeamento: {rename_map}")

    # Converte ativo para numerico
    if 'VL_ATIVO' in df.columns:
        df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    else:
        print(f"  AVISO: coluna VL_ATIVO nao encontrada!")
        df['VL_PL'] = 0.0

    # Remove duplicatas
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
    if 'VL_PL' in df.columns:
        print(f"  PL max: {df['VL_PL'].max():.2f} (reais)")
    return df
