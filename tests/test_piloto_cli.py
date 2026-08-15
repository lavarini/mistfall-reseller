import sys

import pytest

from ferramentas.piloto_cli import CODIGO_POR_DESFECHO, codigo_de_saida, montar_parser
from mistfall.config import Config
from mistfall.piloto import Desfecho, Resultado
from mistfall.tipos import ItemAlvo

def test_parser_tem_simular_e_pasta():
    args = montar_parser().parse_args(["--simular", "--pasta", "/tmp/x"])
    assert args.simular is True
    assert args.pasta == "/tmp/x"

def test_simular_e_falso_por_padrao():
    assert montar_parser().parse_args([]).simular is False

def test_resetar_e_falso_por_padrao():
    assert montar_parser().parse_args([]).resetar is None

def test_resetar_sem_destino_usa_forja_e_aceita_chave():
    assert montar_parser().parse_args(["--resetar"]).resetar == "forja"
    assert montar_parser().parse_args(["--resetar", "chave"]).resetar == "chave"

def test_resetar_nao_pode_ser_combinado_com_simulacao():
    with pytest.raises(SystemExit):
        montar_parser().parse_args(["--resetar", "--simular"])

def test_resetar_executa_so_o_reset(monkeypatch, capsys):
    import ferramentas.piloto_cli as cli
    import mistfall.perifericos.windows as windows

    monkeypatch.setattr(windows, "TelaWindows", type("T", (), {}))
    monkeypatch.setattr(windows, "MaoWindows", type("M", (), {}))
    monkeypatch.setattr(cli, "SEGUNDOS_DE_CONTAGEM", 0)
    monkeypatch.setattr(cli, "carregar_config",
                        lambda *_: pytest.fail("nao deveria carregar config"))
    monkeypatch.setattr(cli, "executar",
                        lambda *_a, **_k: pytest.fail("nao deveria comprar"))
    visto = {}

    def reset_espiao(*_a, **kwargs):
        visto.update(kwargs)
        return True

    monkeypatch.setattr(cli, "resetar_categoria", reset_espiao)

    args = montar_parser().parse_args(["--resetar"])
    assert cli._rodar(args) == 0
    assert "Reset: concluido" in capsys.readouterr().out
    assert visto["categoria_alternativa"] is cli.CategoriaAlternativa.FORJA

def test_cli_repassa_chave_ao_reset(monkeypatch):
    import ferramentas.piloto_cli as cli
    import mistfall.perifericos.windows as windows

    monkeypatch.setattr(windows, "TelaWindows", type("T", (), {}))
    monkeypatch.setattr(windows, "MaoWindows", type("M", (), {}))
    monkeypatch.setattr(cli, "SEGUNDOS_DE_CONTAGEM", 0)
    visto = {}
    monkeypatch.setattr(
        cli, "resetar_categoria",
        lambda *_a, **kwargs: visto.update(kwargs) is None,
    )

    assert cli._rodar(montar_parser().parse_args(["--resetar", "chave"])) == 0
    assert visto["categoria_alternativa"] is cli.CategoriaAlternativa.CHAVE

def test_espera_do_modal_e_ajustavel_em_milissegundos():
    # A Janela abre com animacao, e quanto ela dura so se descobre na maquina
    # do jogo. Calibrar nao pode exigir editar Python la.
    assert montar_parser().parse_args(["--espera-modal", "250"]).espera_modal == 250

def test_espera_do_modal_vira_faixa_com_piso_no_valor_pedido(monkeypatch, tmp_path):
    # O flag e em ms porque e assim que se fala de animacao; o Ritmo e em
    # segundos. E o valor pedido e o PISO da faixa sorteada, nunca o teto: o
    # sorteio existe para o ritmo variar, e variar para baixo perde Compra.
    import ferramentas.piloto_cli as cli
    import mistfall.perifericos.windows as windows

    monkeypatch.setattr(windows, "TelaWindows", type("T", (), {}))
    monkeypatch.setattr(windows, "MaoWindows", type("M", (), {}))
    monkeypatch.setattr(cli, "carregar_config",
                        lambda caminho: Config(precos_alvo={ItemAlvo.DRAGAO: 246}))
    visto = {}

    def espiao(*a, **k):
        visto["ritmo"] = k["ritmo"]
        return Resultado(Desfecho.COMPROU)

    monkeypatch.setattr(cli, "executar", espiao)
    monkeypatch.setattr(sys, "argv", ["mistfall-piloto", "--simular",
                                      "--pasta", str(tmp_path),
                                      "--espera-modal", "250"])
    assert cli.main() == 0
    piso, teto = visto["ritmo"].espera_para_o_modal_abrir
    assert piso == 0.25
    assert teto > piso

def test_comprou_sai_zero():
    assert codigo_de_saida(Resultado(Desfecho.COMPROU)) == 0

def test_nada_compravel_sai_zero():
    assert codigo_de_saida(Resultado(Desfecho.NADA_COMPRAVEL)) == 0

def test_simulou_sai_zero():
    assert codigo_de_saida(Resultado(Desfecho.SIMULOU)) == 0

def test_abortou_sai_um():
    assert codigo_de_saida(Resultado(Desfecho.ABORTOU, "qualquer motivo")) == 1

def test_ouro_que_nao_caiu_nao_sai_zero():
    # Sair 0 aqui deixa "o Espaco nao registrou" indistinguivel de uma Compra
    # confirmada, que e justamente a pergunta que a execucao vai responder.
    assert codigo_de_saida(Resultado(Desfecho.OURO_NAO_CAIU, "parado")) == 3

def test_todo_desfecho_tem_codigo_de_saida():
    # Desfecho novo sem codigo tem de estourar, nunca cair num default 0.
    for desfecho in Desfecho:
        assert codigo_de_saida(Resultado(desfecho)) in (0, 1, 3)

def test_problema_de_ambiente_sai_dois(monkeypatch, capsys):
    # Resolucao errada, tesseract ausente e config invalida sobem excecao.
    # A CLI tem de traduzir isso em codigo 2, nao em traceback.
    import ferramentas.piloto_cli as cli

    def explodir(*_a, **_k):
        raise ValueError("esperava 2560x1440, recebi 1920x1080")

    monkeypatch.setattr(cli, "carregar_config", explodir)
    monkeypatch.setattr(sys, "argv", ["mistfall-piloto", "--simular"])
    assert cli.main() == 2
    assert "2560x1440" in capsys.readouterr().err


def test_cli_imprime_o_tempo_de_cada_etapa(monkeypatch, capsys, tmp_path):
    # Achado do review final: apagar o bloco de tempos em piloto_cli.py
    # (ferramentas/piloto_cli.py:88-91) nao derrubava teste nenhum. A Task 5
    # (tempo por etapa) tinha prova em mistfall.piloto, mas nao no
    # entregavel de verdade, que e o que a CLI imprime para o operador.
    import ferramentas.piloto_cli as cli
    import mistfall.perifericos.windows as windows

    class TelaFalsaQueNaoPrecisaDeMss:
        pass

    class MaoFalsaQueNaoPrecisaDeCtypes:
        pass

    # TelaWindows/MaoWindows de verdade nao instanciam no Mac (mss ausente),
    # e a construcao acontece dentro de _rodar antes de chegar ao executar
    # espiao — entao o duble precisa entrar na classe, nao so na chamada.
    monkeypatch.setattr(windows, "TelaWindows", TelaFalsaQueNaoPrecisaDeMss)
    monkeypatch.setattr(windows, "MaoWindows", MaoFalsaQueNaoPrecisaDeCtypes)
    monkeypatch.setattr(cli, "carregar_config",
                        lambda caminho: Config(precos_alvo={ItemAlvo.DRAGAO: 246}))
    monkeypatch.setattr(
        cli, "executar",
        lambda *a, **k: Resultado(
            Desfecho.COMPROU,
            tempos={"pre_voo": 12.3, "varredura": 456.7, "modal": 78.9},
        ),
    )
    monkeypatch.setattr(sys, "argv",
                        ["mistfall-piloto", "--simular", "--pasta", str(tmp_path)])

    assert cli.main() == 0
    saida = capsys.readouterr().out
    assert "Tempo por etapa" in saida
    assert "varredura: 456.7" in saida


test_todo_desfecho_tem_codigo_de_saida_pelo_resultado = (
    test_todo_desfecho_tem_codigo_de_saida
)


def test_todo_desfecho_tem_codigo_de_saida():
    # O mapa foi escrito sem default de proposito: desfecho novo sem codigo
    # tem de estourar, nao sair 0 e virar indistinguivel de sucesso.
    for desfecho in Desfecho:
        assert desfecho in CODIGO_POR_DESFECHO


def test_parada_pedida_sai_com_zero():
    # F3 e decisao do operador, nao falha do bot.
    assert CODIGO_POR_DESFECHO[Desfecho.PAROU] == 0
