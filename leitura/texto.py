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
from concurrent.futures import ThreadPoolExecutor, as_completed

MIN_CHARS = 50   # abaixo disso a página é tratada como sem texto útil
DPI_OCR = 300
PAGINAS_CARIMBO = 2  # 2ª leitura nas N primeiras e N últimas folhas escaneadas
# OCR SEQUENCIAL (1 por vez). Cada página chama o Tesseract, que roda como
# subprocesso e usa arquivos temporários. Rodar várias páginas em paralelo
# (threads) parecia mais rápido, mas na prática derrubava a leitura: num
# estatuto de 30 folhas, 3 threads liam só 2 páginas (o resto voltava vazio)
# e o estrago ainda contaminava o documento seguinte. Em sequência, as mesmas
# 30 páginas leem 30/30. Num conferidor de documentos, ler certo vale mais que
# ler rápido — e a barra de progresso mantém o mentor informado.
_WORKERS = 1

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


def _eh_imagem(dados):
    """Reconhece foto/scan enviado como imagem (JPEG, PNG, TIFF, GIF, BMP, WebP)
    pela assinatura do arquivo — muitas entidades mandam FOTO do documento."""
    b = dados[:12]
    return (b[:3] == b"\xff\xd8\xff" or b[:4] == b"\x89PNG" or b[:4] in (b"II*\x00", b"MM\x00*")
            or b[:4] == b"GIF8" or b[:2] == b"BM" or (b[:4] == b"RIFF" and b[8:12] == b"WEBP"))


MAX_PIXELS_IMG = 60_000_000   # ~60 MP: cobre foto de celular; barra "bomba" de descompressão


def _ler_imagem(dados):
    """OCR direto numa imagem (não-PDF). Devolve a lista de páginas (uma)."""
    import io as _io
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS_IMG   # levanta DecompressionBombError acima disso
    try:
        img = Image.open(_io.BytesIO(dados))
        img.load()
        img = img.convert("L")
    except Exception:   # inclui DecompressionBombError e imagem corrompida
        return [{"pagina": 1, "texto": "", "extra": "", "origem": "erro", "conf": 0.0}]
    lado = max(img.size)
    if lado > MAX_LADO_PX:
        fator = MAX_LADO_PX / lado
        img = img.resize((max(1, int(img.width * fator)), max(1, int(img.height * fator))))
    if not ocr_disponivel():
        return [{"pagina": 1, "texto": "", "extra": "", "origem": "escaneada", "conf": 0.0}]
    img = _orientar(img)
    txt, conf = _ocr(img)
    if len(txt.strip()) < MIN_CHARS:
        img, txt, conf = _recuperar(img, txt, conf)
    origem = "ocr" if txt.strip() else "escaneada"
    return [{"pagina": 1, "texto": txt, "extra": "", "origem": origem, "conf": conf}]


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
    # 0) orientação detectada pelo Tesseract (página de lado / de cabeça p/ baixo)
    ori = _orientar(img)
    if ori is not img:
        try:
            t, c = _ocr(ori)
            if len(t.strip()) > len(melhor[1].strip()):
                melhor = (ori, t, c)
        except Exception:
            pass
    base_img = melhor[0]
    bin_img = _binarizar(base_img)
    try:
        t, c = _ocr(bin_img)
        if len(t.strip()) > len(melhor[1].strip()):
            melhor = (bin_img, t, c)
    except Exception:
        pass
    if len(melhor[1].strip()) < MIN_CHARS:
        for base in (base_img, bin_img):
            for ang in (90, 180, 270):
                try:
                    cand = base.rotate(-ang, expand=True)
                    t, c = _ocr(cand)
                except Exception:
                    continue
                if len(t.strip()) > len(melhor[1].strip()):
                    melhor = (cand, t, c)
    return melhor


def _ocr_uma_pagina(pdf_bytes, i, fazer_carimbo):
    """Renderiza e lê UMA página (tarefa para rodar em paralelo). Cada thread
    abre seu próprio documento pypdfium (seguro entre threads)."""
    try:
        doc = pdfium.PdfDocument(pdf_bytes)
    except Exception:
        return i, "", 0.0, ""
    try:
        img = _imagem(doc, i)
        txt, conf = _ocr(img)
        if len(txt.strip()) < MIN_CHARS:      # ainda ruim: orienta, binariza e/ou gira
            img, txt, conf = _recuperar(img, txt, conf)
        extra = _ocr(img, psm=11)[0] if fazer_carimbo else ""
        return i, txt, conf, extra
    except Exception:
        return i, "", 0.0, ""
    finally:
        try:
            doc.close()
        except Exception:
            pass


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


def _paginas_por_pdfium(pdf_bytes):
    """Fallback quando o pdfplumber não abre o PDF (arquivo malformado: devolve
    0 páginas ou lança erro). Conta as folhas pelo renderizador — elas entram
    como 'escaneada' e seguem todas para o OCR, que lê a imagem da página.
    Destrava estatutos/atas gerados por scanners que o pdfplumber não parseia."""
    if pdfium is None:
        return []
    try:
        doc = pdfium.PdfDocument(pdf_bytes)
        n = len(doc)
        doc.close()
    except Exception:
        return []
    return [{"pagina": i + 1, "texto": "", "extra": "", "origem": "escaneada", "conf": 0.0}
            for i in range(n)]


import re as _re

# Carimbo de registro/assinatura digital (RCPJ, ITI) que alguns cartórios
# estampam por cima de um estatuto ESCANEADO. Esse carimbo tem texto digital,
# então a página parecia "digital" e pulava o OCR — perdendo o corpo real do
# documento (foi o caso de um estatuto que vinha com 0 artigos lidos).
_CARIMBO_FORTE = _re.compile(
    r"rcpj|iti\.gov\.br|assinad[oa] digitalmente|documento foi registrado",
    _re.IGNORECASE)


def _so_carimbo(txt):
    """True quando o texto 'digital' da página é só o carimbo de registro/
    assinatura digital (RCPJ/ITI) — sinal de que o conteúdo real está numa
    imagem atrás e a página precisa ir para o OCR. Páginas de texto digital
    de verdade têm muito mais que isto, então o limite de tamanho as poupa."""
    return len(txt) < 900 and bool(_CARIMBO_FORTE.search(txt))


def extrair_paginas(arquivo, progresso=None):
    """
    Lista de páginas: {"pagina", "texto", "extra", "origem", "conf"}.
    origem ∈ {"digital", "ocr", "escaneada", "erro"}; "extra" = 2ª leitura
    (carimbos) quando feita. progresso(feitas, total) a cada página de OCR.
    """
    pdf_bytes = _bytes(arquivo)
    erro = [{"pagina": 1, "texto": "", "extra": "", "origem": "erro", "conf": 0.0}]
    if not pdf_bytes:
        return erro

    # Foto/scan enviado como imagem (JPEG/PNG/…): lê por OCR direto, sem PDF.
    if _eh_imagem(pdf_bytes):
        try:
            return _ler_imagem(pdf_bytes)
        except Exception:
            return erro

    paginas = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for i, pg in enumerate(pdf.pages):
                    try:
                        limpa = pg.filter(lambda o: o.get("upright", True))
                        txt = (limpa.extract_text() or "").strip()
                    except Exception:
                        txt = (pg.extract_text() or "").strip()
                    digital = len(txt) >= MIN_CHARS and not _so_carimbo(txt)
                    paginas.append({"pagina": i + 1, "texto": txt, "extra": "",
                                    "origem": "digital" if digital else "escaneada",
                                    "conf": 1.0 if digital else 0.0})
        except Exception:
            paginas = []
    # PDF que o pdfplumber não abriu (0 páginas ou erro): tenta pelo renderizador.
    if not paginas:
        paginas = _paginas_por_pdfium(pdf_bytes)
    if not paginas:
        return erro

    faltam = [p for p in paginas if p["origem"] == "escaneada"]
    if faltam and ocr_disponivel():
        idx = [p["pagina"] - 1 for p in faltam]
        carimbo = set(idx[:PAGINAS_CARIMBO] + idx[-PAGINAS_CARIMBO:])
        por_idx = {p["pagina"] - 1: p for p in faltam}
        total = len(idx)
        feitas = 0
        if progresso:
            progresso(0, total)
        workers = max(1, min(_WORKERS, total))
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futuros = [ex.submit(_ocr_uma_pagina, pdf_bytes, i, i in carimbo) for i in idx]
                for fut in as_completed(futuros):
                    i, txt, conf, extra = fut.result()
                    p = por_idx.get(i)
                    if p is not None:
                        if txt.strip():
                            p.update(texto=txt, origem="ocr", conf=conf)
                        if extra:
                            p["extra"] = extra
                    feitas += 1
                    if progresso:
                        progresso(feitas, total)
        except Exception:
            pass
        # Reentrada: páginas que ficaram vazias (falha transitória do OCR sob
        # carga — some quando a entidade tem dois PDFs grandes juntos) ganham
        # UMA segunda tentativa, agora sequencial (sem concorrência de threads).
        restantes = [p["pagina"] - 1 for p in faltam if p["origem"] == "escaneada"]
        if restantes:
            for i in restantes:
                _ii, txt, conf, extra = _ocr_uma_pagina(pdf_bytes, i, i in carimbo)
                p = por_idx.get(i)
                if p is not None and txt.strip():
                    p.update(texto=txt, origem="ocr", conf=conf)
                    if extra:
                        p["extra"] = extra
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
