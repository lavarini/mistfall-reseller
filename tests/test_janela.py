import cv2
import numpy as np
import pytest
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_quantidade_da_janela, ler_preco_total_da_janela,
    pontuar_icone_da_janela,
)
from mistfall.tipos import ItemAlvo

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

def test_nenhuma_escala_promove_o_item_que_nao_e_alvo(modal):
    # O unico negativo real que existe. A varredura de escala experimenta
    # sete tamanhos do icone, e o risco dela e justamente inventar um
    # positivo: em alguma escala o Espelho Adornado passar a casar.
    #
    # Os limiares aparecem aqui como numero, e nao importados de itens.py,
    # de proposito: importar faria o teste concordar com qualquer valor que
    # o modulo passasse a ter.
    _, scores = pontuar_icone_da_janela(modal)
    melhor, segundo = sorted(scores.values(), reverse=True)[:2]
    assert melhor < 0.70, f"melhor score {melhor} passou do limiar"
    assert melhor - segundo < 0.25, "margem folgada demais para um negativo"

def test_pontuar_o_icone_devolve_um_score_por_item_alvo(modal):
    escala, scores = pontuar_icone_da_janela(modal)
    assert set(scores) == set(ItemAlvo)
    assert 0.85 <= escala <= 1.15

@pytest.mark.parametrize("funcao", [
    ler_item_da_janela,
    ler_preco_da_janela,
    ler_quantidade_da_janela,
    ler_preco_total_da_janela,
    pontuar_icone_da_janela,
])
def test_rejeita_resolucao_errada(funcao):
    pequena = np.zeros((720, 1280, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2560x1440"):
        funcao(pequena)
