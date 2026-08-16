import random

import pytest

from mistfall.geometria import (
    CATEGORIA_CHAVE,
    CATEGORIA_MATERIAL_CONSTRUCAO,
    CATEGORIA_MATERIAL_FORJA,
    area_clique_categoria,
)
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.piloto import Ritmo
from mistfall.reset import CategoriaAlternativa, resetar_categoria


JA = Ritmo.instantaneo()
FORJA = "images/reset-forja.png"
LISTA = "images/broche-dragao-orbe-codice-padrao.png"


def _dentro(ponto, area):
    x, y = ponto
    x0, y0, x1, y1 = area
    return x0 <= x <= x1 and y0 <= y <= y1


def test_reset_clica_forja_e_depois_material_em_areas_seguras():
    mao = MaoFalsa()

    assert resetar_categoria(
        TelaFalsa([FORJA, LISTA]), mao, JA, sorteio=random.Random(1),
    ) is True
    assert len(mao.acoes) == 2
    assert _dentro(mao.acoes[0][1:], area_clique_categoria(CATEGORIA_MATERIAL_FORJA))
    assert _dentro(
        mao.acoes[1][1:], area_clique_categoria(CATEGORIA_MATERIAL_CONSTRUCAO),
    )


def test_reset_pode_usar_chave_como_categoria_alternativa():
    mao = MaoFalsa()

    assert resetar_categoria(
        TelaFalsa(["images/reset-chave.png", LISTA]),
        mao,
        JA,
        categoria_alternativa=CategoriaAlternativa.CHAVE,
        sorteio=random.Random(1),
    ) is True
    assert len(mao.acoes) == 2
    assert _dentro(mao.acoes[0][1:], area_clique_categoria(CATEGORIA_CHAVE))
    assert _dentro(
        mao.acoes[1][1:], area_clique_categoria(CATEGORIA_MATERIAL_CONSTRUCAO),
    )


class SorteioEspiao(random.Random):
    def __init__(self, semente):
        super().__init__(semente)
        self.chamadas = []

    def randint(self, minimo, maximo):
        self.chamadas.append((minimo, maximo))
        return super().randint(minimo, maximo)


def _cliques_do_reset(semente):
    mao = MaoFalsa()
    resetar_categoria(
        TelaFalsa([FORJA, LISTA]), mao, JA,
        sorteio=random.Random(semente),
    )
    return [acao[1:] for acao in mao.acoes]


def test_os_dois_cliques_usam_a_mesma_instancia_injetada():
    sorteio = SorteioEspiao(42)
    resetar_categoria(TelaFalsa([FORJA, LISTA]), MaoFalsa(), JA, sorteio=sorteio)
    assert sorteio.chamadas == [
        (160, 280), (759, 795),
        (160, 280), (687, 723),
    ]


def test_sementes_variadas_produzem_sequencias_diferentes_no_reset():
    sequencias = {tuple(_cliques_do_reset(s)) for s in range(10)}
    assert len(sequencias) > 1


def test_mesma_semente_reproduz_os_dois_cliques_do_reset():
    assert _cliques_do_reset(91) == _cliques_do_reset(91)


def test_reset_injetado_independe_do_random_global():
    random.seed(1)
    primeiro = _cliques_do_reset(73)
    random.seed(999)
    segundo = _cliques_do_reset(73)
    assert primeiro == segundo


@pytest.mark.parametrize(
    "roteiro",
    [
        [LISTA, LISTA],
        [FORJA, FORJA],
    ],
)
def test_reset_so_tem_sucesso_quando_as_duas_transicoes_sao_confirmadas(roteiro):
    mao = MaoFalsa()
    assert resetar_categoria(TelaFalsa(roteiro), mao, JA) is False
    assert len(mao.acoes) == 2
