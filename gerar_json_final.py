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
print("GERADOR DE dados.json - DADOS REAIS DA CVM")
print("=" * 60)

# Procura o CSV
arquivos = list(DATA_DIR.glob("*tab_I*"))
if not arquivos:
    print("ERRO: Nenhum arquivo tab_I encontrado em data/")
    exit(1)

arquivo = arquivos[0]
print(f"\n[1/3] Lendo {arquivo.name}...")

df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
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
print(f"\n[2/3] Processando {len(df)} fundos...")

# Converte ativo para numerico
if 'VL_ATIVO' in df.columns:
    df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
else:
    print("  ERRO: coluna VL_ATIVO nao encontrada!")
    print(f"  Colunas disponiveis: {list(df.columns[:10])}")
    exit(1)

print(f"  PL max (reais): R$ {df['VL_PL'].max():.2f}")

# Remove duplicatas
if 'CNPJ_FUNDO' in df.columns:
    antes = len(df)
    df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
    print(f"  Duplicatas removidas: {antes - len(df)}")

# Converte para milhoes
if df['VL_PL'].max() > 1e8:
    df['VL_PL'] = df['VL_PL'] / 1e6
    print(f"  PL convertido para milhoes: max = R$ {df['VL_PL'].max():.2f} MM")

# Filtra PLs negativos e absurdos
antes = len(df)
df = df[df['VL_PL'].apply(lambda x: isinstance(x, (int, float)) and x >= 0 and x < 500000)]
print(f"  Fundos com PL > 0 e < 500bi: {len(df)} (removidos {antes - len(df)})")

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

print(f"\n[3/3] Salvando docs/dados.json com {len(fundos)} fundos...")

with open(DOCS_DIR / "dados.json", "w") as f:
    json.dump({
        "fundos": fundos,
        "metricas": {},
        "gerado_em": "2026-07-16",
        "versao": "Julho/2026"
    }, f, indent=2, ensure_ascii=False)

print(f"  Arquivo salvo: {DOCS_DIR / 'dados.json'}")

# Mostra amostra
print(f"\n  TOP 10 FUNDOS (por PL):")
print(f"  {'PL (R$ MM)':>12} | {'CNPJ':<20} | {'NOME DO FUNDO'}")
print(f"  {'-'*12} | {'-'*20} | {'-'*50}")
for f in fundos[:10]:
    pl = f.get('VL_PL', 0)
    cnpj = f.get('CNPJ_FUNDO', '')
    nome = (f.get('DENOMINACAO_SOCIAL', '') or '')[:48]
    print(f"  {pl:>10.2f} MM | {cnpj:<18} | {nome}")

print(f"\n  TOTAL: {len(fundos)} fundos")
print(f"  PL TOTAL: R$ {sum(f.get('VL_PL', 0) for f in fundos):.2f} MM")
print("\n" + "=" * 60)
print("PRONTO! Faça upload do docs/dados.json no GitHub.")
print("=" * 60)
