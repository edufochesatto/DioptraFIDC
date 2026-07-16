import pandas as pd
import json
import numpy as np
from pathlib import Path

DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

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

def main():
    print("=" * 60)
    print("DIOPTRA FIDC")
    print("=" * 60)

    print("\n[1/2] Lendo CSV da pasta data/...")

    # Procura o arquivo tab_I
    data_path = Path("data")
    arquivos = list(data_path.glob("*tab_I*"))
    if not arquivos:
        print("  ERRO: Nenhum arquivo tab_I encontrado em data/")
        print(f"  Arquivos encontrados: {[f.name for f in data_path.glob('*')]}")
        return

    arquivo = arquivos[0]
    print(f"  Lendo {arquivo.name}...")

    # Le o CSV
    try:
        df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)

    print(f"  {len(df)} linhas, {len(df.columns)} colunas")
    print(f"  Colunas: {list(df.columns[:10])}")

    # Renomeia colunas
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

    # Converte ativo para PL
    if 'VL_ATIVO' in df.columns:
        df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    else:
        df['VL_PL'] = 0.0

    # Remove duplicatas
    if 'CNPJ_FUNDO' in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
        print(f"  Removidas {antes - len(df)} duplicatas de CNPJ")

    # Converte para milhoes
    if df['VL_PL'].max() > 1e8:
        df['VL_PL'] = df['VL_PL'] / 1e6
        print(f"  PL convertido de reais para milhoes")

    # Filtra PLs negativos e absurdos
    df = df[df['VL_PL'].apply(lambda x: isinstance(x, (int, float)) and x >= 0 and x < 500000)]
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.where(pd.notna(df), None)

    # Colunas que nao existem no tab_I
    df['PDD_PCT'] = 0.0
    df['RECOMPRA_PCT'] = 0.0
    df['RENTABILIDADE'] = 0.0
    df['NUM_SACADOS'] = 0
    df['NUM_CEDENTES'] = 0

    # Ordena por PL decrescente
    df = df.sort_values('VL_PL', ascending=False)

    # Converte para lista de dicionarios
    fundos = []
    for _, row in df.iterrows():
        d = {}
        for col in df.columns:
            val = row[col]
            if isinstance(val, (np.integer,)):
                d[col] = int(val)
            elif isinstance(val, (np.floating,)):
                d[col] = float(val) if not pd.isna(val) else 0.0
            elif isinstance(val, str):
                d[col] = val.strip()
            else:
                d[col] = val
        fundos.append(d)

    print(f"\n[2/2] Salvando dados.json com {len(fundos)} fundos...")

    # Salva
    with open(DOCS_DIR / "dados.json", "w") as f:
        json.dump({
            "fundos": fundos,
            "metricas": {},
            "gerado_em": "2026-07-16",
            "versao": "Julho/2026"
        }, f, indent=2, ensure_ascii=False)

    # Mostra exemplos
    if fundos:
        print(f"\n  Primeiros 3 fundos:")
        for f in fundos[:3]:
            nome = f.get('DENOMINACAO_SOCIAL', '')[:60]
            pl = f.get('VL_PL', 0)
            print(f"    - {pl:.2f} MM | {nome}")

    print("\n" + "=" * 60)
    print("CONCLUIDO!")
    print("=" * 60)

if __name__ == "__main__":
    main()
