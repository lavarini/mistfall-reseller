import cv2
import numpy as np
from ferramentas.anotar import anotar
from mistfall.leilao import varrer

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

def test_devolve_imagem_do_mesmo_tamanho():
    img = cv2.imread(PRINT)
    saida = anotar(img, varrer(img))
    assert saida.shape == img.shape

def test_nao_altera_a_imagem_original():
    img = cv2.imread(PRINT)
    copia = img.copy()
    anotar(img, varrer(img))
    assert np.array_equal(img, copia)

def test_desenha_alguma_coisa():
    img = cv2.imread(PRINT)
    saida = anotar(img, varrer(img))
    assert not np.array_equal(saida, img)
