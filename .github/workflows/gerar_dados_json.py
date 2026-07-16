"""
Gera docs/dados.json apenas com dados reais. Sem sintéticos.
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
    print(f"📊 Pickle: {len(df)} linhas")

    if len(df) > 0 and 'VL_PL' in df.columns and df['VL_PL'].notna().any() and (df['VL_PL'] != 0).any():
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.where(pd.notna(df), None)
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
        print("⚠ Dados vazios ou zerados. Nenhum fundo.")
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
