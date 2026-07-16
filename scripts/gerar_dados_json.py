"""
Gera o arquivo docs/dados.json a partir dos dados processados.
Executado após main.py no workflow.
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
    # Converte para dicionário tratando tipos não serializáveis
    fundos = json.loads(df.to_json(orient='records', force_ascii=False, date_format='iso'))
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
    }, f, indent=2, ensure_ascii=False)

print("✅ dados.json gerado com sucesso!")
