"""
Dioptra FIDC — Orquestrador principal.
Baixa dados da CVM, processa, filtra e gera o dashboard.
"""
import sys
from pathlib import Path
from cvm_downloader import obter_dados_recentes
from data_processor import processar_duplicatas_pme
from dashboard_generator import gerar_dashboard

DATA_DIR = Path("./dados_cvm")
OUTPUT_DIR = Path("./output")
OUTPUT_FILE = OUTPUT_DIR / "Dioptra_FIDC.xlsx"

def main():
    print("=" * 60)
    print("DIOPTRA FIDC")
    print("=" * 60)

    # 1. Download
    print("\n[1/4] Baixando dados mais recentes da CVM...")
    try:
        obter_dados_recentes(DATA_DIR, meses=1)
    except Exception as e:
        print(f"[ERRO] Download: {e}")
        sys.exit(1)

    # 2. Listar arquivos baixados
    print("\n[2/4] Arquivos disponíveis:")
    for f in sorted(DATA_DIR.glob("*.csv")):
        print(f"   {f.name}")

    # 3. Processar
    print("\n[3/4] Processando dados...")
    try:
        df, metricas = processar_duplicatas_pme(DATA_DIR)
    except Exception as e:
        print(f"[ERRO] Processamento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if df.empty:
        print("[AVISO] Nenhum fundo Duplicatas/PME encontrado.")
        print("Verifique se a coluna CLASSE contém 'Duplicata' ou 'PME'.")
        sys.exit(1)

    print(f"\n   → {len(df)} fundos processados.")
    print(f"   → {len(metricas)} métricas calculadas.")

    # 4. Dashboard
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("\n[4/4] Gerando dashboard...")
    gerar_dashboard(df, metricas, OUTPUT_FILE)

    print(f"\n✅ Concluído! {len(df)} fundos analisados.")

if __name__ == "__main__":
    main()
