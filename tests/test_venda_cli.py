import argparse
import sys
import types

from mistfall.config import Config
from mistfall.tipos import ItemAlvo

from ferramentas import venda_cli
from ferramentas.venda_cli import montar_parser


def config_completo():
    return Config(precos_alvo={}, precos_venda={item: 200 for item in ItemAlvo})


def test_parser_aceita_pasta_config_e_tetos():
    args = montar_parser().parse_args([
        "--pasta", "vendas", "--config", "outro.toml",
        "--teto-janela", "8", "--teto-fechamento", "12",
    ])
    assert (args.pasta, args.config) == ("vendas", "outro.toml")
    assert (args.teto_janela, args.teto_fechamento) == (8.0, 12.0)


def test_parser_nao_oferece_limite_de_listagens():
    assert "--limite-listagens" not in montar_parser().format_help()


def test_rodar_valida_config_e_monta_perifericos_windows(monkeypatch, tmp_path):
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.InterruptorWindows = type("InterruptorWindows", (), {})
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    config = config_completo()
    monkeypatch.setattr(venda_cli, "carregar_config", lambda caminho: config)
    validados = []
    monkeypatch.setattr(venda_cli, "validar_precos_venda", validados.append)
    chamadas = []
    monkeypatch.setattr(venda_cli, "executar_ciclo_venda", lambda *a, **k: chamadas.append((a, k)))
    args = argparse.Namespace(
        pasta=str(tmp_path), config="config.toml",
        teto_janela=8.0, teto_fechamento=12.0,
    )
    assert venda_cli._rodar(args) == 0
    assert validados == [config]
    tela, mao, recebido, pasta, interruptor = chamadas[0][0][:5]
    assert isinstance(tela, perifericos.TelaWindows)
    assert isinstance(mao, perifericos.MaoWindows)
    assert isinstance(interruptor, perifericos.InterruptorWindows)
    assert recebido is config
    assert pasta == tmp_path


def test_main_converte_config_invalida_em_codigo_dois(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mistfall-venda"])
    monkeypatch.setattr(venda_cli, "_rodar", lambda _: (_ for _ in ()).throw(ValueError("ruim")))
    assert venda_cli.main() == 2
