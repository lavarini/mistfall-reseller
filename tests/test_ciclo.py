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
        pasta = pathlib.Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        # O que o _Diario de verdade deixa: um PNG por captura e o relatorio.
        (pasta / "00-pre-voo.png").write_bytes(b"png de mentira")
        (pasta / "relatorio.json").write_text("{}", encoding="utf-8")
        if self.roteiro:
            return self.roteiro.pop(0)
        return Resultado(Desfecho.NADA_COMPRAVEL)


class _ResetFalso:
    def __init__(self, funcionou: bool = True) -> None:
        self.categorias: list[CategoriaAlternativa] = []
        self.funcionou = funcionou

    def __call__(self, tela, mao, ritmo=None, categoria_alternativa=None) -> bool:
        self.categorias.append(categoria_alternativa)
        return self.funcionou


def _comprou(preco: int = 200) -> Resultado:
    return Resultado(Desfecho.COMPROU, ouro_antes=1000, ouro_depois=1000 - preco,
                     preco_total_esperado=preco)


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
    _, piloto, _ = _rodar(monkeypatch, tmp_path, [_comprou()], parar_na_pergunta=1)
    assert piloto.chamadas == 0


def test_o_laco_roda_ate_a_parada(monkeypatch, tmp_path):
    sessao, piloto, _ = _rodar(
        monkeypatch, tmp_path, [_comprou(), _comprou(), _comprou()],
        parar_na_pergunta=4)
    assert piloto.chamadas == 3
    assert sessao.voltas == 3


def test_o_laco_encerra_quando_o_piloto_devolve_parou(monkeypatch, tmp_path):
    sessao, piloto, _ = _rodar(
        monkeypatch, tmp_path, [Resultado(Desfecho.PAROU)],
        parar_na_pergunta=3)
    assert piloto.chamadas == 1
    assert sessao.voltas == 1


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
    Desfecho.COMPROU, Desfecho.OURO_NAO_CAIU, Desfecho.ABORTOU])
def test_volta_interessante_guarda_os_prints(monkeypatch, tmp_path, desfecho):
    _rodar(monkeypatch, tmp_path, [Resultado(desfecho)], parar_na_pergunta=2)
    assert (tmp_path / "volta-0001" / "00-pre-voo.png").exists()


def test_so_o_primeiro_aborto_consecutivo_com_o_mesmo_motivo_guarda_print(
        monkeypatch, tmp_path):
    roteiro = [
        Resultado(Desfecho.OURO_NAO_CAIU),
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


def test_a_linha_da_compra_mostra_item_preco_e_ouro():
    listagem = Listagem(linha=0, coluna=0, item=ItemAlvo.BROCHE,
                        preco_unitario=200)
    linha = linha_da_volta(
        1, Resultado(Desfecho.COMPROU, listagem=listagem, ouro_antes=59227,
                     ouro_depois=59027), None, "23:47:12")
    assert "[0001]" in linha
    assert "23:47:12" in linha
    assert "comprou" in linha
    assert ItemAlvo.BROCHE.value in linha
    assert "200g" in linha
    assert "59227" in linha and "59027" in linha


def test_a_linha_do_nada_compravel_diz_para_onde_resetou():
    linha = linha_da_volta(2, Resultado(Desfecho.NADA_COMPRAVEL),
                           CategoriaAlternativa.FORJA, "23:47:19")
    assert "Reset" in linha and "forja" in linha


def test_a_linha_do_ouro_nao_caiu_grita():
    # E o desfecho mais provavel da primeira execucao real (#9): tem de
    # saltar aos olhos numa tela que rola sozinha.
    linha = linha_da_volta(4, Resultado(Desfecho.OURO_NAO_CAIU,
                                        motivo="o Ouro nao se moveu"),
                           None, "23:47:33")
    assert "OURO NAO CAIU" in linha


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
    linhas = linhas_do_fecho(Sessao(voltas=12, compras=3, ouro_gasto=550))
    texto = "\n".join(linhas)
    assert "12" in texto and "3" in texto and "550" in texto
    assert _sem_acento(texto)


def test_o_laco_imprime_uma_linha_por_volta(monkeypatch, tmp_path, capsys):
    _rodar(monkeypatch, tmp_path, [_comprou(), _comprou()], parar_na_pergunta=3)
    saida = capsys.readouterr().out
    assert "[0001]" in saida and "[0002]" in saida
    assert saida.count("comprou") == 2
