import dataclasses
import random

import pytest

from mistfall.config import Config
from mistfall.perifericos.falso import InterruptorFalso, MaoFalsa, TelaFalsa
from mistfall.tipos import Bau, CapacidadeVenda, ItemAlvo, SlotArmazem
from mistfall.venda import DesfechoVenda, ResultadoVenda, RitmoVenda
from mistfall.ciclo_venda import (
    DesfechoSessaoVenda,
    executar_ciclo_venda,
)


STASH = "images/venda-stash-2.png"


def config():
    return Config(
        precos_alvo={},
        precos_venda={item: 200 + indice for indice, item in enumerate(ItemAlvo)},
    )


def sucesso(slot):
    return ResultadoVenda(
        desfecho=DesfechoVenda.VENDEU,
        motivo="",
        item=slot.item.value,
        linha=slot.linha,
        coluna=slot.coluna,
        preco_venda=226,
    )


def test_processa_o_bau_uma_vez_e_vende_todos_os_stacks_tres(monkeypatch, tmp_path):
    slots = [
        SlotArmazem(0, 0, ItemAlvo.BROCHE, 3),
        SlotArmazem(0, 1, ItemAlvo.BROCHE, 2),
        SlotArmazem(0, 2, ItemAlvo.ORBE, 3),
    ]
    capacidades = iter([
        CapacidadeVenda(0, 12),
        CapacidadeVenda(1, 12),
        CapacidadeVenda(2, 12),
    ])
    varreduras = []
    vendidos = []
    sorteio = random.Random(42)
    sorteios_recebidos = []
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: Bau.QUARTO)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.varrer_armazem",
        lambda frame: varreduras.append(frame) or slots,
    )
    def vender(tela, mao, slot, preco, pasta, ritmo, recebido):
        vendidos.append(slot)
        sorteios_recebidos.append(recebido)
        return sucesso(slot)

    monkeypatch.setattr("mistfall.ciclo_venda.executar_venda", vender)

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(), sorteio=sorteio,
    )

    assert vendidos == [slots[0], slots[2]]
    assert sorteios_recebidos == [sorteio, sorteio]
    assert len(varreduras) == 1
    assert sessao.vendas == 2
    assert sessao.desfecho is DesfechoSessaoVenda.ARMAZEM_ESGOTADO


def test_para_quando_a_capacidade_lida_fica_cheia(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    capacidades = iter([CapacidadeVenda(11, 12), CapacidadeVenda(12, 12)])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: Bau.SEGUNDO)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot, slot])
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args, **kwargs: sucesso(slot),
    )
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.vendas == 1
    assert sessao.capacidade_final == CapacidadeVenda(12, 12)
    assert sessao.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA


def test_avanca_somente_um_bau_a_direita(monkeypatch, tmp_path):
    baus = iter([Bau.SEGUNDO, Bau.TERCEIRO, Bau.QUARTO])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: next(baus))
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    mao = MaoFalsa()
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), mao, config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert [acao for acao in mao.acoes if acao[0] == "clicar"] == [
        ("clicar", 1851, 286),
        ("clicar", 1915, 286),
    ]
    assert sessao.baus_processados == [2, 3, 4]


def test_espera_o_destaque_mudar_antes_de_processar_o_proximo_bau(monkeypatch, tmp_path):
    # A primeira captura depois do clique ainda mostra o segundo Bau. Processa-la
    # de novo venderia candidatos antigos; o ciclo precisa esperar o terceiro.
    baus = iter([Bau.SEGUNDO, Bau.SEGUNDO, Bau.TERCEIRO, Bau.QUARTO])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: next(baus))
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), dataclasses.replace(
            RitmoVenda.instantaneo(), teto_espera_fechamento=1.0
        ),
    )
    assert sessao.baus_processados == [2, 3, 4]


def test_limite_novo_substitui_o_anterior(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    capacidades = iter([CapacidadeVenda(1, 12), CapacidadeVenda(2, 20)])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: Bau.QUARTO)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot])
    monkeypatch.setattr("mistfall.ciclo_venda.executar_venda", lambda *a, **k: sucesso(slot))
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.capacidade_final == CapacidadeVenda(2, 20)
    assert sessao.desfecho is DesfechoSessaoVenda.ARMAZEM_ESGOTADO


@pytest.mark.parametrize("campo", ["capacidade", "bau"])
def test_leitura_essencial_ilegivel_aborta(monkeypatch, tmp_path, campo):
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: None if campo == "capacidade" else CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: None if campo == "bau" else Bau.SEGUNDO)
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.desfecho is DesfechoSessaoVenda.ABORTOU
    assert campo in sessao.motivo.lower()


def test_venda_abortada_encerra_a_sessao(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: Bau.QUARTO)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot])
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *a, **k: dataclasses.replace(sucesso(slot), desfecho=DesfechoVenda.ABORTOU, motivo="janela nao abriu"),
    )
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.desfecho is DesfechoSessaoVenda.ABORTOU
    assert sessao.vendas == 0


def test_f3_antes_do_primeiro_stack_nao_clica(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: Bau.QUARTO)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot])
    mao = MaoFalsa()
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), mao, config(), tmp_path,
        InterruptorFalso(parar_na_pergunta=1), RitmoVenda.instantaneo(),
    )
    assert mao.acoes == []
    assert sessao.desfecho is DesfechoSessaoVenda.PAROU
