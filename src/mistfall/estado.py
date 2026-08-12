import cv2
import numpy as np
from mistfall.tipos import EstadoTela

REGIAO_JANELA = (900, 500, 1700, 950)
REGIAO_MENU = (80, 380, 360, 720)

# Janela de Confirmacao escurece o centro: 4.9 contra 11.5-13.3 do resto.
LIMIAR_JANELA = 8.0
# Material de Construcao selecionada da 37.1; outra Categoria da 32.9.
LIMIAR_MENU = 35.0

def _brilho(img: np.ndarray, regiao: tuple[int, int, int, int]) -> float:
    x0, y0, x1, y1 = regiao
    return float(cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).mean())

def identificar_estado(img: np.ndarray) -> EstadoTela:
    if _brilho(img, REGIAO_JANELA) < LIMIAR_JANELA:
        return EstadoTela.JANELA_CONFIRMACAO
    if _brilho(img, REGIAO_MENU) < LIMIAR_MENU:
        return EstadoTela.OUTRA_CATEGORIA
    return EstadoTela.LISTA
