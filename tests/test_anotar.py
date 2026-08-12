import cv2
import numpy as np
from ferramentas.anotar import VERDE, VERMELHO, anotar
from mistfall.geometria import caixa_slot
from mistfall.leilao import varrer
from mistfall.tipos import ItemAlvo, Listagem

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

def _imagem_sintetica():
    return np.zeros((1440, 2560, 3), dtype=np.uint8)

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

def test_cor_indica_item_alvo_ou_nao():
    img = _imagem_sintetica()
    listagens = [
        Listagem(linha=0, coluna=0, item=ItemAlvo.BROCHE, preco_unitario=188),
        Listagem(linha=0, coluna=1, item=None, preco_unitario=None),
    ]
    saida = anotar(img, listagens)

    x0, y0, _, _ = caixa_slot(0, 0)
    assert tuple(saida[y0, x0 + 50]) == VERDE

    x0, y0, _, _ = caixa_slot(0, 1)
    assert tuple(saida[y0, x0 + 50]) == VERMELHO

def test_preco_ausente_nao_quebra_e_usa_o_placeholder():
    img = _imagem_sintetica()
    listagem = Listagem(linha=0, coluna=0, item=ItemAlvo.BROCHE, preco_unitario=None)

    saida = anotar(img, [listagem])

    esperado = img.copy()
    x0, y0, x1, y1 = caixa_slot(0, 0)
    cv2.rectangle(esperado, (x0, y0), (x1, y1), VERDE, 2)
    cv2.putText(
        esperado,
        "broche ??",
        (x0 + 200, y0 + 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        VERDE,
        2,
    )

    assert np.array_equal(saida, esperado)
