"""
Busca benchmarks financeiros em tempo real de APIs públicas.
CDI e IPCA → BCB (SGS)
IBOVESPA → brapi.dev
IMAB 5+ → estimativa baseada na SELIC + IPCA
"""
import json
import requests
from datetime import datetime, timedelta

def buscar_cdi():
    """CDI acumulado 12 meses - SGS BCB código 12"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        # Pega os últimos ~252 dias úteis (12 meses)
        valores = [float(d['valor']) for d in dados[-260:] if d['valor'] != '0']
        if valores:
            cdi_acum = round((sum(valores) / 100 + 1)**(252/len(valores)) - 1, 2) * 100
            return round(cdi_acum, 2)
        return 10.50
    except:
        return 10.50

def buscar_ipca():
    """IPCA acumulado 12 meses - SGS BCB código 433"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        # Pega os últimos 13 meses e calcula acumulado
        valores = [float(d['valor']) for d in dados[-13:]]
        if valores:
            ipca_acum = round((sum(valores) / 100 + 1)**(12/len(valores)) - 1, 2) * 100
            return round(ipca_acum, 2)
        return 4.50
    except:
        return 4.50

def buscar_ibovespa():
    """IBOVESPA via brapi.dev (gratuito, sem API key)"""
    try:
        url = "https://brapi.dev/api/quote/^BVSP?range=1d&interval=1d"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        if 'results' in dados and len(dados['results']) > 0:
            return round(dados['results'][0].get('regularMarketPrice', 129650), 0)
        return 129650
    except:
        return 129650

def buscar_imab():
    """IMAB 5+ estimado via SELIC + IPCA"""
    try:
        # Busca SELIC (código 11)
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados?formato=json"
        resp = requests.get(url, timeout=10)
        dados = resp.json()
        valores = [float(d['valor']) for d in dados[-260:] if d['valor'] != '0']
        if valores:
            selic_acum = round((sum(valores) / 100 + 1)**(252/len(valores)) - 1, 2) * 100
            # IMAB 5+ costuma ficar ~0.8-1.5 p.p. acima do CDI
            ipca = buscar_ipca() / 100
            imab_est = round(selic_acum + (selic_acum - ipca * 100) * 0.3, 2)
            return imab_est
        return 11.80
    except:
        return 11.80

def main():
    print("📊 Buscando benchmarks em tempo real...")

    cdi = buscar_cdi()
    print(f"   CDI: {cdi:.2f}% a.a.")

    ipca = buscar_ipca()
    print(f"   IPCA: {ipca:.2f}% a.a.")

    imab = buscar_imab()
    print(f"   IMAB 5+: {imab:.2f}% a.a.")

    ibov = buscar_ibovespa()
    print(f"   IBOVESPA: {int(ibov):,} pts".replace(",", "."))

    benchmarks = {
        "cdi": {"valor": cdi, "unidade": "% a.a.", "fonte": "BCB SGS"},
        "imab": {"valor": imab, "unidade": "% a.a.", "fonte": "BCB SGS (estimado)"},
        "ipca": {"valor": ipca, "unidade": "% a.a.", "fonte": "BCB SGS"},
        "ibovespa": {"valor": int(ibov), "unidade": "pts", "fonte": "brapi.dev"},
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    with open("docs/benchmarks.json", "w") as f:
        json.dump(benchmarks, f, indent=2, ensure_ascii=False)

    print(f"✅ benchmarks.json salvo!")

if __name__ == "__main__":
    main()
