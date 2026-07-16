"""
Busca benchmarks em tempo real — apenas IPCA e IBOVESPA.
"""
import json
import requests
from datetime import datetime

def buscar_ipca():
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        valores = [float(d['valor']) for d in dados[-13:] if d['valor']]
        if valores:
            ipca_acum = 1.0
            for v in valores:
                ipca_acum *= (1 + v / 100)
            return round((ipca_acum - 1) * 100, 2)
        return 4.50
    except:
        return 4.50

def buscar_ibovespa():
    try:
        url = "https://brapi.dev/api/quote/^BVSP?range=1d&interval=1d"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        if 'results' in dados and len(dados['results']) > 0:
            return round(dados['results'][0].get('regularMarketPrice', 129650), 0)
        return 129650
    except:
        return 129650

def main():
    print("📊 Buscando benchmarks...")

    ipca = buscar_ipca()
    print(f"   IPCA: {ipca:.2f}%")

    ibov = buscar_ibovespa()
    print(f"   IBOVESPA: {int(ibov):,} pts".replace(",", "."))

    benchmarks = {
        "ipca": {"valor": ipca, "unidade": "% a.a.", "fonte": "BCB SGS"},
        "ibovespa": {"valor": int(ibov), "unidade": "pts", "fonte": "brapi.dev"},
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    with open("docs/benchmarks.json", "w") as f:
        json.dump(benchmarks, f, indent=2, ensure_ascii=False)

    print(f"✅ benchmarks.json salvo!")

if __name__ == "__main__":
    main()
