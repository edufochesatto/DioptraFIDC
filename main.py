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

print(f"\n[1/2] Buscando arquivo tab_I em {DATA_DIR}...")

# Estrategia 1: busca EXATA por _tab_I_ (com underscore dos dois lados)
arquivos = sorted(DATA_DIR.glob("*_tab_I_*"))
print(f"  Busca _tab_I_: {[f.name for f in arquivos]}")

# Estrategia 2: se nao achou, busca todos com tab_I mas sem tab_III/tab_II etc
if not arquivos:
    todos = list(DATA_DIR.glob("*tab_I*"))
    arquivos = [f for f in todos if not any(
        x in f.name.upper() for x in 
        ['_TAB_II', '_TAB_III', '_TAB_IV', '_TAB_V', '_TAB_VI', '_TAB_VII', '_TAB_IX', '_TAB_X']
    )]
    print(f"  Busca filtrada tab_I: {[f.name for f in arquivos]}")

# Estrategia 3: varre TODOS os CSVs e testa qual tem VL_ATIVO
if not arquivos:
    print("  Busca exata falhou. Varrendo todos os CSVs...")
    for f in sorted(DATA_DIR.glob("*.csv")):
        try:
            teste = pd.read_csv(f, encoding='latin1', sep=';', nrows=5, dtype=str, low_memory=False)
            for col in teste.columns:
                if 'VL_ATIVO' in col.upper() or 'ATIVO' in col.upper():
                    # Tem coluna de ativo! Pode ser o tab_I
                    arquivos = [f]
                    print(f"  Encontrado: {f.name} (tem coluna {col})")
                    break
        except:
            pass
        if arquivos:
            break

if not arquivos:
    print("  ERRO FATAL: Nenhum arquivo com dados de ativo encontrado!")
    print(f"  Arquivos em data/: {[f.name for f in DATA_DIR.glob('*')]}")
    exit(1)

arquivo = arquivos[0]
print(f"\n  Lendo {arquivo.name}...")

try:
    df = pd.read_csv(arquivo, encoding='latin1', sep=';', dtype=str, low_memory=False)
except:
    try:
        df = pd.read_csv(arquivo, encoding='utf-8', sep=';', dtype=str, low_memory=False)
    except:
        df = pd.read_csv(arquivo, sep=';', dtype=str, low_memory=False)

print(f"  {len(df)} linhas, {len(df.columns)} colunas")
print(f"  Colunas originais: {list(df.columns[:8])}")

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
    # Tb tenta minusculo
    if col.strip() == 'cnpj_fundo_classe':
        rename_map[col] = 'CNPJ_FUNDO'
    elif col.strip() == 'denom_social':
        rename_map[col] = 'DENOMINACAO_SOCIAL'
    elif col.strip() == 'tab_i_vl_ativo':
        rename_map[col] = 'VL_ATIVO'

df = df.rename(columns=rename_map)

# Procura VL_ATIVO com qualquer nome parecido
if 'VL_ATIVO' not in df.columns:
    for col in df.columns:
        if 'VL_ATIVO' in col.upper() or ('ATIVO' in col.upper() and 'TAB_I' in col.upper()):
            df['VL_ATIVO'] = df[col]
            print(f"  Usando coluna {col} como VL_ATIVO")
            break

if 'VL_ATIVO' in df.columns:
    df['VL_PL'] = df['VL_ATIVO'].apply(limpar_valor)
    print(f"  VL_ATIVO encontrado! Max: R$ {df['VL_PL'].max():.2f}")
else:
    print(f"  ERRO: Nao foi possivel encontrar coluna de ativo!")
    print(f"  Colunas: {list(df.columns)}")
    exit(1)

# Remove duplicatas
if 'CNPJ_FUNDO' in df.columns:
    antes = len(df)
    df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
    print(f"  Duplicatas removidas: {antes - len(df)}")
else:
    # Tenta CNPJ_FUNDO_CLASSE
    for col in df.columns:
        if 'CNPJ' in col.upper() and 'FUNDO' in col.upper():
            df = df.rename(columns={col: 'CNPJ_FUNDO'})
            antes = len(df)
            df = df.drop_duplicates(subset=['CNPJ_FUNDO'], keep='last')
            print(f"  Usando {col} como CNPJ. Duplicatas: {antes - len(df)}")
            break

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
