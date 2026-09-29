# -*- coding: utf-8 -*-
"""
Extração de texto do PDF, com OCR como último recurso.

Ordem: pdfplumber (texto digital, ignora caracteres girados como carimbos) →
OCR com Tesseract em português só nas páginas sem texto. Se o Tesseract não
estiver instalado, a página sem texto é marcada como "escaneada" para a tela
avisar que precisa de conferência manual. Nada trava o app: qualquer erro
devolve texto vazio com origem "erro".
"""
import glob
import io
import os

MIN_CHARS = 50  # abaixo disso a página é tratada como sem texto útil (calibrar)

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import pytesseract
    from pdf2image import convert_from_bytes
except Exception:
    pytesseract = None
    convert_from_bytes = None

# Caminhos padrão de instalação no Windows — assim o OCR "funciona sozinho"
# depois de instalar, sem precisar mexer no PATH.
_TESSERACT_PADRAO = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
_POPPLER_PADRAO = glob.glob(r"C:\Program Files\poppler*\Library\bin") + \
    glob.glob(r"C:\poppler*\Library\bin") + \
    glob.glob(r"C:\Program Files\poppler*\bin")


def _config_tesseract():
    if pytesseract is None:
        return
    try:
        atual = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
        if atual and atual != "tesseract" and os.path.exists(atual):
            return
        for caminho in _TESSERACT_PADRAO:
            if os.path.exists(caminho):
                pytesseract.pytesseract.tesseract_cmd = caminho
                return
    except Exception:
        pass


def _poppler_path():
    for p in _POPPLER_PADRAO:
        if os.path.isdir(p):
            return p
    return None


_config_tesseract()


def ocr_disponivel():
    """True se o Tesseract está instalado e acessível (para PDFs escaneados)."""
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _bytes(arquivo):
    """Aceita bytes, UploadedFile do Streamlit ou file-like; devolve bytes."""
    if arquivo is None:
        return b""
    if isinstance(arquivo, (bytes, bytearray)):
        return bytes(arquivo)
    for metodo in ("getvalue", "read"):
        fn = getattr(arquivo, metodo, None)
        if callable(fn):
            try:
                arquivo.seek(0)
            except Exception:
                pass
            return fn()
    return b""


def _ocr_pagina(pdf_bytes, indice):
    """Roda OCR numa página (0-based). Devolve (texto, confiança 0..1)."""
    if not ocr_disponivel() or convert_from_bytes is None:
        return "", 0.0
    try:
        extra = {"poppler_path": _poppler_path()} if _poppler_path() else {}
        imgs = convert_from_bytes(pdf_bytes, dpi=300,
                                  first_page=indice + 1, last_page=indice + 1, **extra)
        if not imgs:
            return "", 0.0
        d = pytesseract.image_to_data(imgs[0], lang="por",
                                      output_type=pytesseract.Output.DICT)
        palavras = [w for w in d["text"] if w and w.strip()]
        confs = [float(c) for c in d["conf"] if str(c) not in ("-1", "") and float(c) >= 0]
        conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return " ".join(palavras), conf
    except Exception:
        return "", 0.0


def extrair_paginas(arquivo):
    """
    Devolve uma lista de páginas: {"pagina", "texto", "origem", "conf"}.
    origem ∈ {"digital", "ocr", "escaneada", "erro"}.
    """
    pdf_bytes = _bytes(arquivo)
    if not pdf_bytes or pdfplumber is None:
        return [{"pagina": 1, "texto": "", "origem": "erro", "conf": 0.0}]

    paginas = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, pg in enumerate(pdf.pages):
                try:
                    limpa = pg.filter(lambda o: o.get("upright", True))
                    txt = (limpa.extract_text() or "").strip()
                except Exception:
                    txt = (pg.extract_text() or "").strip()

                if len(txt) >= MIN_CHARS:
                    paginas.append({"pagina": i + 1, "texto": txt,
                                    "origem": "digital", "conf": 1.0})
                else:
                    txt_ocr, conf = _ocr_pagina(pdf_bytes, i)
                    if txt_ocr.strip():
                        paginas.append({"pagina": i + 1, "texto": txt_ocr,
                                        "origem": "ocr", "conf": conf})
                    else:
                        paginas.append({"pagina": i + 1, "texto": txt,
                                        "origem": "escaneada", "conf": 0.0})
    except Exception:
        return [{"pagina": 1, "texto": "", "origem": "erro", "conf": 0.0}]
    return paginas or [{"pagina": 1, "texto": "", "origem": "erro", "conf": 0.0}]


def extrair(arquivo):
    """
    Resumo pronto para a conferência:
      {"texto", "origem", "conf", "paginas", "escaneado", "ocr_usado", "ocr_disp"}
    - texto: todo o texto concatenado
    - origem: "digital", "ocr", "escaneada" (nenhuma página teve texto) ou "erro"
    - conf: menor confiança entre as páginas com conteúdo (0..1)
    """
    pgs = extrair_paginas(arquivo)
    texto = "\n".join(p["texto"] for p in pgs if p["texto"]).strip()
    origens = {p["origem"] for p in pgs}
    ocr_usado = "ocr" in origens
    if texto:
        confs = [p["conf"] for p in pgs if p["texto"]]
        conf = min(confs) if confs else 0.0
        origem = "ocr" if ocr_usado and "digital" not in origens else "digital"
    else:
        conf = 0.0
        origem = "escaneada" if "escaneada" in origens else "erro"
    return {
        "texto": texto,
        "origem": origem,
        "conf": conf,
        "paginas": len(pgs),
        "escaneado": (origem == "escaneada"),
        "ocr_usado": ocr_usado,
        "ocr_disp": ocr_disponivel(),
    }
