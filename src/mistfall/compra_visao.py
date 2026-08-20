"""Detectores visuais puros da aba Comprar."""

from enum import Enum
from difflib import SequenceMatcher
import unicodedata

import cv2
import numpy as np
import pytesseract

from mistfall.geometria import conferir_resolucao


# O texto do toast fica sempre no vazio entre as duas colunas de listagens.
REGIAO_TEXTO_TOAST = (950, 345, 1800, 385)
ESCALA_OCR_TOAST = 4
CONFIG_OCR_TOAST = "--psm 7"
PALAVRA_INVENTARIO_CHEIO = "cheios"
PALAVRAS_SUCESSO = ("realizada", "guardado")
SIMILARIDADE_MINIMA_CHEIOS = 0.80

# Sexto icone da faixa de raridade: roxo com a moldura de selecao visivel.
REGIAO_ICONE_ROXO = (775, 205, 825, 255)
MATIZ_ROXO = (130, 170)
SATURACAO_MINIMA_ROXO = 80
VALOR_MINIMO_ROXO = 80
PROPORCAO_MINIMA_ROXO = 0.04


class MensagemCompra(Enum):
    SUCESSO = "sucesso"
    INVENTARIO_CHEIO = "inventario_cheio"
    NENHUMA = "nenhuma"


def _recortar(img: np.ndarray, regiao: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = regiao
    return img[y0:y1, x0:x1]


def _normalizar_texto(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(caractere for caractere in sem_acentos if not unicodedata.combining(caractere)).lower()


def _ler_toast(img: np.ndarray, adaptativo: bool) -> str:
    cinza = cv2.cvtColor(_recortar(img, REGIAO_TEXTO_TOAST), cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(
        cinza,
        None,
        fx=ESCALA_OCR_TOAST,
        fy=ESCALA_OCR_TOAST,
        interpolation=cv2.INTER_CUBIC,
    )
    if adaptativo:
        binaria = cv2.adaptiveThreshold(
            ampliado,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        )
    else:
        _, binaria = cv2.threshold(
            ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    return _normalizar_texto(
        pytesseract.image_to_string(binaria, config=CONFIG_OCR_TOAST)
    )


def _contem_cheios(texto: str) -> bool:
    return any(
        SequenceMatcher(None, palavra, PALAVRA_INVENTARIO_CHEIO).ratio()
        >= SIMILARIDADE_MINIMA_CHEIOS
        for palavra in texto.split()
    )


def detectar_mensagem_compra(img: np.ndarray) -> MensagemCompra:
    texto = _ler_toast(img, adaptativo=False)
    if any(palavra in texto for palavra in PALAVRAS_SUCESSO):
        return MensagemCompra.SUCESSO
    if _contem_cheios(_ler_toast(img, adaptativo=True)):
        return MensagemCompra.INVENTARIO_CHEIO
    return MensagemCompra.NENHUMA


def filtro_roxo_ativo(img: np.ndarray) -> bool:
    # Mesmo guardrail de `identificar_estado`: em resolucao errada o recorte
    # sai vazio, `.mean()` devolve `nan` e a resposta seria um `False`
    # silencioso. Resolucao diferente e erro, nao caso a tratar (ADR-0002).
    conferir_resolucao(img)
    hsv = cv2.cvtColor(_recortar(img, REGIAO_ICONE_ROXO), cv2.COLOR_BGR2HSV)
    roxo = (
        (hsv[:, :, 0] >= MATIZ_ROXO[0])
        & (hsv[:, :, 0] <= MATIZ_ROXO[1])
        & (hsv[:, :, 1] >= SATURACAO_MINIMA_ROXO)
        & (hsv[:, :, 2] >= VALOR_MINIMO_ROXO)
    )
    return float(roxo.mean()) >= PROPORCAO_MINIMA_ROXO
