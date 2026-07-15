"""
Módulo responsável por baixar e extrair os dados do Informe Mensal de FIDCs
do Portal de Dados Abertos da CVM.
"""
import requests
import zipfile
import io
import os
import re
from pathlib import Path

CVM_BASE_URL = "https://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS"

def listar_meses_disponiveis():
    response = requests.get(f"{CVM_BASE_URL}/", timeout=30)
    response.raise_for_status()
    padrao = r'inf_mensal_fidc_(\d{6})\.zip'
    return sorted(set(re.findall(padrao, response.text)), reverse=True)

def baixar_zip(competencia, dest_dir):
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = f"{CVM_BASE_URL}/inf_mensal_fidc_{competencia}.zip"
    print(f"[DOWNLOAD] Baixando {url}...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(dest_dir)
    print(f"[OK] Extraído em {dest_dir}")
    return dest_dir

def baixar_historico(ano, dest_dir):
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = f"{CVM_BASE_URL}/HIST/inf_mensal_fidc_{ano}.zip"
    print(f"[DOWNLOAD] Baixando histórico {url}...")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(dest_dir)
    print(f"[OK] Histórico {ano} extraído em {dest_dir}")
    return dest_dir

def obter_dados_recentes(dest_dir, meses=1):
    disponiveis = listar_meses_disponiveis()
    if not disponiveis:
        raise RuntimeError("Nenhum arquivo encontrado no repositório da CVM.")
    for competencia in disponiveis[:meses]:
        baixar_zip(competencia, dest_dir)
    return Path(dest_dir)
