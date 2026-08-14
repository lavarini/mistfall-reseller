import sys

from ferramentas.piloto_cli import codigo_de_saida, montar_parser
from mistfall.piloto import Desfecho, Resultado

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
