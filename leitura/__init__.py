# -*- coding: utf-8 -*-
"""
Pacote de leitura da Fase 2 (documental).

Pipeline 100% local — nada é enviado para fora, exceto a consulta pública do
CNPJ na BrasilAPI (que não carrega nenhum dado pessoal, só o número do CNPJ).

Módulos:
  texto.py        — extrai texto do PDF (pdfplumber) com fallback de OCR (Tesseract)
  campos.py       — acha CNPJ, datas e termos por rótulo, com cor de confiança
  cnpj_online.py  — consulta situação cadastral e data de abertura na BrasilAPI
  conferencia.py  — junta tudo e sugere a conferência de cada critério do edital
"""
