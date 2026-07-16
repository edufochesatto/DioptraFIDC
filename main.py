import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from data_processor import processar_dados_cvm
import pandas as pd
import json
import numpy as np

DATA_DIR = Path("data")
DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 60)
    print("DIOPTRA FIDC")
    print("=" * 60)

    print("\n[1/2] Lendo CSVs da pasta data/raw/...")
    df = processar_dados_cvm(DATA_DIR / "raw")

    print("\n[2/2] Gerando dados.json...")

    fundos = []
    if not df.empty and 'VL_PL' in df.columns:
        # Converte de reais para milhoes se necessario
        if df['VL_PL'].max() > 1e8:
            df['VL_PL'] = df['VL_PL'] / 1e6
            print(f"  PL convertido de reais para milhoes")

        # Filtra PLs negativos e absurdos
        mask = df['VL_PL'].apply(lambda x: isinstance(x, (int, float)) and x >= 0 and x < 500000)
        df = df[mask]
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

        print(f"  {len(fundos)} fundos com PL > 0")

    # Salva dados.json
    with open(DOCS_DIR / "dados.json", "w") as f:
        json.dump({
            "fundos": fundos,
            "metricas": {},
            "gerado_em": "2026-07-16",
            "versao": "Julho/2026"
        }, f, indent=2, ensure_ascii=False)

    print(f"  dados.json salvo com {len(fundos)} fundos")

    # Resumo
    if fundos:
        pls = [f.get('VL_PL', 0) for f in fundos if f.get('VL_PL', 0) > 0]
        if pls:
            print(f"  PL total: R$ {sum(pls):.2f} milhoes")
            print(f"  PL medio: R$ {sum(pls)/len(pls):.2f} milhoes")
            print(f"  Maior fundo: {fundos[0].get('DENOMINACAO_SOCIAL', '')[:50]}...")

    print("\n" + "=" * 60)
    print("Concluido!")
    print("=" * 60)

if __name__ == "__main__":
    main()
