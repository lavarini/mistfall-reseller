import cv2
import pytest
from mistfall.geometria import TODOS_OS_SLOTS, regiao_icone
from mistfall.itens import identificar_item, pontuar
from mistfall.tipos import ItemAlvo

FONTE = "images/broche-tres-adaga-lanterna-rede-padrao.png"
# Print diferente do que gerou os templates. Foi ele que expos o bug de
# template do mesmo tamanho da busca: quatro Itens-alvo sumiam aqui.
OUTRO = "images/broche-dragao-orbe-codice-padrao.png"

ALVOS_FONTE = {
    (0, 0): ItemAlvo.BROCHE,
    (0, 1): ItemAlvo.ADAGA,
    (1, 1): ItemAlvo.LANTERNA,
    (3, 0): ItemAlvo.DRAGAO,
    (3, 1): ItemAlvo.ORBE,
    (4, 0): ItemAlvo.REDE,
    (5, 0): ItemAlvo.CODICE,
}
NAO_ALVOS_FONTE = [(1, 0), (2, 0), (2, 1), (4, 1), (5, 1)]

ALVOS_OUTRO = {
    (0, 0): ItemAlvo.BROCHE,
    (0, 1): ItemAlvo.ADAGA,
    (2, 1): ItemAlvo.DRAGAO,
    (3, 0): ItemAlvo.ORBE,
    (4, 0): ItemAlvo.LANTERNA,
    (4, 1): ItemAlvo.CODICE,
    (5, 0): ItemAlvo.REDE,
}

@pytest.fixture(scope="module")
def fonte():
    return cv2.imread(FONTE)

@pytest.fixture(scope="module")
def outro():
    return cv2.imread(OUTRO)

@pytest.mark.parametrize("slot,item", sorted(ALVOS_FONTE.items()))
def test_identifica_cada_item_alvo(fonte, slot, item):
    assert identificar_item(regiao_icone(fonte, *slot)) is item

@pytest.mark.parametrize("slot", NAO_ALVOS_FONTE)
def test_rejeita_o_que_nao_e_item_alvo(fonte, slot):
    assert identificar_item(regiao_icone(fonte, *slot)) is None

@pytest.mark.parametrize("slot,item", sorted(ALVOS_OUTRO.items()))
def test_identifica_em_print_que_nao_gerou_os_templates(outro, slot, item):
    assert identificar_item(regiao_icone(outro, *slot)) is item

def test_acha_os_sete_itens_alvo_no_outro_print(outro):
    achados = {
        slot: identificar_item(regiao_icone(outro, *slot))
        for slot in TODOS_OS_SLOTS
    }
    assert {s: i for s, i in achados.items() if i} == ALVOS_OUTRO

def test_margem_sobre_o_segundo_colocado_e_folgada(outro):
    for slot in ALVOS_OUTRO:
        ranking = sorted(pontuar(regiao_icone(outro, *slot)).values(), reverse=True)
        assert ranking[0] - ranking[1] > 0.20, slot
