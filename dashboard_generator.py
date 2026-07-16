"""
DIOPTRA FIDC — Dashboard de Governança para FIDCs de Duplicatas/PME
Autor: Eduardo Fochesatto
Licença: MIT
"""
import pandas as pd
import numpy as np
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border
from openpyxl.utils.dataframe import dataframe_to_rows

# ── CONFIGURAÇÃO ──
NOME_FERRAMENTA = "Dioptra FIDC"
AUTOR = "Eduardo Fochesatto"
REPOSITORIO = "https://github.com/eduardofochesatto/dioptra-fidc"
VERSAO = "Julho/2026"

# ── Cores ──
AZUL_ESCURO = "1F3864"
BRANCO      = "FFFFFF"
VERDE       = "C6EFCE"
VERMELHO    = "FFC7CE"
AMARELO     = "FFEB9C"
CINZA_L     = "F5F5F5"
CINZA_T     = "808080"
PRETO       = "1A1A1A"

FILL_H = PatternFill("solid", fgColor=AZUL_ESCURO)
FILL_Z = PatternFill("solid", fgColor=CINZA_L)
FILL_V = PatternFill("solid", fgColor=VERDE)
FILL_R = PatternFill("solid", fgColor=VERMELHO)
FILL_A = PatternFill("solid", fgColor=AMARELO)

FONT_H = Font(name="Calibri", bold=True, color=BRANCO, size=11)
FONT_T = Font(name="Calibri", bold=True, size=18, color=AZUL_ESCURO)
FONT_T2= Font(name="Calibri", bold=True, size=14, color=AZUL_ESCURO)
FONT_S = Font(name="Calibri", italic=True, size=11, color=CINZA_T)
FONT_D = Font(name="Calibri", bold=True, size=12, color=AZUL_ESCURO)
FONT_N = Font(name="Calibri", size=10)
FONT_A = Font(name="Calibri", bold=True, size=10, color="CC0000")

AL = Alignment(horizontal="left", vertical="top", wrap_text=True)
AR = Alignment(horizontal="right", vertical="center")
AC = Alignment(horizontal="center", vertical="center")

BENCH = {
    "CDI": {"2022":12.40,"2023":13.05,"2024":10.80,"2025":11.20,"2026":10.50},
    "IMAB":{"2022":10.10,"2023":15.80,"2024":8.40,"2025":12.50,"2026":11.80},
    "IPCA":{"2022":5.79,"2023":4.62,"2024":4.30,"2025":4.80,"2026":4.50},
}

def _cab(ws, l, n):
    for c in range(1, n+1):
        cl = ws.cell(row=l, column=c)
        cl.fill = FILL_H; cl.font = FONT_H; cl.alignment = AC

def _zeb(ws, i, f, n):
    for r in range(i, f+1):
        if (r-i) % 2 == 1:
            for c in range(1, n+1):
                ws.cell(row=r, column=c).fill = FILL_Z

def _assin(ws, l):
    ws.cell(row=l, column=1,
            value=f"{NOME_FERRAMENTA} — {AUTOR} — {REPOSITORIO}").font = FONT_S

def _ajustar_largura(ws, dx):
    for ci, col in enumerate(dx.columns, 1):
        comp = max(len(str(col)),
                   dx[col].astype(str).str.len().max() if len(dx) > 0 else 0)
        ws.column_dimensions[
            ws.cell(row=1, column=ci).column_letter
        ].width = min(comp + 3, 35)

def criar_capa(wb):
    ws = wb.active; ws.title = "0. Capa"
    itens = [
        (1, f"{NOME_FERRAMENTA}", FONT_T),
        (2, "Dashboard de Governança para FIDCs de Duplicatas/PME", FONT_D),
        (3, f"{AUTOR} — {VERSAO}", FONT_S),
        (5, "╔╗", None),
        (6, "║           AVISO IMPORTANTE                       ║", None),
        (7, "╠╣", None),
        (8,  "║  Dados públicos autodeclarados à CVM.           ║", None),
        (9,  "║  LIMITAÇÕES: defasagem 30-45d, preenchimento    ║", None),
        (10, "║  parcial, classificação aproximada.             ║", None),
        (11, "╠╣", None),
        (12, "║  NÃO SUBSTITUI DILIGÊNCIA — triagem, não decisão║", None),
        (13, "╚╝", None),
        (15, f"📬 {AUTOR}", FONT_D),
        (16, f"Repositório: {REPOSITORIO}", FONT_S),
        (17, "Licença: MIT", FONT_S),
        (19, "📋 Abas: 0.Capa | 1.Ranking | 2.Top10 | 3.CDI vs IMAB | 4.Governança | 5.Propósito | 6.Fontes | 7.Glossário", FONT_N),
    ]
    for l, txt, st in itens:
        c = ws.cell(row=l, column=1, value=txt)
        if st: c.font = st
    for l in [6, 10, 12]:
        ws.cell(row=l, column=1).font = Font(name="Consolas", bold=True, size=10, color="CC0000")
    for l in range(5, 14):
        ws.cell(row=l, column=1).font = Font(name="Consolas", size=10, color=PRETO)
    ws.column_dimensions["A"].width = 100
    ws.sheet_properties.tabColor = "CC0000"

def criar_ranking(wb, df):
    """Aba 1: Ranking completo com filtro automático."""
    ws = wb.create_sheet("1. Ranking Completo")

    MAPA = {
        'CNPJ_FUNDO':'CNPJ do Fundo', 'DENOMINACAO_SOCIAL':'Nome do Fundo',
        'GESTORA':'Gestora', 'CLASSE':'Classe', 'VL_PL':'PL (R$ milhões)',
        'PRAZO_MEDIO':'Prazo Médio (dias)', 'RENTABILIDADE':'Rentabilidade (% a.a.)',
        'PDD_PCT':'PDD (% PL)', 'RECOMPRA_PCT':'Recompra (%)',
        'PCT_SUBORDINADO':'Subordinado (%)',
