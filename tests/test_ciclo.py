"""O laco: quantas Voltas, quando reseta e com qual Categoria."""

import dataclasses
import json
import pathlib
import random
import time
from datetime import datetime
from types import SimpleNamespace

import pytest

from mistfall.ciclo import Sessao, _espera_para_proxima_volta, executar_ciclo
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
        self.sorteios: list[random.Random | None] = []

    def __call__(self, tela, mao, config, pasta, **kwargs) -> Resultado:
        self.chamadas += 1
        self.sorteios.append(kwargs.get("sorteio"))
        pasta = pathlib.Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        # O que o _Diario de verdade deixa: um PNG por captura e o relatorio.
        (pasta / "00-pre-voo.png").write_bytes(b"png de mentira")
        (pasta / "relatorio.json").write_text("{}", encoding="utf-8")
        resultado = (
            self.roteiro.pop(0)
            if self.roteiro
            else Resultado(Desfecho.NADA_COMPRAVEL)
        )
        observador = kwargs.get("observador_ouro")
        if observador is not None:
            observador(
                resultado.ouro_observado,
                time.monotonic(),
                datetime.now().astimezone(),
            )
        return resultado


class _ResetFalso:
    def __init__(self, funcionou: bool = True) -> None:
        self.categorias: list[CategoriaAlternativa] = []
        self.sorteios: list[random.Random | None] = []
        self.funcionou = funcionou

    def __call__(self, tela, mao, ritmo=None, categoria_alternativa=None,
                 sorteio=None) -> bool:
        self.categorias.append(categoria_alternativa)
        self.sorteios.append(sorteio)
        return self.funcionou


def _compra_enviada() -> Resultado:
    return Resultado(Desfecho.COMPRA_ENVIADA, ouro_observado=1000)


class _RelogioFalso:
    def __init__(self):
        self.agora = 100.0
        self.esperas = []

    def monotonic(self):
        return self.agora

    def sleep(self, segundos):
        self.esperas.append(segundos)
        self.agora += segundos

    def strftime(self, _formato):
        return "12:00:00"


def _instalar_relogio(monkeypatch):
    relogio = _RelogioFalso()
    monkeypatch.setattr(
        "mistfall.ciclo.time",
        SimpleNamespace(
            monotonic=relogio.monotonic,
            sleep=relogio.sleep,
            strftime=relogio.strftime,
        ),
    )
    return relogio


def test_compra_enviada_sorteia_espera_na_faixa_pos_compra():
    ritmo = Ritmo()
    vistos = {
        _espera_para_proxima_volta(
            Desfecho.COMPRA_ENVIADA, ritmo, random.Random(semente),
        )
        for semente in range(12)
    }
    assert len(vistos) > 1
    assert all(0.65 <= espera <= 0.75 for espera in vistos)


def test_mesma_semente_reproduz_espera_pos_compra():
    ritmo = Ritmo()
    primeira = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(91),
    )
    segunda = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(91),
    )
    assert primeira == segunda


def test_sorteio_injetado_da_espera_independe_do_random_global():
    ritmo = Ritmo()
    random.seed(1)
    primeira = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(73),
    )
    random.seed(999)
    segunda = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(73),
    )
    assert primeira == segunda


@pytest.mark.parametrize(
    "desfecho",
    [Desfecho.NADA_COMPRAVEL, Desfecho.ABORTOU, Desfecho.SIMULOU],
)
def test_desfecho_sem_compra_mantem_espera_comum(desfecho):
    ritmo = dataclasses.replace(Ritmo.instantaneo(), espera_entre_voltas=0.15)
    assert _espera_para_proxima_volta(
        desfecho, ritmo, random.Random(42),
    ) == 0.15


def _rodar(monkeypatch, tmp_path, roteiro, parar_na_pergunta,
           reset_funcionou=True):
    piloto = _PilotoFalso(roteiro)
    reset = _ResetFalso(funcionou=reset_funcionou)
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
    _, piloto, _ = _rodar(
        monkeypatch, tmp_path, [_compra_enviada()], parar_na_pergunta=1)
    assert piloto.chamadas == 0


def test_o_laco_roda_ate_a_parada(monkeypatch, tmp_path):
    sessao, piloto, _ = _rodar(
        monkeypatch, tmp_path,
        [_compra_enviada(), _compra_enviada(), _compra_enviada()],
        parar_na_pergunta=4)
    assert piloto.chamadas == 3
    assert sessao.voltas == 3


def test_o_laco_encerra_quando_o_piloto_devolve_parou(monkeypatch, tmp_path):
    sessao, piloto, _ = _rodar(
        monkeypatch, tmp_path, [Resultado(Desfecho.PAROU)],
        parar_na_pergunta=3)
    assert piloto.chamadas == 1
    assert sessao.voltas == 1


def test_ciclo_aplica_espera_pos_compra(monkeypatch, tmp_path):
    relogio = _instalar_relogio(monkeypatch)
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(), espera_apos_compra=(0.65, 0.75),
    )
    piloto = _PilotoFalso([_compra_enviada(), Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=ritmo,
        sorteio=random.Random(42),
    )

    assert len(relogio.esperas) == 1
    assert 0.65 <= relogio.esperas[0] <= 0.75


@pytest.mark.parametrize("desfecho", [Desfecho.NADA_COMPRAVEL, Desfecho.ABORTOU])
def test_ciclo_mantem_150_ms_quando_nao_compra(
    monkeypatch, tmp_path, desfecho,
):
    relogio = _instalar_relogio(monkeypatch)
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(),
        espera_entre_voltas=0.15,
        espera_apos_compra=(0.65, 0.75),
    )
    piloto = _PilotoFalso([Resultado(desfecho), Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=ritmo,
        sorteio=random.Random(42),
    )

    assert relogio.esperas == [0.15]


def test_parou_nao_dorme(monkeypatch, tmp_path):
    relogio = _instalar_relogio(monkeypatch)
    piloto = _PilotoFalso([Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=2),
        ritmo=Ritmo(),
        sorteio=random.Random(42),
    )

    assert relogio.esperas == []


def test_nada_compravel_dispara_reset(monkeypatch, tmp_path):
    _, _, reset = _rodar(monkeypatch, tmp_path,
                         [Resultado(Desfecho.NADA_COMPRAVEL)], parar_na_pergunta=2)
    assert reset.categorias == [CategoriaAlternativa.FORJA]


def test_reset_que_falha_avisa_preserva_print_e_nao_avanca(
        monkeypatch, tmp_path, capsys):
    _, _, reset = _rodar(
        monkeypatch, tmp_path,
        [Resultado(Desfecho.NADA_COMPRAVEL)] * 2,
        parar_na_pergunta=3, reset_funcionou=False)

    saida = capsys.readouterr().out
    assert saida.count("-> Reset falhou (forja)") == 2
    assert reset.categorias == [CategoriaAlternativa.FORJA] * 2
    assert (tmp_path / "volta-0001" / "00-pre-voo.png").exists()
    assert (tmp_path / "volta-0002" / "00-pre-voo.png").exists()


@pytest.mark.parametrize("desfecho", [
    Desfecho.COMPRA_ENVIADA, Desfecho.ABORTOU])
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


def test_compartilha_um_sorteio_com_todas_as_voltas_e_resets(
        monkeypatch, tmp_path):
    sorteio = random.Random(42)
    piloto = _PilotoFalso([
        Resultado(Desfecho.NADA_COMPRAVEL),
        Resultado(Desfecho.COMPRA_ENVIADA),
        Resultado(Desfecho.NADA_COMPRAVEL),
    ])
    reset = _ResetFalso()
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", reset)

    executar_ciclo(
        tela=None,
        mao=None,
        config=None,
        pasta=tmp_path,
        interruptor=InterruptorFalso(parar_na_pergunta=4),
        ritmo=Ritmo.instantaneo(),
        sorteio=sorteio,
    )

    assert piloto.sorteios == [sorteio, sorteio, sorteio]
    assert reset.sorteios == [sorteio, sorteio]
    assert reset.categorias == [CategoriaAlternativa.FORJA,
                                CategoriaAlternativa.CHAVE]


def test_cria_um_unico_sorteio_quando_a_sessao_nao_recebe_um(
        monkeypatch, tmp_path):
    criados = []

    class RandomFalso(random.Random):
        def __init__(self):
            super().__init__(42)
            criados.append(self)

    piloto = _PilotoFalso([Resultado(Desfecho.NADA_COMPRAVEL)] * 2)
    reset = _ResetFalso()
    monkeypatch.setattr("mistfall.ciclo.random.Random", RandomFalso)
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", reset)

    executar_ciclo(
        tela=None,
        mao=None,
        config=None,
        pasta=tmp_path,
        interruptor=InterruptorFalso(parar_na_pergunta=3),
        ritmo=Ritmo.instantaneo(),
    )

    assert len(criados) == 1
    assert piloto.sorteios == [criados[0], criados[0]]
    assert reset.sorteios == [criados[0], criados[0]]


def test_a_sessao_conta_compras_enviadas(monkeypatch, tmp_path):
    sessao, _, _ = _rodar(
        monkeypatch, tmp_path,
        [_compra_enviada(), Resultado(Desfecho.NADA_COMPRAVEL),
         _compra_enviada()],
        parar_na_pergunta=4)
    assert sessao.voltas == 3
    assert sessao.compras_enviadas == 2


def test_o_laco_escreve_ouro_de_cada_volta_em_jsonl(monkeypatch, tmp_path):
    _rodar(
        monkeypatch,
        tmp_path,
        [_compra_enviada(), _compra_enviada()],
        parar_na_pergunta=3,
    )

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "telemetria-ouro.jsonl").read_text().splitlines()
    ]

    assert [linha["volta"] for linha in linhas] == [1, 2]
    assert [linha["ouro"] for linha in linhas] == [1000, 1000]


def test_telemetria_registra_espera_pos_compra_realmente_aplicada(
    monkeypatch, tmp_path,
):
    relogio = _instalar_relogio(monkeypatch)
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(), espera_apos_compra=(0.35, 0.35),
    )
    piloto = _PilotoFalso([_compra_enviada(), Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=ritmo,
        sorteio=random.Random(42),
    )

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "tempos-do-laco.jsonl").read_text().splitlines()
    ]

    assert len(linhas) == 1
    assert linhas[0]["espera_efetiva_ms"] == 350.0
    assert linhas[0]["intervalo_entre_inicios_ms"] == 350.0
    assert relogio.esperas == [0.35]


def test_telemetria_mede_so_o_sleep_depois_do_sorteio(
    monkeypatch, tmp_path,
):
    relogio = _instalar_relogio(monkeypatch)
    piloto = _PilotoFalso([_compra_enviada(), Resultado(Desfecho.PAROU)])

    def sortear_espera(desfecho, ritmo, sorteio):
        relogio.agora += 0.1
        return 0.35

    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())
    monkeypatch.setattr(
        "mistfall.ciclo._espera_para_proxima_volta", sortear_espera,
    )

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=Ritmo.instantaneo(),
        sorteio=random.Random(42),
    )

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "tempos-do-laco.jsonl").read_text().splitlines()
    ]
    assert linhas[0]["espera_efetiva_ms"] == 350.0
    assert linhas[0]["intervalo_entre_inicios_ms"] == 450.0


def test_cada_volta_tem_a_propria_pasta(monkeypatch, tmp_path):
    _rodar(monkeypatch, tmp_path, [_compra_enviada(), _compra_enviada()],
           parar_na_pergunta=3)
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_dir()) == [
        "volta-0001",
        "volta-0002",
    ]


def test_volta_de_rotina_descarta_os_prints(monkeypatch, tmp_path):
    # NADA_COMPRAVEL e o caso comum e o que nao carrega informacao: uma tela
    # sem Item-alvo no Preco-alvo e o esperado na maioria das Voltas.
    _rodar(monkeypatch, tmp_path, [Resultado(Desfecho.NADA_COMPRAVEL)],
           parar_na_pergunta=2)
    volta = tmp_path / "volta-0001"
    assert list(volta.glob("*.png")) == []


def test_volta_de_rotina_mantem_o_relatorio(monkeypatch, tmp_path):
    # O JSON e pequeno e e o que permite reconstruir a sessao depois.
    _rodar(monkeypatch, tmp_path, [Resultado(Desfecho.NADA_COMPRAVEL)],
           parar_na_pergunta=2)
    assert (tmp_path / "volta-0001" / "relatorio.json").exists()


@pytest.mark.parametrize("desfecho", [
    Desfecho.COMPRA_ENVIADA, Desfecho.ABORTOU])
def test_volta_interessante_guarda_os_prints(monkeypatch, tmp_path, desfecho):
    _rodar(monkeypatch, tmp_path, [Resultado(desfecho)], parar_na_pergunta=2)
    assert (tmp_path / "volta-0001" / "00-pre-voo.png").exists()


def test_so_o_primeiro_aborto_consecutivo_com_o_mesmo_motivo_guarda_print(
        monkeypatch, tmp_path):
    roteiro = [
        Resultado(Desfecho.COMPRA_ENVIADA),
        Resultado(Desfecho.ABORTOU, motivo="janela aberta"),
        Resultado(Desfecho.ABORTOU, motivo="janela aberta"),
        Resultado(Desfecho.ABORTOU, motivo="tela errada"),
    ]
    _rodar(monkeypatch, tmp_path, roteiro, parar_na_pergunta=5)

    assert [
        (tmp_path / f"volta-{numero:04d}" / "00-pre-voo.png").exists()
        for numero in range(1, 5)
    ] == [True, True, False, True]
    assert all(
        (tmp_path / f"volta-{numero:04d}" / "relatorio.json").exists()
        for numero in range(1, 5)
    )


import unicodedata

from mistfall.ciclo import linha_da_volta, linhas_do_fecho
from mistfall.tipos import ItemAlvo, Listagem


def _sem_acento(texto: str) -> bool:
    return texto == unicodedata.normalize("NFKD", texto).encode(
        "ascii", "ignore").decode("ascii")


def test_a_linha_da_compra_enviada_mostra_item_e_preco():
    listagem = Listagem(linha=0, coluna=0, item=ItemAlvo.BROCHE,
                        preco_unitario=200)
    linha = linha_da_volta(
        1, Resultado(Desfecho.COMPRA_ENVIADA, listagem=listagem,
                     ouro_observado=59227), None, "23:47:12")
    assert "[0001]" in linha
    assert "23:47:12" in linha
    assert "compra enviada" in linha
    assert ItemAlvo.BROCHE.value in linha
    assert "200g" in linha
    assert "59227" not in linha


def test_a_linha_do_nada_compravel_diz_para_onde_resetou():
    linha = linha_da_volta(2, Resultado(Desfecho.NADA_COMPRAVEL),
                           CategoriaAlternativa.FORJA, "23:47:19")
    assert "Reset" in linha and "forja" in linha


def test_a_linha_do_aborto_carrega_o_motivo():
    linha = linha_da_volta(
        5, Resultado(Desfecho.ABORTOU, motivo="pre-voo viu janela, esperava lista"),
        None, "23:47:40")
    assert "esperava lista" in linha


@pytest.mark.parametrize("desfecho", list(Desfecho))
def test_nenhuma_linha_tem_acento(desfecho):
    # A pagina de codigo do console do Windows: o projeto inteiro escreve
    # saida sem acento, e esta e a unica superficie que o operador ve
    # enquanto o bot roda.
    linha = linha_da_volta(
        1, Resultado(desfecho, motivo="operação inválida; exceção não prevista"),
        CategoriaAlternativa.CHAVE, "00:00:00")
    assert _sem_acento(linha), linha


def test_o_fecho_resume_a_sessao():
    linhas = linhas_do_fecho(Sessao(voltas=12, compras_enviadas=3))
    texto = "\n".join(linhas)
    assert "12" in texto and "3 Compras enviadas" in texto
    assert "Ouro gasto" not in texto
    assert _sem_acento(texto)


def test_o_laco_imprime_uma_linha_por_volta(monkeypatch, tmp_path, capsys):
    _rodar(monkeypatch, tmp_path, [_compra_enviada(), _compra_enviada()],
           parar_na_pergunta=3)
    saida = capsys.readouterr().out
    assert "[0001]" in saida and "[0002]" in saida
    assert saida.count("compra enviada") == 2
