"""
Dioptra FIDC — Orquestrador principal.
Baixa dados da CVM, processa, filtra e gera o dashboard.
"""
import argparse
import sys
from pathlib import Path
from cvm_downloader import obter_dados_recentes, baixar_zip, baixar_historico
from data_processor import carregar_tabela, filtrar_duplicatas_pme, calcular_metricas_governanca
from dashboard_generator import gerar_dashboard

DATA_DIR = Path("./dados_cvm")
OUTPUT_DIR = Path("./output")
OUTPUT_FILE = OUTPUT_DIR / "Dioptra_FIDC_Julho2026.xlsx"

def main():
    parser = argparse.ArgumentParser(description="Dioptra FIDC — Dashboard de FIDCs")
    parser.add_argument("--mes", type=str, help="Competência YYYYMM (ex: 202605)")
    parser.add_argument("--historico", type=str, help="Ano histórico YYYY (ex: 2024)")
    args = parser.parse_args()

    print("=" * 60)
    print("DIOPTRA FIDC")
    print("=" * 60)

    try:
        if args.mes:
            print(f"\n[1/4] Baixando {args.mes}...")
            baixar_zip(args.mes, DATA_DIR)
        elif args.historico:
            print(f"\n[1/4] Baixando histórico {args.historico}...")
            baixar_historico(args.historico, DATA_DIR)
        else:
            print("\n[1/4] Baixando dados mais recentes da CVM...")
            obter_dados_recentes(DATA_DIR, meses=1)
    except Exception as e:
        print(f"[ERRO] Falha ao baixar: {e}")
        sys.exit(1)

    print("\n[2/4] Carregando tabelas...")
    try:
        tab_i = carregar_tabela(DATA_DIR, "tab_I")
        tab_ii = carregar_tabela(DATA_DIR, "tab_II")
        tab_iii = carregar_tabela(DATA_DIR, "tab_III")
        tab_v = carregar_tabela(DATA_DIR, "tab_V")
        tab_vi = carregar_tabela(DATA_DIR, "tab_VI")
        tab_vii = carregar_tabela(DATA_DIR, "tab_VII")
        tab_ix = carregar_tabela(DATA_DIR, "tab_IX")
    except FileNotFoundError as e:
        print(f"[ERRO] {e}")
        sys.exit(1)

    print("[3/4] Filtrando Duplicatas/PME...")
    df = filtrar_duplicatas_pme(tab_i, tab_ii, tab_iii, tab_v, tab_vi, tab_vii, tab_ix)
    if len(df) == 0:
        print("[AVISO] Nenhum fundo de Duplicatas/PME encontrado.")
        if 'CLASSE' in tab_i.columns:
            print("Classes disponíveis:")
            print(tab_i['CLASSE'].value_counts().to_string())
        sys.exit(1)
    print(f"   → {len(df)} fundos encontrados.")
    metricas = calcular_metricas_governanca(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[4/4] Gerando dashboard...")
    gerar_dashboard(df, metricas, OUTPUT_FILE)

    print(f"\n✅ Concluído! {len(df)} fundos analisados.")

if __name__ == "__main__":
    main()
