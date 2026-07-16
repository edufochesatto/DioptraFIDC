"""
Gera docs/dados.json apenas com dados reais. Sem sintéticos.
Converte PL de reais para milhões automaticamente.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("output")
DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

pkl_file = DATA_DIR / "dados.pkl"
fundos = []

if pkl_file.exists():
    df = pd.read_pickle(pkl_file)
    print(f"📊 Pickle: {len(df)} linhas, colunas: {list(df.columns[:20])}")

    if len(df) > 0 and 'VL_PL' in df.columns and df['VL_PL'].notna().any() and (df['VL_PL'] != 0).any():
        # Converte PL para milhões (REAIS → milhões)
        pl_max = df['VL_PL'].max()
        pl_min_positivo = df[df['VL_PL'] > 0]['VL_PL'].min() if any(df['VL_PL'] > 0) else 0

        print(f"   PL max: R$ {pl_max:,.2f}, PL min positivo: R$ {pl_min_positivo:,.2f}")

        # Se o PL está em reais (valores > 1e9), converte para milhões
        if pl_max > 1e8:
            df['VL_PL'] = df['VL_PL'] / 1e6
            print(f"   PL convertido de reais → milhões")
            pl_max_novo = df['VL_PL'].max()
            print(f"   Novo PL max: {pl_max_novo:,.2f} milhões")

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.where(pd.notna(df), None)

        # Filtra PLs negativos e absurdos (> R$ 500 bi em milhões = 500.000)
        df = df[df['VL_PL'].apply(lambda x: isinstance(x, (int, float)) and x >= 0 and x < 500000)]

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
        print(f"✅ {len(fundos)} fundos exportados")
    else:
        print("⚠ Dados vazios ou zerados.")
else:
    print("⚠ Pickle não encontrado.")

with open(DOCS_DIR / "dados.json", "w") as f:
    json.dump({
        "fundos": fundos,
        "metricas": {},
        "gerado_em": "2026-07-16",
        "versao": "Julho/2026"
    }, f, indent=2, ensure_ascii=False)

print(f"✅ dados.json: {len(fundos)} fundos")
