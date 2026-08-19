"""Detectores visuais puros da aba Comprar."""

from enum import Enum

import cv2
import numpy as np


# O texto do toast fica sempre no vazio entre as duas colunas de listagens.
REGIAO_TEXTO_TOAST = (1000, 345, 1500, 385)
LIMIAR_TEXTO_CLARO = 85
PROPORCAO_MINIMA_TOAST = 0.02
PROPORCAO_INVENTARIO_CHEIO = 0.20

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


def _proporcao_texto_claro(img: np.ndarray) -> float:
    # A conversao para luminancia remove a variacao entre o dourado do aviso de
    # Inventario e o cinza do aviso de sucesso antes de medir o texto.
    cinza = cv2.cvtColor(_recortar(img, REGIAO_TEXTO_TOAST), cv2.COLOR_BGR2GRAY)
    return float((cinza >= LIMIAR_TEXTO_CLARO).mean())


def detectar_mensagem_compra(img: np.ndarray) -> MensagemCompra:
    proporcao = _proporcao_texto_claro(img)
    if proporcao < PROPORCAO_MINIMA_TOAST:
        return MensagemCompra.NENHUMA
    if proporcao >= PROPORCAO_INVENTARIO_CHEIO:
        return MensagemCompra.INVENTARIO_CHEIO
    return MensagemCompra.SUCESSO


def filtro_roxo_ativo(img: np.ndarray) -> bool:
    hsv = cv2.cvtColor(_recortar(img, REGIAO_ICONE_ROXO), cv2.COLOR_BGR2HSV)
    roxo = (
        (hsv[:, :, 0] >= MATIZ_ROXO[0])
        & (hsv[:, :, 0] <= MATIZ_ROXO[1])
        & (hsv[:, :, 1] >= SATURACAO_MINIMA_ROXO)
        & (hsv[:, :, 2] >= VALOR_MINIMO_ROXO)
    )
    return float(roxo.mean()) >= PROPORCAO_MINIMA_ROXO
