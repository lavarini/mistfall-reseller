"""O laco: quantas Voltas, quando reseta e com qual Categoria."""

import pathlib

import pytest

from mistfall.ciclo import Sessao, executar_ciclo
from mistfall.perifericos.falso import InterruptorFalso
from mistfall.piloto import Desfecho, Resultado, Ritmo
from mistfall.reset import CategoriaAlternativa


class _PilotoFalso:
    """Devolve desfechos de um roteiro, sem tocar em tela nem em mao.

    O ciclo e testado contra este duble, e nao contra o piloto de verdade:
    o que esta em jogo aqui e a decisao de resetar e a de parar, nao a
    Compra — essa ja tem os testes dela em test_piloto.py.
    """

    def __init__(self, roteiro: list[Resultado]) -> None:
        self.roteiro = list(roteiro)
        self.chamadas = 0

    def __call__(self, tela, mao, config, pasta, **kwargs) -> Resultado:
        self.chamadas += 1
        pathlib.Path(pasta).mkdir(parents=True, exist_ok=True)
        if self.roteiro:
            return self.roteiro.pop(0)
        return Resultado(Desfecho.NADA_COMPRAVEL)


class _ResetFalso:
    def __init__(self) -> None:
        self.categorias: list[CategoriaAlternativa] = []

    def __call__(self, tela, mao, ritmo=None, categoria_alternativa=None) -> bool:
        self.categorias.append(categoria_alternativa)
        return True


def _comprou(preco: int = 200) -> Resultado:
    return Resultado(Desfecho.COMPROU, ouro_antes=1000, ouro_depois=1000 - preco,
                     preco_total_esperado=preco)


def _rodar(monkeypatch, tmp_path, roteiro, parar_na_pergunta):
    piloto, reset = _PilotoFalso(roteiro), _ResetFalso()
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", reset)
    sessao = executar_ciclo(
        tela=None, mao=None, config=None, pasta=tmp_path,
        interruptor=InterruptorFalso(parar_na_pergunta=parar_na_pergunta),
        ritmo=Ritmo.instantaneo(),
    )
    return sessao, piloto, reset


def test_o_laco_espera_o_inicio_antes_de_qualquer_coisa(monkeypatch, tmp_path):
    interruptor = InterruptorFalso(parar_na_pergunta=1)
    monkeypatch.setattr("mistfall.ciclo.executar", _PilotoFalso([]))
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())
    executar_ciclo(tela=None, mao=None, config=None, pasta=tmp_path,
                   interruptor=interruptor, ritmo=Ritmo.instantaneo())
    assert interruptor.inicios == 1


def test_a_parada_encerra_o_laco_sem_rodar_volta(monkeypatch, tmp_path):
    _, piloto, _ = _rodar(monkeypatch, tmp_path, [_comprou()], parar_na_pergunta=1)
    assert piloto.chamadas == 0


def test_o_laco_roda_ate_a_parada(monkeypatch, tmp_path):
    sessao, piloto, _ = _rodar(
        monkeypatch, tmp_path, [_comprou(), _comprou(), _comprou()],
        parar_na_pergunta=4)
    assert piloto.chamadas == 3
    assert sessao.voltas == 3


def test_nada_compravel_dispara_reset(monkeypatch, tmp_path):
    _, _, reset = _rodar(monkeypatch, tmp_path,
                         [Resultado(Desfecho.NADA_COMPRAVEL)], parar_na_pergunta=2)
    assert reset.categorias == [CategoriaAlternativa.FORJA]


@pytest.mark.parametrize("desfecho", [
    Desfecho.COMPROU, Desfecho.OURO_NAO_CAIU, Desfecho.ABORTOU])
def test_os_outros_desfechos_nao_resetam(monkeypatch, tmp_path, desfecho):
    # A lista recarrega sozinha depois de uma Compra ou tentativa; abortar
    # nem chegou a mexer na tela.
    _, _, reset = _rodar(monkeypatch, tmp_path, [Resultado(desfecho)],
                         parar_na_pergunta=2)
    assert reset.categorias == []


def test_a_categoria_do_reset_alterna(monkeypatch, tmp_path):
    # Um Reset usa UMA Categoria alternativa. A alternancia e entre Resets
    # sucessivos, nunca dentro do mesmo.
    _, _, reset = _rodar(
        monkeypatch, tmp_path, [Resultado(Desfecho.NADA_COMPRAVEL)] * 3,
        parar_na_pergunta=4)
    assert reset.categorias == [CategoriaAlternativa.FORJA,
                                CategoriaAlternativa.CHAVE,
                                CategoriaAlternativa.FORJA]


def test_a_sessao_conta_compras_e_ouro_gasto(monkeypatch, tmp_path):
    sessao, _, _ = _rodar(
        monkeypatch, tmp_path,
        [_comprou(200), Resultado(Desfecho.NADA_COMPRAVEL), _comprou(150)],
        parar_na_pergunta=4)
    assert sessao.voltas == 3
    assert sessao.compras == 2
    assert sessao.ouro_gasto == 350


def test_cada_volta_tem_a_propria_pasta(monkeypatch, tmp_path):
    _rodar(monkeypatch, tmp_path, [_comprou(), _comprou()], parar_na_pergunta=3)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["volta-0001", "volta-0002"]
