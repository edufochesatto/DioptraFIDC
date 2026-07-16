"""
cvm_downloader.py — Download dos dados da CVM.
Tenta baixar o mês mais recente. Se falhar, retorna False.
"""
import requests
import zipfile
from pathlib import Path

def baixar_arquivo(url, destino):
    resposta = requests.get(url, timeout=60, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    resposta.raise_for_status()
    with open(destino, 'wb') as f:
        f.write(resposta.content)
    return destino

def extrair_zip(zip_path, destino_dir):
    import os
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(destino_dir)
    arquivos = [f for f in os.listdir(destino_dir) if f.endswith('.csv')]
    print(f"   → Extraídos {len(arquivos)} arquivos CSV")
    return arquivos

def obter_dados_recentes(data_dir):
    data_dir = Path(data_dir)
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    for i in range(6):
        m = mes - i
        a = ano
        while m <= 0:
            m += 12
            a -= 1
        codigo = f"{a}{m:02d}"
        nome_zip = f"inf_mensal_fidc_{codigo}.zip"
        url = f"https://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/{nome_zip}"

        print(f"   Tentando {nome_zip}...")
        try:
            zip_path = raw_dir / nome_zip
            baixar_arquivo(url, zip_path)
            print(f"   ✅ {nome_zip} baixado!")
            extrair_zip(zip_path, raw_dir)
            return True
        except requests.exceptions.RequestException as e:
            print(f"   ⚠ {nome_zip} indisponível: {e}")
            continue

    print("   ❌ Nenhum dado da CVM disponível.")
    return False
