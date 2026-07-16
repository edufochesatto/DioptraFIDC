"""
Gera o arquivo docs/dados.json a partir dos dados processados.
"""
import json
import pandas as pd
from pathlib import Path

DATA_DIR = Path("output")
DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

pkl_file = DATA_DIR / "dados.pkl"
if pkl_file.exists():
    df = pd.read_pickle(pkl_file)
    fundos = df.fillna(0).to_dict('records')
    print(f"✅ {len(fundos)} fundos exportados para dados.json")
else:
    fundos = []
    print("⚠ Nenhum dado pickle encontrado, usando JSON vazio")

with open(DOCS_DIR / "dados.json", "w") as f:
    json.dump({
        "fundos": fundos,
        "metricas": {},
        "gerado_em": "2026-07-16",
        "versao": "Julho/2026"
    }, f, indent=2, ensure_ascii=False, default=str)

print("✅ dados.json gerado com sucesso!")
