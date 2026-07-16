"""
main.py — Pipeline Dioptra FIDC
Tenta baixar dados da CVM. Se falhar, dashboard fica vazio.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_processor import processar_duplicatas_pme
from cvm_downloader import obter_dados_recentes
import pandas as pd

DATA_DIR = Path("output")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 60)
    print("DIOPTRA FIDC")
    print("=" * 60)

    print("\n[1/3] Baixando dados da CVM...")
    sucesso = obter_dados_recentes(DATA_DIR)

    print("\n[2/3] Processando dados...")
    df = pd.DataFrame()

    if sucesso:
        try:
            df, metricas = processar_duplicatas_pme(DATA_DIR / "raw")
            print(f"   ✅ {len(df)} fundos processados da CVM")
        except Exception as e:
            print(f"   ⚠ Erro no processamento: {e}")
    else:
        print("   ⚠ CVM indisponível. Dashboard ficará vazio.")

    pickle_path = DATA_DIR / "dados.pkl"
    df.to_pickle(pickle_path)
    print(f"   ✅ Pickle salvo em {pickle_path}")

    print("\n[3/3] Resumo:")
    if not df.empty:
        print(f"   - {len(df)} fundos")
        if 'VL_PL' in df.columns:
            print(f"   - PL total: R$ {df['VL_PL'].sum() / 1e6:.2f} bi")
    else:
        print("   - Nenhum dado real.")

    print("\n" + "=" * 60)
    print("Concluído!")
    print("=" * 60)

if __name__ == "__main__":
    main()
