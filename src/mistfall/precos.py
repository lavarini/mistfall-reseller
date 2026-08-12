import cv2
import numpy as np
import pytesseract

_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"

def ler_preco(recorte: np.ndarray) -> int | None:
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(
        ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    texto = pytesseract.image_to_string(binaria, config=_CONFIG).strip()
    return int(texto) if texto.isdigit() else None
