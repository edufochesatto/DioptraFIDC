"""
Busca benchmarks financeiros em tempo real de APIs públicas.
CDI e IPCA → BCB (SGS)
IBOVESPA → brapi.dev
"""
import json
import requests
from datetime import datetime

def buscar_cdi():
    """CDI acumulado 12 meses - BCB SGS código 12"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        # Código 12 = CDI diária (% ao dia)
        # Acumula: produto de (1 + taxa/100) para cada dia útil
        taxas = []
        for d in dados[-380:]:  # pega mais que 252 dias uteis
            try:
                v = float(d['valor'])
                if v > 0:
                    taxas.append(v)
            except:
                pass
        if len(taxas) >= 20:
            # Pega os últimos 252 dias uteis (~12 meses)
            taxas = taxas[-252:]
            cdi_acum = 1.0
            for t in taxas:
                cdi_acum *= (1 + t / 100)
            cdi_pct = round((cdi_acum - 1) * 100, 2)
            return cdi_pct
        return 10.50
    except Exception as e:
        print(f"   [ERRO CDI] {e}")
        return 10.50

def buscar_ipca():
    """IPCA acumulado 12 meses - BCB SGS código 433"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        # Código 433 = IPCA mensal (%)
        valores = [float(d['valor']) for d in dados[-13:] if d['valor']]
        if valores:
            ipca_acum = 1.0
            for v in valores:
                ipca_acum *= (1 + v / 100)
            ipca_pct = round((ipca_acum - 1) * 100, 2)
            return ipca_pct
        return 4.50
    except Exception as e:
        print(f"   [ERRO IPCA] {e}")
        return 4.50

def buscar_ibovespa():
    """IBOVESPA via brapi.dev"""
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
    print("📊 Buscando benchmarks em tempo real...")

    cdi = buscar_cdi()
    print(f"   CDI: {cdi:.2f}% a.a.")

    ipca = buscar_ipca()
    print(f"   IPCA: {ipca:.2f}% a.a.")

    ibov = buscar_ibovespa()
    print(f"   IBOVESPA: {int(ibov):,} pts".replace(",", "."))

    benchmarks = {
        "cdi": {"valor": cdi, "unidade": "% a.a.", "fonte": "BCB SGS"},
        "ipca": {"valor": ipca, "unidade": "% a.a.", "fonte": "BCB SGS"},
        "ibovespa": {"valor": int(ibov), "unidade": "pts", "fonte": "brapi.dev"},
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    with open("docs/benchmarks.json", "w") as f:
        json.dump(benchmarks, f, indent=2, ensure_ascii=False)

    print(f"✅ benchmarks.json salvo!")

if __name__ == "__main__":
    main()
