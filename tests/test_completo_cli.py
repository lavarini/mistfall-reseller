import argparse
import pathlib
import sys
import tomllib
import types

from mistfall.ciclo_completo import DesfechoSessaoCompleta, SessaoCompleta
from mistfall.config import Config
from mistfall.tipos import ItemAlvo

from ferramentas import completo_cli
from ferramentas.completo_cli import montar_parser


def _config_completo():
    return Config(precos_alvo={}, precos_venda={item: 200 for item in ItemAlvo})


def _perifericos_falsos(monkeypatch):
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.VK_F3 = 0x72
    perifericos.VK_F4 = 0x73
    perifericos.InterruptorWindows = lambda **kwargs: object()
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    monkeypatch.setattr(completo_cli, "carregar_config", lambda _: _config_completo())
    monkeypatch.setattr(completo_cli, "validar_precos_venda", lambda _: None)
    return perifericos


def test_parser_aceita_pasta_config_e_ritmos():
    args = montar_parser().parse_args([
        "--pasta", "completa", "--config", "outro.toml",
        "--espera-modal", "150", "--teto-janela", "8",
        "--teto-fechamento", "12",
    ])
    assert (args.pasta, args.config) == ("completa", "outro.toml")
    assert args.espera_modal == 150
    assert (args.teto_janela, args.teto_fechamento) == (8.0, 12.0)


def test_rodar_valida_venda_e_monta_f3_f4(monkeypatch, tmp_path):
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.VK_F3 = 0x72
    perifericos.VK_F4 = 0x73

    class InterruptorWindows:
        def __init__(self, vk_inicio, vk_parada):
            self.teclas = (vk_inicio, vk_parada)

    perifericos.InterruptorWindows = InterruptorWindows
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    config = _config_completo()
    monkeypatch.setattr(completo_cli, "carregar_config", lambda _: config)
    validados = []
    monkeypatch.setattr(completo_cli, "validar_precos_venda", validados.append)
    chamadas = []
    monkeypatch.setattr(
        completo_cli,
        "executar_ciclo_completo",
        lambda *args, **kwargs: chamadas.append((args, kwargs))
        or SessaoCompleta(DesfechoSessaoCompleta.PAROU),
    )
    args = argparse.Namespace(
        pasta=str(tmp_path), config="config.toml", espera_modal=150,
        teto_janela=8.0, teto_fechamento=12.0,
    )

    assert completo_cli._rodar(args) == 0

    assert validados == [config]
    recebidos, _ = chamadas[0]
    tela, mao, recebido, pasta, interruptor, ritmo_compra, ritmo_venda = recebidos[:7]
    assert isinstance(tela, perifericos.TelaWindows)
    assert isinstance(mao, perifericos.MaoWindows)
    assert recebido is config
    assert pasta == tmp_path
    assert interruptor.teclas == (perifericos.VK_F3, perifericos.VK_F4)
    assert ritmo_compra.espera_para_o_modal_abrir == (0.15, 0.225)
    assert ritmo_venda.teto_espera_janela == 8.0
    assert ritmo_venda.teto_espera_fechamento == 12.0


def test_anuncia_f3_f4_e_main_converte_erro_em_codigo_dois(
    monkeypatch, capsys,
):
    _perifericos_falsos(monkeypatch)
    monkeypatch.setattr(
        completo_cli,
        "executar_ciclo_completo",
        lambda *a, **k: SessaoCompleta(DesfechoSessaoCompleta.PAROU),
    )
    args = montar_parser().parse_args([])

    assert completo_cli._rodar(args) == 0
    assert "F3 no jogo para comecar, F4 para pausar, F5 para encerrar" in capsys.readouterr().out

    monkeypatch.setattr(
        completo_cli,
        "_rodar",
        lambda _: (_ for _ in ()).throw(ValueError("ruim")),
    )
    monkeypatch.setattr(sys, "argv", ["mistfall-completo"])
    assert completo_cli.main() == 2


def test_entry_point_mistfall_completo_existe():
    dados = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
    assert (
        dados["project"]["scripts"]["mistfall-completo"]
        == "ferramentas.completo_cli:main"
    )


def test_imprime_o_desfecho_e_devolve_um_quando_a_sessao_aborta(monkeypatch, capsys):
    # Sem isto o operador encontrava processo terminado em codigo 0, console
    # silencioso e nenhum registro do porque — justo no modo que roda mais
    # tempo sem supervisao.
    _perifericos_falsos(monkeypatch)
    monkeypatch.setattr(
        completo_cli,
        "executar_ciclo_completo",
        lambda *a, **k: SessaoCompleta(
            DesfechoSessaoCompleta.ABORTOU,
            motivo="Compra nao confirmou filtro roxo",
            compras_enviadas=7,
            unidades_listadas=45,
        ),
    )
    args = montar_parser().parse_args([])

    assert completo_cli._rodar(args) == 1

    saida = capsys.readouterr().out
    assert "abortou" in saida
    assert "Compra nao confirmou filtro roxo" in saida


def test_imprime_o_desfecho_e_devolve_zero_quando_o_operador_para(monkeypatch, capsys):
    _perifericos_falsos(monkeypatch)
    monkeypatch.setattr(
        completo_cli,
        "executar_ciclo_completo",
        lambda *a, **k: SessaoCompleta(
            DesfechoSessaoCompleta.PAROU, compras_enviadas=3, unidades_listadas=45,
        ),
    )
    args = montar_parser().parse_args([])

    assert completo_cli._rodar(args) == 0

    saida = capsys.readouterr().out
    assert "parou" in saida
    assert "3" in saida and "45" in saida


def test_completo_roda_nova_sessao_depois_do_f4_ate_o_f5(monkeypatch, tmp_path):
    perifericos = types.ModuleType("mistfall.perifericos.windows")
    perifericos.VK_F3 = 0x72
    perifericos.VK_F4 = 0x73

    class InterruptorWindows:
        def __init__(self, vk_inicio, vk_parada):
            self.sessoes = 0

        def pediu_encerramento(self):
            self.sessoes += 1
            return self.sessoes >= 2

    perifericos.InterruptorWindows = InterruptorWindows
    perifericos.MaoWindows = type("MaoWindows", (), {})
    perifericos.TelaWindows = type("TelaWindows", (), {})
    monkeypatch.setitem(sys.modules, "mistfall.perifericos.windows", perifericos)
    monkeypatch.setattr(completo_cli, "carregar_config", lambda _: _config_completo())
    monkeypatch.setattr(completo_cli, "validar_precos_venda", lambda _: None)
    chamadas = []
    monkeypatch.setattr(
        completo_cli, "executar_ciclo_completo",
        lambda *a, **k: chamadas.append(1)
        or SessaoCompleta(DesfechoSessaoCompleta.PAROU),
    )
    args = montar_parser().parse_args([])
    args.pasta = str(tmp_path)

    assert completo_cli._rodar(args) == 0
    assert len(chamadas) == 2
