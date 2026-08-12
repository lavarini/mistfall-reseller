import cv2
import numpy as np
from mistfall.tipos import EstadoTela

REGIAO_CENTRO = (900, 500, 1700, 950)
REGIAO_MENU = (80, 380, 360, 720)

# Cada estado exige evidencia positiva em ambas as regioes.
# Janela de Confirmacao escurece o centro (4.9) e mantem menu num intervalo intermediario (18.3).
CENTRO_JANELA_MAX = 8.0
MENU_JANELA = (12.0, 25.0)

# Lista e reset: centro normal (11.5-13.3), menu claro (37.1 para Material de Construcao).
CENTRO_LISTA = (9.0, 18.0)
MENU_MATERIAL = (35.0, 40.0)

# Outra Categoria: centro normal, menu mais escuro (32.9).
MENU_OUTRA_CATEGORIA = (28.0, 35.0)

def _brilho(img: np.ndarray, regiao: tuple[int, int, int, int]) -> float:
    x0, y0, x1, y1 = regiao
    return float(cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).mean())

def _dentro_faixa(valor: float, faixa: tuple[float, float]) -> bool:
    return faixa[0] <= valor <= faixa[1]

def identificar_estado(img: np.ndarray) -> EstadoTela:
    centro = _brilho(img, REGIAO_CENTRO)
    menu = _brilho(img, REGIAO_MENU)

    # Janela de Confirmacao: centro muito escuro E menu numa faixa intermediaria.
    if centro < CENTRO_JANELA_MAX and _dentro_faixa(menu, MENU_JANELA):
        return EstadoTela.JANELA_CONFIRMACAO

    # Lista: centro normal E menu muito claro (Material de Construcao).
    if _dentro_faixa(centro, CENTRO_LISTA) and _dentro_faixa(menu, MENU_MATERIAL):
        return EstadoTela.LISTA

    # Outra Categoria: centro normal E menu moderado.
    if _dentro_faixa(centro, CENTRO_LISTA) and _dentro_faixa(menu, MENU_OUTRA_CATEGORIA):
        return EstadoTela.OUTRA_CATEGORIA

    # Qualquer outra combinacao: desconhecido.
    return EstadoTela.DESCONHECIDO
