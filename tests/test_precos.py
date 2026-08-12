import cv2
import numpy as np
import pytest
from mistfall.geometria import recorte_preco
from mistfall.precos import ler_preco

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

ESPERADO = {
    (0, 0): 191, (0, 1): 199,
    (1, 0): 234, (1, 1): 234,
    (2, 0): 237, (2, 1): 239,
    (3, 0): 250, (3, 1): 258,
    (4, 0): 260, (4, 1): 269,
    (5, 0): 295, (5, 1): 388,
}

@pytest.fixture(scope="module")
def img():
    return cv2.imread(PRINT)

@pytest.mark.parametrize("slot,preco", sorted(ESPERADO.items()))
def test_le_o_preco_de_cada_slot(img, slot, preco):
    linha, coluna = slot
    assert ler_preco(recorte_preco(img, linha, coluna)) == preco

def test_recorte_vazio_devolve_none():
    assert ler_preco(np.zeros((45, 80, 3), dtype=np.uint8)) is None
