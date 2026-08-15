import json

import pytest

from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.tipos import ItemAlvo, SlotArmazem
from mistfall.venda import (
    CENTRO_PRECO_VENDA,
    CENTRO_QUANTIDADE_VENDA,
    DesfechoVenda,
    RitmoVenda,
    executar_venda,
)
from mistfall.venda_visao import centro_slot_armazem


STASH = "images/venda-stash-2.png"
MODAL = "images/modal-venda-broche.png"
SLOT = SlotArmazem(6, 1, ItemAlvo.BROCHE, 3)


def test_executa_um_stack_de_tres_com_preco_configurado(tmp_path):
    tela = TelaFalsa([STASH, MODAL, STASH])
    mao = MaoFalsa()
    resultado = executar_venda(
        tela, mao, SLOT, 226, tmp_path, ritmo=RitmoVenda.instantaneo()
    )
    assert mao.acoes == [
        ("clicar", *centro_slot_armazem(SLOT)),
        ("clicar", *CENTRO_PRECO_VENDA),
        ("selecionar_tudo",),
        ("digitar_numero", 226),
        ("clicar", *CENTRO_QUANTIDADE_VENDA),
        ("selecionar_tudo",),
        ("digitar_numero", 3),
        ("apertar_espaco",),
    ]
    assert resultado.desfecho is DesfechoVenda.VENDEU
    assert resultado.quantidade == 3


def test_nao_digita_nem_confirma_quando_janela_nao_abre(tmp_path):
    mao = MaoFalsa()
    resultado = executar_venda(
        TelaFalsa([STASH]), mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )
    assert mao.acoes == [("clicar", *centro_slot_armazem(SLOT))]
    assert resultado.desfecho is DesfechoVenda.ABORTOU
    assert "nao abriu" in resultado.motivo


def test_nao_repete_espaco_quando_janela_nao_fecha(tmp_path):
    mao = MaoFalsa()
    resultado = executar_venda(
        TelaFalsa([STASH, MODAL]), mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )
    assert mao.acoes.count(("apertar_espaco",)) == 1
    assert resultado.desfecho is DesfechoVenda.ABORTOU
    assert "nao fechou" in resultado.motivo


@pytest.mark.parametrize("preco", [0, -1, True, 2.5])
def test_preco_invalido_aborta_antes_de_io(tmp_path, preco):
    tela = TelaFalsa([STASH])
    mao = MaoFalsa()
    with pytest.raises(ValueError, match="Preco de Venda"):
        executar_venda(tela, mao, SLOT, preco, tmp_path)
    assert tela.capturas_feitas == 0
    assert mao.acoes == []


def test_relatorio_e_gravado_quando_mao_falha_no_meio(tmp_path):
    class MaoQueFalha(MaoFalsa):
        def digitar_numero(self, numero):
            raise OSError("teclado falhou")

    with pytest.raises(OSError, match="teclado falhou"):
        executar_venda(
            TelaFalsa([STASH, MODAL]), MaoQueFalha(), SLOT, 226, tmp_path,
            ritmo=RitmoVenda.instantaneo(),
        )
    relatorio = json.loads((tmp_path / "relatorio.json").read_text())
    assert relatorio["desfecho"] == "abortou"
    assert relatorio["item"] == "broche"
