import cv2
import numpy as np
import pytest

from mistfall.tipos import Bau, CapacidadeVenda, ItemAlvo, SlotArmazem
from mistfall.venda_visao import (
    PainelItens,
    caixa_slot_armazem,
    centro_bau,
    centro_slot_armazem,
    eh_janela_venda,
    eh_tela_venda,
    escolher_slot_de_venda,
    REGIAO_CAPACIDADE,
    ler_bau_selecionado,
    ler_capacidade,
    ler_painel_itens,
    varrer_armazem,
)


@pytest.fixture
def stash_2():
    return cv2.imread("images/venda-stash-2.png")


@pytest.fixture
def stash_3():
    return cv2.imread("images/venda-stash-3.png")


def test_le_capacidade_nas_duas_telas_de_armazem(stash_2, stash_3):
    esperado = CapacidadeVenda(ocupadas=0, limite=12)
    assert ler_capacidade(stash_2) == esperado
    assert ler_capacidade(stash_3) == esperado


def test_regiao_de_capacidade_tem_largura_para_contador_de_dois_digitos():
    x0, _, x1, _ = REGIAO_CAPACIDADE
    assert x1 - x0 >= 105

def test_detecta_bau_dourado_selecionado(stash_2, stash_3):
    assert ler_bau_selecionado(stash_2) is Bau.SEGUNDO
    assert ler_bau_selecionado(stash_3) is Bau.TERCEIRO


def test_detecta_painel_armazem_selecionado(stash_2):
    assert ler_painel_itens(stash_2) is PainelItens.ARMAZEM


def test_tela_com_resgate_continua_como_tela_de_venda():
    imagem = cv2.imread("images/tela-venda-resgatar.png")
    assert ler_painel_itens(imagem) is PainelItens.ARMAZEM
    assert eh_tela_venda(imagem)
    assert ler_capacidade(imagem) == CapacidadeVenda(0, 15)


def test_modal_com_resgate_continua_como_janela_de_venda():
    imagem = cv2.imread("images/modal-venda-resgatar.png")
    assert eh_janela_venda(imagem)


def test_varredura_mapeia_slots_com_quatro_trabalhadores(monkeypatch):
    chamada = {}

    def mapear(funcao, itens, trabalhadores):
        chamada["trabalhadores"] = trabalhadores
        itens = list(itens)
        chamada["itens"] = itens
        return [funcao(item) for item in itens]

    monkeypatch.setattr("mistfall.venda_visao.mapear", mapear)
    monkeypatch.setattr(
        "mistfall.venda_visao._identificar_item_do_slot",
        lambda _: None,
    )

    resultado = varrer_armazem(np.zeros((1440, 2560, 3), dtype=np.uint8))

    assert chamada["trabalhadores"] == 4
    assert len(chamada["itens"]) == 56
    assert [(slot.linha, slot.coluna) for slot in resultado] == [
        (linha, coluna)
        for linha in range(7)
        for coluna in range(8)
    ]


def test_painel_de_itens_ambiguo_e_recusado(monkeypatch, stash_2):
    monkeypatch.setattr(
        "mistfall.venda_visao._proporcoes_douradas_abas",
        lambda _: [0.16, 0.16],
    )
    assert ler_painel_itens(stash_2) is None


def test_detecta_inventario_quando_primeiro_titulo_esta_dourado(monkeypatch, stash_2):
    monkeypatch.setattr(
        "mistfall.venda_visao._proporcoes_douradas_abas",
        lambda _: [0.163, 0.110],
    )
    assert ler_painel_itens(stash_2) is PainelItens.INVENTARIO


def test_geometria_tem_8_colunas_e_7_linhas_sem_sobrepor():
    caixas = [caixa_slot_armazem(l, c) for l in range(7) for c in range(8)]
    assert len(set(caixas)) == 56
    for esquerda in caixas:
        x0, y0, x1, y1 = esquerda
        assert 0 <= x0 < x1 <= 2560
        assert 0 <= y0 < y1 <= 1440


def test_ultima_coluna_fica_alinhada_com_a_grade_real():
    x0, _, x1, _ = caixa_slot_armazem(4, 7)
    assert (x0, x1) == (2342, 2425)


def test_centro_de_cada_bau_e_distinto():
    assert len({centro_bau(bau) for bau in Bau}) == 4


def test_capacidade_incoerente_e_recusada(monkeypatch, stash_2):
    monkeypatch.setattr("mistfall.venda_visao._ocr_capacidade", lambda _: "13/12")
    assert ler_capacidade(stash_2) is None


def test_capacidade_com_limite_zero_e_recusada(monkeypatch, stash_2):
    monkeypatch.setattr("mistfall.venda_visao._ocr_capacidade", lambda _: "0/0")
    assert ler_capacidade(stash_2) is None


def test_capacidade_ilegivel_e_recusada(monkeypatch, stash_2):
    monkeypatch.setattr("mistfall.venda_visao._ocr_capacidade", lambda _: "")
    assert ler_capacidade(stash_2) is None


def test_bau_ambiguo_e_recusado(monkeypatch, stash_2):
    monkeypatch.setattr(
        "mistfall.venda_visao._proporcoes_douradas", lambda _: [0.8, 0.8, 0.0, 0.0]
    )
    assert ler_bau_selecionado(stash_2) is None


def test_resolucao_errada_e_erro():
    with pytest.raises(ValueError, match="2560x1440"):
        ler_capacidade(np.zeros((720, 1280, 3), dtype=np.uint8))


def test_bau_dois_le_os_tres_stacks_de_broche(stash_2):
    por_posicao = {(s.linha, s.coluna): s for s in varrer_armazem(stash_2)}
    assert por_posicao[(6, 1)] == SlotArmazem(6, 1, ItemAlvo.BROCHE, 3)
    assert por_posicao[(6, 2)] == SlotArmazem(6, 2, ItemAlvo.BROCHE, 3)
    assert por_posicao[(6, 3)] == SlotArmazem(6, 3, ItemAlvo.BROCHE, 2)


def test_bau_dois_escolhe_primeiro_stack_tres_em_ordem_visual(stash_2):
    escolhido = escolher_slot_de_venda(varrer_armazem(stash_2))
    assert escolhido == SlotArmazem(6, 1, ItemAlvo.BROCHE, 3)


def test_bau_tres_le_os_stacks_alvo_da_primeira_linha(stash_3):
    por_posicao = {(s.linha, s.coluna): s for s in varrer_armazem(stash_3)}
    assert por_posicao[(0, 0)] == SlotArmazem(0, 0, ItemAlvo.ORBE, 3)
    assert por_posicao[(0, 1)] == SlotArmazem(0, 1, ItemAlvo.ORBE, 2)
    assert por_posicao[(0, 2)] == SlotArmazem(0, 2, ItemAlvo.REDE, 3)
    assert por_posicao[(0, 3)] == SlotArmazem(0, 3, ItemAlvo.REDE, 3)
    assert por_posicao[(0, 6)] == SlotArmazem(0, 6, ItemAlvo.LANTERNA, 3)
    assert por_posicao[(0, 7)] == SlotArmazem(0, 7, ItemAlvo.LANTERNA, 3)


def test_quantidade_ausente_nunca_vira_um_implicitamente(stash_3):
    por_posicao = {(s.linha, s.coluna): s for s in varrer_armazem(stash_3)}
    assert por_posicao[(0, 4)].item is ItemAlvo.REDE
    assert por_posicao[(0, 4)].quantidade is None


def test_so_item_alvo_com_quantidade_tres_e_escolhido():
    slots = [
        SlotArmazem(0, 0, ItemAlvo.BROCHE, 2),
        SlotArmazem(0, 1, None, 3),
        SlotArmazem(0, 2, ItemAlvo.ADAGA, None),
        SlotArmazem(0, 3, ItemAlvo.ADAGA, 3),
    ]
    assert escolher_slot_de_venda(slots) == slots[-1]


def test_centro_do_slot_fica_dentro_da_caixa():
    slot = SlotArmazem(2, 4, ItemAlvo.ORBE, 3)
    x, y = centro_slot_armazem(slot)
    x0, y0, x1, y1 = caixa_slot_armazem(2, 4)
    assert x0 < x < x1
    assert y0 < y < y1
