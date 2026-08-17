import json
import random

import pytest

from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.tipos import ItemAlvo, SlotArmazem
from mistfall.venda import (
    AREA_SEGURA_BOTAO_LISTAR,
    CENTRO_PRECO_VENDA,
    CENTRO_QUANTIDADE_VENDA,
    PONTO_NEUTRO_POS_VENDA,
    DesfechoVenda,
    RitmoVenda,
    executar_venda,
)
from mistfall.venda_visao import (
    CENTRO_ABA_ARMAZEM,
    PainelItens,
    centro_slot_armazem,
)


STASH = "images/venda-stash-2.png"
MODAL = "images/modal-venda-broche.png"
SLOT = SlotArmazem(6, 1, ItemAlvo.BROCHE, 3)


def dentro(ponto, area):
    x, y = ponto
    x0, y0, x1, y1 = area
    return x0 <= x <= x1 and y0 <= y <= y1


def test_ritmo_do_modal_tem_pausa_curta_e_ritmo_instantaneo_nao_espera():
    assert RitmoVenda().pausa_interacao_modal == 0.05
    assert RitmoVenda().pausa_antes_do_preco == 0.15
    assert RitmoVenda().esperas_capacidade_cheia == (1.0, 5.0, 10.0, 20.0, 30.0)
    assert RitmoVenda.instantaneo().pausa_interacao_modal == 0.0
    assert RitmoVenda.instantaneo().pausa_antes_do_preco == 0.0


def test_executa_um_stack_com_cliques_dentro_das_areas_seguras(tmp_path):
    tela = TelaFalsa([STASH, MODAL, STASH])
    mao = MaoFalsa()
    resultado = executar_venda(
        tela, mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(), sorteio=random.Random(42),
    )
    cliques = [acao[1:] for acao in mao.acoes if acao[0] == "clicar"]
    cx, cy = centro_slot_armazem(SLOT)
    assert dentro(cliques[0], (cx - 20, cy - 26, cx + 20, cy + 26))
    assert cliques[1:3] == [CENTRO_PRECO_VENDA, CENTRO_QUANTIDADE_VENDA]
    assert dentro(cliques[3], AREA_SEGURA_BOTAO_LISTAR)
    assert mao.acoes[1:7] == [
        ("clicar", *CENTRO_PRECO_VENDA),
        ("selecionar_tudo",),
        ("digitar_numero", 226),
        ("clicar", *CENTRO_QUANTIDADE_VENDA),
        ("selecionar_tudo",),
        ("digitar_numero", 3),
    ]
    indice_listar = max(
        indice for indice, acao in enumerate(mao.acoes)
        if acao[0] == "clicar" and dentro(acao[1:], AREA_SEGURA_BOTAO_LISTAR)
    )
    assert mao.acoes[indice_listar + 1] == ("mover", *PONTO_NEUTRO_POS_VENDA)
    assert ("apertar_esc",) not in mao.acoes
    assert resultado.desfecho is DesfechoVenda.VENDEU
    assert resultado.quantidade == 3


def test_recupera_inventario_e_volta_ao_armazem(monkeypatch, tmp_path):
    estados = iter([PainelItens.INVENTARIO, PainelItens.ARMAZEM])
    monkeypatch.setattr("mistfall.venda.ler_painel_itens", lambda _: next(estados))
    monkeypatch.setattr("mistfall.venda.eh_tela_venda", lambda _: True)
    mao = MaoFalsa()

    resultado = executar_venda(
        TelaFalsa([STASH, MODAL, STASH, STASH]),
        mao,
        SLOT,
        226,
        tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )

    assert resultado.desfecho is DesfechoVenda.VENDEU
    assert mao.acoes.count(("clicar", *CENTRO_ABA_ARMAZEM)) == 1
    assert mao.acoes.count(("mover", *PONTO_NEUTRO_POS_VENDA)) == 2
    assert ("apertar_esc",) not in mao.acoes
    assert resultado.armazem_reaberto is True


def test_aborta_sem_esc_quando_painel_permanece_ilegivel(monkeypatch, tmp_path):
    monkeypatch.setattr("mistfall.venda.ler_painel_itens", lambda _: None)
    mao = MaoFalsa()
    resultado = executar_venda(
        TelaFalsa([STASH, MODAL, MODAL]), mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )
    assert resultado.desfecho is DesfechoVenda.ABORTOU
    assert ("apertar_esc",) not in mao.acoes
    assert not any(
        acao == ("clicar", *CENTRO_ABA_ARMAZEM) for acao in mao.acoes
    )


def test_nao_digita_nem_confirma_quando_janela_nao_abre(tmp_path):
    mao = MaoFalsa()
    resultado = executar_venda(
        TelaFalsa([STASH]), mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )
    cliques = [acao[1:] for acao in mao.acoes if acao[0] == "clicar"]
    cx, cy = centro_slot_armazem(SLOT)
    assert len(cliques) == 1
    assert dentro(cliques[0], (cx - 20, cy - 26, cx + 20, cy + 26))
    assert mao.acoes == [("clicar", *cliques[0])]
    assert resultado.desfecho is DesfechoVenda.ABORTOU
    assert "nao abriu" in resultado.motivo


def test_nao_repete_clique_de_confirmacao_quando_janela_nao_fecha(tmp_path):
    mao = MaoFalsa()
    resultado = executar_venda(
        TelaFalsa([STASH, MODAL]), mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )
    cliques = [acao[1:] for acao in mao.acoes if acao[0] == "clicar"]
    assert sum(dentro(clique, AREA_SEGURA_BOTAO_LISTAR) for clique in cliques) == 1
    assert ("apertar_espaco",) not in mao.acoes
    assert resultado.desfecho is DesfechoVenda.ABORTOU
    assert "nao fechou" in resultado.motivo
    assert (tmp_path / "02-nao-fechou.png").exists()


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


def cliques_com_semente(tmp_path, semente):
    mao = MaoFalsa()
    executar_venda(
        TelaFalsa([STASH, MODAL, STASH]), mao, SLOT, 226,
        tmp_path / str(semente), ritmo=RitmoVenda.instantaneo(),
        sorteio=random.Random(semente),
    )
    return [acao[1:] for acao in mao.acoes if acao[0] == "clicar"]


def test_sementes_variadas_produzem_mais_de_um_ponto(tmp_path):
    sequencias = [cliques_com_semente(tmp_path, s) for s in range(10)]
    assert len({seq[0] for seq in sequencias}) > 1
    assert len({seq[3] for seq in sequencias}) > 1


def test_mesma_semente_reproduz_os_cliques(tmp_path):
    assert cliques_com_semente(tmp_path, 91) == cliques_com_semente(tmp_path, 91)


def test_sorteio_injetado_independe_do_random_global(tmp_path):
    random.seed(1)
    primeira = cliques_com_semente(tmp_path, 73)
    random.seed(999)
    segunda = cliques_com_semente(tmp_path, 73)
    assert primeira == segunda
