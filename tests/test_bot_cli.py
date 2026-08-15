"""O CLI do laco. Nao importa windows: a suite roda no macOS."""

import argparse
import sys
import types

from mistfall.ciclo import Sessao

from ferramentas import bot_cli
from ferramentas.bot_cli import montar_parser


def test_o_parser_aceita_pasta_config_e_espera_modal():
    args = montar_parser().parse_args(
        ["--pasta", "sessao", "--config", "outro.toml", "--espera-modal", "150"])
    assert args.pasta == "sessao"
    assert args.config == "outro.toml"
    assert args.espera_modal == 150


def test_a_pasta_padrao_nao_e_a_do_piloto():
    # Duas ferramentas, dois destinos: o bot nao pode sobrescrever a pasta de
    # depuracao do mistfall-piloto.
    assert montar_parser().parse_args([]).pasta != "execucao"


def test_parar_antes_da_primeira_volta_sai_com_sucesso(monkeypatch, tmp_path):
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.InterruptorWindows = type("InterruptorWindows", (), {})
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    monkeypatch.setattr(bot_cli, "carregar_config", lambda _: None)
    monkeypatch.setattr(
        bot_cli, "executar_ciclo", lambda *args, **kwargs: Sessao(voltas=0))
    args = argparse.Namespace(
        pasta=str(tmp_path), config="config.toml", espera_modal=100)

    assert bot_cli._rodar(args) == 0
