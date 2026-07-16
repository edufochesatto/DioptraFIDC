import pandas as pd
import json
import numpy as np
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

DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("DIOPTRA FIDC")
print("=" * 60)

# Procura CSV
data_path = Path("data")
arquivos = list(data_path.glob("*tab_I*"))
if not arquivos:
    print("  ERRO: Nenhum arquivo tab_I encontrado!")
    exit(1)

arquivo = arquivos[0]
print(f"\n[1/2] Lendo {arquivo.name}...")

try:
    df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
except:
    try:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, sep=';', dtype=str, low_memory=False)

print(f"  {len(df)} linhas, {len(df.columns)} colunas")

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

# Converte ativo
if 'VL_ATIVO' in df.columns:
    df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
else:
    df['VL_PL'] = 0.0

# Remove duplicatas
if 'CNPJ_FUNDO' in df.columns:
    df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')

# Converte reais para milhoes
if df['VL_PL'].max() > 1e8:
    df['VL_PL'] = df['VL_PL'] / 1e6
    print(f"  PL convertido para milhoes: max = {df['VL_PL'].max():.2f} MM")

# Filtra PLs negativos e absurdos
df = df[df['VL_PL'].apply(lambda x: isinstance(x, (int, float)) and x >= 0 and x < 500000)]
df = df.replace([np.inf, -np.inf], np.nan)
df = df.where(pd.notna(df), None)

# Colunas padrao
df['PDD_PCT'] = 0.0
df['RECOMPRA_PCT'] = 0.0
df['RENTABILIDADE'] = 0.0
df['NUM_SACADOS'] = 0
df['NUM_CEDENTES'] = 0

# Ordena por PL
df = df.sort_values('VL_PL', ascending=False)

# Converte para lista
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

print(f"\n[2/2] Salvando {len(fundos)} fundos em docs/dados.json...")

with open(DOCS_DIR / "dados.json", "w") as f:
    json.dump({
        "fundos": fundos,
        "metricas": {},
        "gerado_em": "2026-07-16",
        "versao": "Julho/2026"
    }, f, indent=2, ensure_ascii=False)

# Amostra
if fundos:
    print(f"\n  Top 5 fundos:")
    for f in fundos[:5]:
        nome = (f.get('DENOMINACAO_SOCIAL', '') or '')[:60]
        pl = f.get('VL_PL', 0)
        print(f"    R$ {pl:>10.2f} MM | {nome}")

print(f"\n  Total: {len(fundos)} fundos")
print("\n" + "=" * 60)
print("CONCLUIDO!")
print("=" * 60)
