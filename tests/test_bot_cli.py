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
    class InterruptorWindows:
        def __init__(self):
            self.teclas = (perifericos.VK_F3, perifericos.VK_F4)

    perifericos.VK_F3 = 0x72
    perifericos.VK_F4 = 0x73
    perifericos.InterruptorWindows = InterruptorWindows
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    monkeypatch.setattr(bot_cli, "carregar_config", lambda _: None)
    visto = {}

    def executar_ciclo(*args, **kwargs):
        visto["args"] = args
        visto.update(kwargs)
        return Sessao(voltas=0)

    monkeypatch.setattr(bot_cli, "executar_ciclo", executar_ciclo)
    args = argparse.Namespace(
        pasta=str(tmp_path), config="config.toml", espera_modal=100)

    assert bot_cli._rodar(args) == 0
    ritmo = visto["ritmo"]
    assert ritmo.pausa_antes_do_clique == (0.05, 0.15)
    assert ritmo.espera_entre_voltas == 0.15
    assert ritmo.espera_apos_compra == (0.65, 0.75)
    assert ritmo.espera_para_o_modal_abrir == (0.1, 0.15)
    interruptor = visto["args"][4]
    assert isinstance(interruptor, InterruptorWindows)
    assert interruptor.teclas == (perifericos.VK_F3, perifericos.VK_F4)


def test_bot_anuncia_f3_para_comecar_e_f4_para_parar(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(bot_cli, "carregar_config", lambda _: None)
    monkeypatch.setattr(bot_cli, "executar_ciclo", lambda *args, **kwargs: None)
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.InterruptorWindows = type("InterruptorWindows", (), {})
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)

    args = argparse.Namespace(
        pasta=str(tmp_path), config="config.toml", espera_modal=100)
    bot_cli._rodar(args)

    assert "F3 no jogo para comecar, F4 para pausar, F5 para encerrar" in capsys.readouterr().out


def test_bot_roda_nova_sessao_depois_do_f4_ate_o_f5(monkeypatch, tmp_path):
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.VK_F3 = 0x72
    perifericos.VK_F4 = 0x73
    perifericos.VK_F5 = 0x74

    class InterruptorWindows:
        def __init__(self):
            self.sessoes = 0

        def pediu_encerramento(self):
            self.sessoes += 1
            return self.sessoes >= 2

    perifericos.InterruptorWindows = InterruptorWindows
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    monkeypatch.setattr(bot_cli, "carregar_config", lambda _: None)
    chamadas = []
    monkeypatch.setattr(bot_cli, "executar_ciclo", lambda *args, **kwargs: chamadas.append(1))

    args = argparse.Namespace(pasta=str(tmp_path), config="config.toml", espera_modal=100)

    assert bot_cli._rodar(args) == 0
    assert len(chamadas) == 2
