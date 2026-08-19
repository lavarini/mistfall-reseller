import random
from collections import deque

import numpy as np

from mistfall.ciclo_venda import DesfechoSessaoVenda, SessaoVenda
from mistfall.compra_visao import MensagemCompra
from mistfall.fluxo import ModoFluxo, estado_inicial
from mistfall.navegacao import ResultadoNavegacao
from mistfall.piloto import Desfecho, Resultado, Ritmo
from mistfall.venda import RitmoVenda

from mistfall.ciclo_completo import (
    DesfechoSessaoCompleta,
    executar_ciclo_completo,
)


RITMO_COMPRA = Ritmo.instantaneo()
RITMO_VENDA = RitmoVenda.instantaneo()


class InterruptorRoteirizado:
    def __init__(self, respostas=()):
        self._respostas = deque(respostas)
        self.inicios = 0
        self.perguntas = 0

    def esperar_inicio(self):
        self.inicios += 1

    def pediram_parada(self):
        self.perguntas += 1
        return self._respostas.popleft() if self._respostas else False


def _resultado(desfecho, *, ouro=1000, preco=100):
    resultado = Resultado(desfecho, ouro_observado=ouro)
    if desfecho is Desfecho.COMPRA_ENVIADA:
        from mistfall.tipos import ItemAlvo, Listagem

        resultado.listagem = Listagem(0, 0, ItemAlvo.BROCHE, preco)
    return resultado


def _preparar(monkeypatch, resultados, mensagens=None, venda=None):
    import mistfall.ciclo_completo as completo

    resultados = deque(resultados)
    mensagens = deque(mensagens or [MensagemCompra.NENHUMA] * len(resultados))
    chamadas = []
    frame_atual = [0]

    def executar(*args, **kwargs):
        frame_atual[0] += 1
        kwargs["observador_frame_inicial"](
            np.full((1, 1, 3), frame_atual[0], dtype=np.uint8)
        )
        chamadas.append("compra")
        return resultados.popleft()

    def detectar(_frame):
        return mensagens.popleft() if mensagens else MensagemCompra.NENHUMA

    monkeypatch.setattr(completo, "executar", executar)
    monkeypatch.setattr(completo, "detectar_mensagem_compra", detectar)
    monkeypatch.setattr(
        completo,
        "garantir_filtro_roxo",
        lambda *args: chamadas.append("filtro_inicial")
        or ResultadoNavegacao(True, np.zeros((1, 1, 3), dtype=np.uint8), ""),
    )
    monkeypatch.setattr(
        completo,
        "ir_para_venda",
        lambda *args: chamadas.append("ir_venda")
        or ResultadoNavegacao(True, np.zeros((1, 1, 3), dtype=np.uint8), ""),
    )
    monkeypatch.setattr(
        completo,
        "ir_para_compra",
        lambda *args: chamadas.append("ir_compra")
        or ResultadoNavegacao(True, np.zeros((1, 1, 3), dtype=np.uint8), ""),
    )
    monkeypatch.setattr(
        completo,
        "resetar_categoria",
        lambda *args, **kwargs: chamadas.append("reset") or True,
    )
    monkeypatch.setattr(
        completo,
        "executar_venda_parcial",
        lambda *args, **kwargs: chamadas.append("venda")
        or (venda or SessaoVenda(DesfechoSessaoVenda.ARMAZEM_ESGOTADO)),
    )
    return chamadas


def _executar(tmp_path, interruptor):
    return executar_ciclo_completo(
        object(), object(), object(), tmp_path, interruptor,
        RITMO_COMPRA, RITMO_VENDA, random.Random(42),
    )


def test_comeca_em_comprar_validando_o_filtro_e_espera_f3_uma_vez(
    monkeypatch, tmp_path,
):
    chamadas = _preparar(monkeypatch, [])
    interruptor = InterruptorRoteirizado([True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.desfecho is DesfechoSessaoCompleta.PAROU
    assert interruptor.inicios == 1
    assert chamadas == ["filtro_inicial"]


def test_compra_rapida_reseta_so_sem_intencao_e_nao_faz_venda_voluntaria(
    monkeypatch, tmp_path,
):
    chamadas = _preparar(monkeypatch, [
        _resultado(Desfecho.COMPRA_ENVIADA),
        _resultado(Desfecho.NADA_COMPRAVEL, ouro=900),
        _resultado(Desfecho.COMPRA_ENVIADA, ouro=900),
    ])
    interruptor = InterruptorRoteirizado([False] * 3 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.modo is ModoFluxo.RAPIDO
    assert sessao.compras_enviadas == 2
    assert chamadas.count("reset") == 1
    assert "venda" not in chamadas


def test_inventario_cheio_entra_em_venda(monkeypatch, tmp_path):
    chamadas = _preparar(
        monkeypatch,
        [
            _resultado(Desfecho.COMPRA_ENVIADA),
            _resultado(Desfecho.NADA_COMPRAVEL, ouro=1000),
        ],
        [MensagemCompra.NENHUMA, MensagemCompra.INVENTARIO_CHEIO],
    )
    interruptor = InterruptorRoteirizado([False] * 3 + [True])

    _executar(tmp_path, interruptor)

    assert chamadas.count("venda") == 1
    assert chamadas.index("ir_venda") < chamadas.index("venda")


def test_tres_intervalos_lentos_entram_em_venda(monkeypatch, tmp_path):
    intencao = lambda: _resultado(Desfecho.COMPRA_ENVIADA)
    reset = lambda: _resultado(Desfecho.NADA_COMPRAVEL)
    resultados = (
        [intencao()]
        + [reset() for _ in range(3)]
        + [intencao()]
        + [reset() for _ in range(3)]
        + [intencao()]
        + [reset() for _ in range(3)]
        + [intencao()]
    )
    chamadas = _preparar(monkeypatch, resultados)
    interruptor = InterruptorRoteirizado([False] * 14 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.modo is ModoFluxo.LENTO
    assert chamadas.count("venda") == 1


def test_cinco_resets_consecutivos_entram_em_venda(monkeypatch, tmp_path):
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL) for _ in range(5)],
    )
    interruptor = InterruptorRoteirizado([False] * 6 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.modo is ModoFluxo.LENTO
    assert chamadas.count("reset") == 5
    assert chamadas.count("venda") == 1


def test_retorno_da_venda_restaura_comprar_e_filtro_roxo(
    monkeypatch, tmp_path,
):
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    _executar(tmp_path, interruptor)

    assert chamadas[-3:] == ["ir_venda", "venda", "ir_compra"]


def test_venda_de_45_preserva_saldo_55_de_um_estoque_100(
    monkeypatch, tmp_path,
):
    import mistfall.ciclo_completo as completo

    venda = SessaoVenda(
        DesfechoSessaoVenda.CAPACIDADE_CHEIA,
        unidades_listadas=45,
    )
    _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        venda,
    )
    monkeypatch.setattr(
        completo, "estado_inicial", lambda: estado_inicial(estoque_estimado=100)
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.estoque_estimado == 55
    assert sessao.unidades_listadas == 45


def test_f4_para_durante_compra_ou_venda(monkeypatch, tmp_path):
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.PAROU)],
    )
    sessao_compra = _executar(
        tmp_path / "compra", InterruptorRoteirizado([False])
    )
    assert sessao_compra.desfecho is DesfechoSessaoCompleta.PAROU
    assert "venda" not in chamadas

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        SessaoVenda(DesfechoSessaoVenda.PAROU),
    )
    sessao_venda = _executar(
        tmp_path / "venda", InterruptorRoteirizado([False] * 2)
    )
    assert sessao_venda.desfecho is DesfechoSessaoCompleta.PAROU
    assert chamadas[-2:] == ["ir_venda", "venda"]
    assert "ir_compra" not in chamadas
