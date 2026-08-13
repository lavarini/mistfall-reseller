import cv2
import numpy as np
import pytest
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_quantidade_da_janela, ler_preco_total_da_janela,
)

JANELA = "images/janela.png"

@pytest.fixture(scope="module")
def modal():
    return cv2.imread(JANELA)

def test_le_o_preco_unitario(modal):
    assert ler_preco_da_janela(modal) == 237

def test_le_a_quantidade(modal):
    assert ler_quantidade_da_janela(modal) == 1

def test_le_o_preco_total(modal):
    assert ler_preco_total_da_janela(modal) == 237

def test_rejeita_item_que_nao_e_alvo(modal):
    # O modal deste print mostra Espelho Adornado, que nao e Item-alvo.
    assert ler_item_da_janela(modal) is None

@pytest.mark.parametrize("funcao", [
    ler_item_da_janela,
    ler_preco_da_janela,
    ler_quantidade_da_janela,
    ler_preco_total_da_janela,
])
def test_rejeita_resolucao_errada(funcao):
    pequena = np.zeros((720, 1280, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2560x1440"):
        funcao(pequena)
