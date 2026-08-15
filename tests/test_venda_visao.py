import cv2
import numpy as np
import pytest

from mistfall.tipos import Bau, CapacidadeVenda
from mistfall.venda_visao import (
    caixa_slot_armazem,
    centro_bau,
    ler_bau_selecionado,
    ler_capacidade,
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

def test_detecta_bau_dourado_selecionado(stash_2, stash_3):
    assert ler_bau_selecionado(stash_2) is Bau.SEGUNDO
    assert ler_bau_selecionado(stash_3) is Bau.TERCEIRO


def test_geometria_tem_8_colunas_e_7_linhas_sem_sobrepor():
    caixas = [caixa_slot_armazem(l, c) for l in range(7) for c in range(8)]
    assert len(set(caixas)) == 56
    for esquerda in caixas:
        x0, y0, x1, y1 = esquerda
        assert 0 <= x0 < x1 <= 2560
        assert 0 <= y0 < y1 <= 1440


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
