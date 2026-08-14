import sys

from ferramentas.piloto_cli import codigo_de_saida, montar_parser
from mistfall.config import Config
from mistfall.piloto import Desfecho, Resultado
from mistfall.tipos import ItemAlvo

def test_parser_tem_simular_e_pasta():
    args = montar_parser().parse_args(["--simular", "--pasta", "/tmp/x"])
    assert args.simular is True
    assert args.pasta == "/tmp/x"

def test_simular_e_falso_por_padrao():
    assert montar_parser().parse_args([]).simular is False

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
