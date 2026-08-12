import cv2
import pytest
from mistfall.leilao import varrer
from mistfall.tipos import ItemAlvo

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

@pytest.fixture(scope="module")
def listagens():
    return varrer(cv2.imread(PRINT))

def test_devolve_os_doze_slots(listagens):
    assert len(listagens) == 12

def test_vem_em_ordem_de_leitura(listagens):
    # Lista literal de propósito: comparar com sorted(posicoes) seria
    # tautológico, porque TODOS_OS_SLOTS já nasce ordenado por construção.
    posicoes = [(l.linha, l.coluna) for l in listagens]
    assert posicoes == [
        (0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1),
        (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1),
    ]

def test_encontra_os_sete_itens_alvo(listagens):
    achados = {l.item for l in listagens if l.item is not None}
    assert achados == set(ItemAlvo)

def test_casa_item_com_o_preco_do_mesmo_slot(listagens):
    por_item = {l.item: l.preco_unitario for l in listagens if l.item}
    assert por_item[ItemAlvo.BROCHE] == 191
    assert por_item[ItemAlvo.ADAGA] == 199
    assert por_item[ItemAlvo.CODICE] == 295

def test_le_preco_mesmo_de_slot_que_nao_e_alvo(listagens):
    nao_alvo = [l for l in listagens if l.item is None]
    assert all(l.preco_unitario is not None for l in nao_alvo)
