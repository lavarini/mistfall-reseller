"""Leitura dentro da Janela de Confirmacao.

E visao pura — imagem para dado. Nao tem nada de IO, e por isso nao vive
em perifericos.

As regioes foram medidas contra images/janela.png, que le 237 no Preco
Unitario, 1 na Quantidade e 237 no Preco Total.
"""

import cv2
import numpy as np
import pytesseract

from mistfall.geometria import conferir_resolucao
from mistfall.itens import identificar_item
from mistfall.tipos import ItemAlvo

PRECO_UNITARIO_REL = (1500, 628, 1900, 674)
QUANTIDADE_REL = (1500, 730, 1900, 776)
PRECO_TOTAL_REL = (1500, 826, 1900, 872)
# O recorte do icone tem 116x128 — exatamente a dimensao da regiao de busca
# da lista, entao os sete templates existentes servem sem adaptacao.
ICONE_JANELA_REL = (1390, 448, 1518, 564)

_CONFIG_OCR = "--psm 7 -c tessedit_char_whitelist=0123456789"


def _numero(img: np.ndarray, regiao: tuple[int, int, int, int]) -> int | None:
    conferir_resolucao(img)
    x0, y0, x1, y1 = regiao
    cinza = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    texto = pytesseract.image_to_string(binaria, config=_CONFIG_OCR).strip()
    return int(texto) if texto.isdigit() else None


def ler_preco_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, PRECO_UNITARIO_REL)


def ler_quantidade_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, QUANTIDADE_REL)


def ler_preco_total_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, PRECO_TOTAL_REL)


def ler_item_da_janela(img: np.ndarray) -> ItemAlvo | None:
    conferir_resolucao(img)
    x0, y0, x1, y1 = ICONE_JANELA_REL
    return identificar_item(img[y0:y1, x0:x1])
