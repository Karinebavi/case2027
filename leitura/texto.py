# -*- coding: utf-8 -*-
"""
Extração de texto do PDF, página a página, com OCR quando a página é imagem.

Ordem: pdfplumber (texto digital, ignora caracteres girados como carimbos) →
OCR com Tesseract em português nas páginas sem texto. A página é convertida
em imagem pelo pypdfium2 (já vem com o pdfplumber) — não precisa de poppler.

Carimbos e selos de cartório têm letra miúda e ficam espalhados pela folha;
a leitura normal costuma pular esse texto. Por isso as primeiras e últimas
folhas escaneadas recebem uma 2ª leitura em "modo texto esparso" (psm 11),
guardada à parte em "extra" — é onde aparecem "Selo de consulta",
"Protocolo", "Registro nº"...

Nada trava o app: erro devolve página vazia com origem "erro".
"""
import io
import os

MIN_CHARS = 50   # abaixo disso a página é tratada como sem texto útil
DPI_OCR = 300
PAGINAS_CARIMBO = 2  # 2ª leitura nas N primeiras e N últimas folhas escaneadas

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import pypdfium2 as pdfium
except Exception:
    pdfium = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# Caminhos padrão no Windows — o OCR "funciona sozinho" depois de instalar.
_TESSERACT_PADRAO = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


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


_config_tesseract()


def ocr_disponivel():
    """True se o Tesseract (com português) e o renderizador estão prontos."""
    if pytesseract is None or pdfium is None:
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


MAX_LADO_PX = 3600  # ~A4 a 300 dpi; evita imagem gigante em PDF com "página" enorme


def _imagem(pdf_doc, indice, dpi=DPI_OCR):
    pagina = pdf_doc[indice]
    larg, alt = pagina.get_size()  # em pontos (1/72")
    escala = min(dpi / 72, MAX_LADO_PX / max(larg, alt, 1))
    return pagina.render(scale=escala).to_pil().convert("L")


def _orientar(img):
    """Corrige a orientação da página (0/90/180/270) usando a detecção do
    Tesseract (OSD), ANTES de ler — resolve páginas escaneadas de lado/de
    cabeça para baixo. Best-effort: se a detecção falhar, devolve a original."""
    try:
        osd = pytesseract.image_to_osd(img, config=f"--dpi {DPI_OCR}",
                                       output_type=pytesseract.Output.DICT)
        ang = int(osd.get("rotate", 0)) % 360
        if ang:
            return img.rotate(-ang, expand=True)
    except Exception:
        pass
    return img


def _binarizar(img):
    """Scan de baixo contraste: o Tesseract às vezes não separa letra do fundo
    sozinho e devolve página vazia. Normaliza o contraste e força preto-e-branco
    para recuperar a leitura (foi o que destravou atas escaneadas claras)."""
    from PIL import ImageOps
    return ImageOps.autocontrast(img).point(lambda x: 0 if x < 140 else 255, "L")


def _recuperar(img, txt, conf):
    """A leitura normal veio curta. Tenta recuperar, da mais barata à mais cara:
    1) binariza (resolve o scan claro/baixo contraste, causa comum de 'não leu
    nada'); 2) se ainda curto, testa as 4 rotações — na imagem e na binarizada.
    Só roda em páginas-problema, então não pesa nas boas.
    Devolve (imagem usada, texto, confiança)."""
    melhor = (img, txt, conf)
    bin_img = _binarizar(img)
    try:
        t, c = _ocr(bin_img)
        if len(t.strip()) > len(melhor[1].strip()):
            melhor = (bin_img, t, c)
    except Exception:
        pass
    if len(melhor[1].strip()) < MIN_CHARS:
        for base in (img, bin_img):
            for ang in (90, 180, 270):
                try:
                    cand = base.rotate(-ang, expand=True)
                    t, c = _ocr(cand)
                except Exception:
                    continue
                if len(t.strip()) > len(melhor[1].strip()):
                    melhor = (cand, t, c)
    return melhor


def _ocr(img, psm=None):
    """OCR de uma imagem. Devolve (texto com quebras de linha, confiança 0..1)."""
    partes = [f"--dpi {DPI_OCR}"]   # evita o erro "resolução 0 dpi" e melhora a escala
    if psm:
        partes.append(f"--psm {psm}")
    config = " ".join(partes)
    d = pytesseract.image_to_data(img, lang="por", config=config,
                                  output_type=pytesseract.Output.DICT)
    linhas, atual, chave = [], [], None
    for i, palavra in enumerate(d["text"]):
        k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        if k != chave and atual:
            linhas.append(" ".join(atual))
            atual = []
        chave = k
        if palavra and palavra.strip():
            atual.append(palavra.strip())
    if atual:
        linhas.append(" ".join(atual))
    confs = [float(c) for c in d["conf"] if str(c) not in ("-1", "") and float(c) >= 0]
    conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return "\n".join(linhas), conf


def extrair_paginas(arquivo, progresso=None):
    """
    Lista de páginas: {"pagina", "texto", "extra", "origem", "conf"}.
    origem ∈ {"digital", "ocr", "escaneada", "erro"}; "extra" = 2ª leitura
    (carimbos) quando feita. progresso(feitas, total) a cada página de OCR.
    """
    pdf_bytes = _bytes(arquivo)
    erro = [{"pagina": 1, "texto": "", "extra": "", "origem": "erro", "conf": 0.0}]
    if not pdf_bytes or pdfplumber is None:
        return erro

    paginas = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, pg in enumerate(pdf.pages):
                try:
                    limpa = pg.filter(lambda o: o.get("upright", True))
                    txt = (limpa.extract_text() or "").strip()
                except Exception:
                    txt = (pg.extract_text() or "").strip()
                digital = len(txt) >= MIN_CHARS
                paginas.append({"pagina": i + 1, "texto": txt, "extra": "",
                                "origem": "digital" if digital else "escaneada",
                                "conf": 1.0 if digital else 0.0})
    except Exception:
        return erro
    if not paginas:
        return erro

    faltam = [p for p in paginas if p["origem"] == "escaneada"]
    if faltam and ocr_disponivel():
        try:
            doc = pdfium.PdfDocument(pdf_bytes)
        except Exception:
            doc = None
        if doc is not None:
            idx = [p["pagina"] - 1 for p in faltam]
            carimbo = set(idx[:PAGINAS_CARIMBO] + idx[-PAGINAS_CARIMBO:])
            for n, p in enumerate(faltam):
                if progresso:
                    progresso(n, len(faltam))
                i = p["pagina"] - 1
                try:
                    img = _orientar(_imagem(doc, i))       # corrige página girada
                    txt, conf = _ocr(img)
                    if len(txt.strip()) < MIN_CHARS:        # ainda ruim: binariza e/ou gira
                        img, txt, conf = _recuperar(img, txt, conf)
                    if txt.strip():
                        p.update(texto=txt, origem="ocr", conf=conf)
                    if i in carimbo:
                        p["extra"], _ = _ocr(img, psm=11)
                except Exception:
                    continue
            if progresso:
                progresso(len(faltam), len(faltam))
    return paginas


def origem_geral(paginas):
    """Como o documento foi lido: digital, ocr, misto, escaneada (sem texto) ou erro."""
    origens = {p["origem"] for p in paginas}
    if origens == {"erro"}:
        return "erro"
    if "ocr" in origens:
        return "ocr" if "digital" not in origens else "misto"
    if origens == {"digital"}:
        return "digital"
    if "digital" in origens:
        return "misto"
    return "escaneada"
