import cv2
import numpy as np
import pytesseract

# Medida e validada nos nove prints em que o Ouro e legivel.
CAIXA_OURO = (2350, 119, 2475, 160)
_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789,"

def ler_ouro(img: np.ndarray) -> int | None:
    x0, y0, x1, y1 = CAIXA_OURO
    cinza = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    texto = pytesseract.image_to_string(binaria, config=_CONFIG).strip().replace(",", "")
    return int(texto) if texto.isdigit() else None
