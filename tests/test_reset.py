import pytest

from mistfall.geometria import (
    CATEGORIA_MATERIAL_CONSTRUCAO,
    CATEGORIA_MATERIAL_FORJA,
)
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.piloto import Ritmo
from mistfall.reset import resetar_categoria


JA = Ritmo.instantaneo()
FORJA = "images/reset-forja.png"
LISTA = "images/broche-dragao-orbe-codice-padrao.png"


def test_reset_clica_forja_e_depois_material_de_construcao():
    mao = MaoFalsa()

    assert resetar_categoria(TelaFalsa([FORJA, LISTA]), mao, JA) is True
    assert mao.acoes == [
        ("clicar", *CATEGORIA_MATERIAL_FORJA),
        ("clicar", *CATEGORIA_MATERIAL_CONSTRUCAO),
    ]


@pytest.mark.parametrize(
    "roteiro",
    [
        [LISTA, LISTA],
        [FORJA, FORJA],
    ],
)
def test_reset_so_tem_sucesso_quando_as_duas_transicoes_sao_confirmadas(roteiro):
    assert resetar_categoria(TelaFalsa(roteiro), MaoFalsa(), JA) is False
