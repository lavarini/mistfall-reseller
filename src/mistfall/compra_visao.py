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
# O filtro nao se detecta pela cor do losango, e sim pela MARCA de selecao que
# o jogo poe por cima dele: uma borda branca e um tique dourado. Medir o roxo
# le o sinal invertido — a marca COBRE o roxo, entao a proporcao de roxo cai
# quando o filtro liga (0.116 desligado contra 0.053 ligado) e nenhum limiar
# separa os dois estados no sentido esperado.
MATIZ_TIQUE = (15, 40)
SATURACAO_MINIMA_TIQUE = 100
VALOR_MINIMO_TIQUE = 120
SATURACAO_MAXIMA_BORDA = 60
VALOR_MINIMO_BORDA = 170
# Medido no corpus: 0.0000 nos dois sinais com o filtro desligado, contra
# 0.047 (tique) e 0.078 (borda) com ele ligado. O limiar fica no meio do vao.
PROPORCAO_MINIMA_MARCA = 0.02


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
    tique = (
        (hsv[:, :, 0] >= MATIZ_TIQUE[0])
        & (hsv[:, :, 0] <= MATIZ_TIQUE[1])
        & (hsv[:, :, 1] >= SATURACAO_MINIMA_TIQUE)
        & (hsv[:, :, 2] >= VALOR_MINIMO_TIQUE)
    )
    borda = (
        (hsv[:, :, 1] <= SATURACAO_MAXIMA_BORDA)
        & (hsv[:, :, 2] >= VALOR_MINIMO_BORDA)
    )
    # Qualquer uma das duas basta. Falso negativo aqui e o erro caro: ele faz
    # `garantir_filtro_roxo` clicar num filtro que ja estava ligado, o que o
    # DESLIGA.
    return (
        float(tique.mean()) >= PROPORCAO_MINIMA_MARCA
        or float(borda.mean()) >= PROPORCAO_MINIMA_MARCA
    )
