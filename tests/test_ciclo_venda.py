import dataclasses
import random

import pytest

from mistfall.config import Config
from mistfall.perifericos.falso import InterruptorFalso, MaoFalsa, TelaFalsa
from mistfall.navegacao import ResultadoNavegacao
from mistfall.tipos import CapacidadeVenda, ItemAlvo, SlotArmazem
from mistfall.venda import DesfechoVenda, ResultadoVenda, RitmoVenda
from mistfall.ciclo_venda import (
    DesfechoSessaoVenda,
    executar_ciclo_venda,
    executar_venda_parcial,
)
from mistfall.venda_visao import PainelItens


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
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
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


def test_rele_candidatos_depois_de_reabrir_armazem(monkeypatch, tmp_path):
    slots = [
        SlotArmazem(0, 0, ItemAlvo.BROCHE, 3),
        SlotArmazem(0, 1, ItemAlvo.ADAGA, 3),
    ]
    capacidades = iter([
        CapacidadeVenda(0, 15),
        CapacidadeVenda(1, 15),
        CapacidadeVenda(2, 15),
    ])
    vendidos = []
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    varreduras = []
    monkeypatch.setattr(
        "mistfall.ciclo_venda.varrer_armazem",
        lambda frame: varreduras.append(frame) or slots,
    )

    def vender(tela, mao, slot, preco, pasta, ritmo, recebido):
        vendidos.append((slot.item, preco))
        resultado = sucesso(slot)
        if len(vendidos) == 1:
            resultado.armazem_reaberto = True
        return resultado

    monkeypatch.setattr("mistfall.ciclo_venda.executar_venda", vender)
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert vendidos == [
        (ItemAlvo.BROCHE, config().precos_venda[ItemAlvo.BROCHE]),
        (ItemAlvo.ADAGA, config().precos_venda[ItemAlvo.ADAGA]),
    ]
    assert sessao.vendas == 2
    assert len(varreduras) == 1


def test_painel_inventario_no_inicio_aborta_antes_de_varrer(monkeypatch, tmp_path):
    varreduras = []
    monkeypatch.setattr("mistfall.ciclo_venda.eh_tela_venda", lambda _: True)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_painel_itens",
        lambda _: PainelItens.INVENTARIO,
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_capacidade",
        lambda _: CapacidadeVenda(0, 12),
    )
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 1)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.varrer_armazem",
        lambda frame: varreduras.append(frame) or [],
    )
    mao = MaoFalsa()

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), mao, config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.desfecho is DesfechoSessaoVenda.ABORTOU
    assert "Armazem" in sessao.motivo
    assert varreduras == []
    assert mao.acoes == []


def test_bau_validamente_vazio_nao_faz_reset_e_avanca(monkeypatch, tmp_path):
    grades = iter([[], []])
    capacidades = iter([
        CapacidadeVenda(0, 15),
        CapacidadeVenda(0, 15),
        CapacidadeVenda(1, 15),
    ])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: next(grades))

    mao = MaoFalsa()
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), mao, config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.vendas == 0
    assert sessao.desfecho is DesfechoSessaoVenda.ARMAZEM_ESGOTADO
    assert mao.acoes == []


def test_releitura_no_armazem_encontra_candidato_sem_reset(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.ADAGA, 3)
    grades = iter([[], [slot]])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 15))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: next(grades))
    monkeypatch.setattr("mistfall.ciclo_venda.executar_venda", lambda *args, **kwargs: sucesso(slot))
    resets = []
    monkeypatch.setattr(
        "mistfall.ciclo_venda._forcar_reset_armazem",
        lambda *args: resets.append(True),
    )

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.vendas == 1
    assert resets == []


def test_releitura_atualiza_capacidade_antes_de_vender(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.ADAGA, 3)
    grades = iter([[], [slot]])
    capacidades = iter([
        CapacidadeVenda(0, 15),
        CapacidadeVenda(15, 15),
    ])
    vendidos = []
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: next(grades))
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args, **kwargs: vendidos.append(True) or sucesso(slot),
    )
    capacidade_recebida = []
    monkeypatch.setattr(
        "mistfall.ciclo_venda._esperar_vaga",
        lambda tela, interruptor, capacidade, ritmo: (
            capacidade_recebida.append(capacidade) or ((tela.capturar(), capacidade), "capacidade cheia")
        ),
    )

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert vendidos == []
    assert capacidade_recebida == [CapacidadeVenda(15, 15)]
    assert sessao.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA


def test_reseta_as_abas_depois_de_tres_listagens_com_capacidade_inalterada(
    monkeypatch, tmp_path,
):
    slot = SlotArmazem(0, 0, ItemAlvo.ADAGA, 3)
    capacidades = iter([
        CapacidadeVenda(0, 15),
        CapacidadeVenda(0, 15),
        CapacidadeVenda(0, 15),
        CapacidadeVenda(0, 15),
        CapacidadeVenda(15, 15),
    ])
    grades = iter([[slot, slot, slot], [slot]])
    navegacoes = []
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades)
    )
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 1)
    monkeypatch.setattr("mistfall.ciclo_venda.contar_baus", lambda _: 2)
    monkeypatch.setattr("mistfall.ciclo_venda.eh_tela_venda", lambda _: True)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_painel_itens", lambda _: PainelItens.ARMAZEM
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda.varrer_armazem", lambda _: next(grades)
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args, **kwargs: sucesso(slot),
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ir_para_compra",
        lambda *args: navegacoes.append("compra")
        or ResultadoNavegacao(True, STASH, ""),
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ir_para_venda",
        lambda *args: navegacoes.append("venda")
        or ResultadoNavegacao(True, STASH, ""),
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda._esperar_vaga",
        lambda *args: ((args[0].capturar(), CapacidadeVenda(15, 15)), "capacidade cheia"),
    )

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.vendas == 3
    assert sessao.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA
    assert navegacoes == ["compra", "venda"]


def test_leitura_inconclusiva_usa_reset_como_fallback(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.ADAGA, 3)
    grades = iter([[], [slot]])
    paineis = iter([
        PainelItens.ARMAZEM,
        PainelItens.INVENTARIO,
        PainelItens.ARMAZEM,
    ])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 15))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_painel_itens", lambda _: next(paineis))
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: next(grades))
    monkeypatch.setattr("mistfall.ciclo_venda.executar_venda", lambda *args, **kwargs: sucesso(slot))
    resets = []
    monkeypatch.setattr(
        "mistfall.ciclo_venda._forcar_reset_armazem",
        lambda tela, *args: resets.append(True) or tela.capturar(),
    )

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.vendas == 1
    assert resets == [True]


def test_leitura_inconclusiva_persistente_aborta_com_diagnostico(monkeypatch, tmp_path):
    paineis = iter([
        PainelItens.ARMAZEM,
        PainelItens.INVENTARIO,
        PainelItens.INVENTARIO,
    ])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 15))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_painel_itens", lambda _: next(paineis))
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    monkeypatch.setattr(
        "mistfall.ciclo_venda._forcar_reset_armazem",
        lambda tela, *args: tela.capturar(),
    )

    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.desfecho is DesfechoSessaoVenda.ABORTOU
    assert "leitura inconclusiva" in sessao.motivo


def test_aguarda_vaga_e_retorna_a_vender_quando_capacidade_libera(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    capacidades = iter([
        CapacidadeVenda(14, 15),
        CapacidadeVenda(15, 15),
        CapacidadeVenda(15, 15),
        CapacidadeVenda(14, 15),
        CapacidadeVenda(15, 15),
    ])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot, slot])
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args, **kwargs: sucesso(slot),
    )
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.vendas == 2
    assert sessao.capacidade_final == CapacidadeVenda(15, 15)
    assert sessao.desfecho is DesfechoSessaoVenda.ARMAZEM_ESGOTADO


def test_avanca_somente_um_bau_a_direita(monkeypatch, tmp_path):
    baus = iter([1, 1, 2, 2, 3, 3])
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
    baus = iter([1, 1, 1, 2, 2, 3, 3])
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
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
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
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: None if campo == "bau" else 1)
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.desfecho is DesfechoSessaoVenda.ABORTOU
    assert campo in sessao.motivo.lower()


def test_venda_abortada_encerra_a_sessao(monkeypatch, tmp_path):
    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
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
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 3)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot])
    mao = MaoFalsa()
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH]), mao, config(), tmp_path,
        InterruptorFalso(parar_na_pergunta=1), RitmoVenda.instantaneo(),
    )
    assert mao.acoes == []
    assert sessao.desfecho is DesfechoSessaoVenda.PAROU


def test_venda_parcial_inicia_no_segundo_bau_e_lista_stacks_ate_a_capacidade(
    monkeypatch, tmp_path,
):
    slots = [
        SlotArmazem(0, 0, ItemAlvo.BROCHE, 3),
        SlotArmazem(0, 1, ItemAlvo.ORBE, 3),
        SlotArmazem(0, 2, ItemAlvo.ADAGA, 3),
    ]
    capacidades = iter([
        CapacidadeVenda(0, 2),
        CapacidadeVenda(1, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(2, 2),
    ])
    vendidos = []
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 1)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: slots)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args: vendidos.append(args[2]) or sucesso(args[2]),
    )
    agora = [0.0]
    monkeypatch.setattr("mistfall.ciclo_venda.time.monotonic", lambda: agora[0])
    monkeypatch.setattr("mistfall.ciclo_venda.time.sleep", lambda _: agora.__setitem__(0, 3.0))
    interruptor = InterruptorFalso()
    mao = MaoFalsa()

    sessao = executar_venda_parcial(
        TelaFalsa([STASH]), mao, config(), tmp_path, interruptor,
        RitmoVenda.instantaneo(), random.Random(42),
    )

    assert mao.acoes[0] == ("clicar", 1787, 286)
    assert interruptor.inicios == 0
    assert vendidos == slots[:2]
    assert sessao.vendas == 2
    assert sessao.unidades_listadas == 6
    assert sessao.capacidade_final == CapacidadeVenda(2, 2)
    assert sessao.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA


def test_venda_parcial_aproveita_vaga_e_encerra_apos_tres_segundos_estaveis(
    monkeypatch, tmp_path,
):
    slots = [
        SlotArmazem(0, 0, ItemAlvo.BROCHE, 3),
        SlotArmazem(0, 1, ItemAlvo.ORBE, 3),
    ]
    capacidades = iter([
        CapacidadeVenda(1, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(1, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(2, 2),
        CapacidadeVenda(2, 2),
    ])
    vendidos = []
    agora = [0.0]
    esperas = []

    def dormir(segundos):
        esperas.append(segundos)
        agora[0] += segundos

    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: next(capacidades))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 1)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: slots)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args: vendidos.append(args[2]) or sucesso(args[2]),
    )
    monkeypatch.setattr("mistfall.ciclo_venda.time.monotonic", lambda: agora[0])
    monkeypatch.setattr("mistfall.ciclo_venda.time.sleep", dormir)

    sessao = executar_venda_parcial(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path, InterruptorFalso(),
        RitmoVenda(intervalo_entre_perguntas=1.0), random.Random(42),
    )

    assert vendidos == slots
    assert sum(esperas) == pytest.approx(3.0)
    assert sessao.unidades_listadas == 6
    assert sessao.capacidade_final == CapacidadeVenda(2, 2)
    assert sessao.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA


def test_varre_ate_o_ultimo_bau_detectado(monkeypatch, tmp_path):
    # Armazem expandido de season: seis Baus. Parar no quarto deixaria dois sem
    # varrer, em silencio.
    baus = iter([1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    monkeypatch.setattr("mistfall.ciclo_venda.contar_baus", lambda _: 6)
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
        ("clicar", 1979, 286),
        ("clicar", 2043, 286),
    ]
    assert sessao.baus_processados == [2, 3, 4, 5, 6]
    assert sessao.total_baus == 6


def test_venda_parcial_aceita_a_contagem_ja_feita_e_nao_reconta(monkeypatch, tmp_path):
    # O Fluxo Completo conta uma vez por sessao e repassa. Se a parcial
    # recontasse, o numero guardado nao teria serventia nenhuma.
    def _explodir(_):
        raise AssertionError("nao deveria recontar os Baus")

    baus = iter([1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    monkeypatch.setattr("mistfall.ciclo_venda.contar_baus", _explodir)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: next(baus))
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    sessao = executar_venda_parcial(
        TelaFalsa([STASH] * 12), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(), total_baus=6,
    )
    assert sessao.total_baus == 6
    assert sessao.baus_processados == [2, 3, 4, 5, 6]


def test_contagem_de_baus_implausivel_aborta(monkeypatch, tmp_path):
    # O jogo sempre da ao menos dois Baus, entao contar menos que isso e a
    # deteccao errando — nao Armazem pequeno. Seguir com um numero errado
    # varreria o Armazem pela metade em silencio.
    monkeypatch.setattr("mistfall.ciclo_venda.contar_baus", lambda _: 1)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12))
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 0)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    sessao = executar_ciclo_venda(
        TelaFalsa([STASH] * 4), MaoFalsa(), config(),
        tmp_path, InterruptorFalso(), RitmoVenda.instantaneo(),
    )
    assert sessao.desfecho is DesfechoSessaoVenda.ABORTOU
    assert "implausivel" in sessao.motivo
