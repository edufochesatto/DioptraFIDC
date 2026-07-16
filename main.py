import pandas as pd
import json
import numpy as np
from pathlib import Path

DOCS_DIR = Path("docs")
DATA_DIR = Path("data")
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

print("=" * 60)
print("DIOPTRA FIDC")
print("=" * 60)

# Procura CSV - SOMENTE tab_I (exclui tab_II, tab_III etc)
print(f"\n[1/2] Procurando tab_I em {DATA_DIR}...")
todos = sorted(DATA_DIR.glob("*tab_I*"))
arquivos = [f for f in todos if "_tab_I_" in f.name or f.name.endswith("_tab_I")]
# Se ainda nao achou, tenta outro padrao
if not arquivos:
    arquivos = [f for f in todos if not any(x in f.name.upper() for x in ["_TAB_II", "_TAB_III", "_TAB_IV", "_TAB_V", "_TAB_VI", "_TAB_VII", "_TAB_IX", "_TAB_X"])]

if not arquivos:
    print("  ERRO: Nenhum arquivo tab_I encontrado!")
    print(f"  Arquivos com tab_I: {[f.name for f in todos]}")
    exit(1)

arquivo = arquivos[0]
print(f"  Lendo {arquivo.name}...")

try:
    df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
except:
    try:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, sep=';', dtype=str, low_memory=False)

print(f"  {len(df)} linhas, {len(df.columns)} colunas")
print(f"  Primeiras colunas: {list(df.columns[:8])}")

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
print(f"  Colunas mapeadas: {list(rename_map.keys())}")

# Converte ativo para numero
if 'VL_ATIVO' in df.columns:
    df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    print(f"  VL_ATIVO encontrado! Max: R$ {df['VL_PL'].max():.2f}")
else:
    print(f"  ERRO: coluna VL_ATIVO nao encontrada!")
    print(f"  Colunas disponiveis: {[c for c in df.columns if 'ATIVO' in c.upper() or 'PL' in c.upper()]}")
    exit(1)

# Remove duplicatas
if 'CNPJ_FUNDO' in df.columns:
    antes = len(df)
    df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
    print(f"  Duplicatas removidas: {antes - len(df)}")

# Converte reais para milhoes
if df['VL_PL'].max() > 1e8:
    df['VL_PL'] = df['VL_PL'] / 1e6
    print(f"  PL convertido para milhoes: max = R$ {df['VL_PL'].max():.2f} MM")

# Filtra PLs negativos e absurdos
antes = len(df)
df = df[df['VL_PL'].apply(lambda x: isinstance(x, (int, float)) and x >= 0 and x < 500000)]
print(f"  Fundos com PL valido: {len(df)} (removidos {antes - len(df)})")
df = df.replace([np.inf, -np.inf], np.nan)
df = df.where(pd.notna(df), None)

# Colunas padrao
df['PDD_PCT'] = 0.0
df['RECOMPRA_PCT'] = 0.0
df['RENTABILIDADE'] = 0.0
df['NUM_SACADOS'] = 0
df['NUM_CEDENTES'] = 0

# Ordena por PL decrescente
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

print(f"\n  TOP 10 FUNDOS (por PL):")
for f in fundos[:10]:
    nome = (f.get('DENOMINACAO_SOCIAL', '') or '')[:55]
    pl = f.get('VL_PL', 0)
    print(f"  R$ {pl:>10.2f} MM | {nome}")

print(f"\n  TOTAL: {len(fundos)} fundos")
pl_total = sum(f.get('VL_PL', 0) for f in fundos)
print(f"  PL TOTAL: R$ {pl_total:,.2f} MM")
print("\n" + "=" * 60)
print("CONCLUIDO!")
print("=" * 60)
