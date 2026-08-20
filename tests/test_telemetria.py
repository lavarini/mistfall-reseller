import json
from datetime import datetime, timezone

from mistfall.fluxo import AcaoFluxo, EstadoFluxo, ModoFluxo
from mistfall.telemetria import TelemetriaSessao


def test_registra_ouro_inclusive_nulo_sem_corromper_linhas(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    horario = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)
    telemetria.registrar_ouro(1, 500, 10.25, horario)
    telemetria.registrar_ouro(2, None, 11.00, horario)

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "telemetria-ouro.jsonl").read_text().splitlines()
    ]

    assert linhas == [
        {
            "volta": 1,
            "instante_monotonico_ms": 250.0,
            "horario": horario.isoformat(),
            "ouro": 500,
            "origem": "pre_voo",
        },
        {
            "volta": 2,
            "instante_monotonico_ms": 1000.0,
            "horario": horario.isoformat(),
            "ouro": None,
            "origem": "pre_voo",
        },
    ]


def test_registra_intervalo_real_entre_voltas(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    telemetria.registrar_intervalo(
        3, proximo_inicio=12.5, espera_ms=150.2, intervalo_ms=980.4
    )

    linha = json.loads((tmp_path / "tempos-do-laco.jsonl").read_text())

    assert linha == {
        "volta": 3,
        "proximo_inicio_monotonico_ms": 2500.0,
        "espera_efetiva_ms": 150.2,
        "intervalo_entre_inicios_ms": 980.4,
    }


def test_registra_evento_do_fluxo_completo_com_estado_e_motivo_da_transicao(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    horario = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)
    estado = EstadoFluxo(
        estoque_estimado=48,
        intencoes_desde_reset=2,
        resets_desde_intencao=3,
        modo=ModoFluxo.LENTO,
        capacidade_observada=(12, 40),
    )

    telemetria.registrar_evento_fluxo(
        5, 10.9, horario, estado, unidades_listadas=45,
        acao=AcaoFluxo.VENDER_POR_FLUXO_LENTO,
    )

    linha = json.loads((tmp_path / "eventos-do-fluxo.jsonl").read_text())

    assert linha == {
        "volta": 5,
        "instante_monotonico_ms": 900.0,
        "horario": horario.isoformat(),
        "modo": "lento",
        "intencoes_desde_reset": 2,
        "resets_desde_intencao": 3,
        "estoque_estimado": 48,
        "unidades_listadas": 45,
        "capacidade_observada": [12, 40],
        "motivo_transicao": "vender_por_fluxo_lento",
    }


def test_registra_evento_do_fluxo_completo_sem_capacidade_observada(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    horario = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)
    estado = EstadoFluxo()

    telemetria.registrar_evento_fluxo(
        1, 10.0, horario, estado, unidades_listadas=0,
        acao=AcaoFluxo.EXECUTAR_COMPRA,
    )

    linha = json.loads((tmp_path / "eventos-do-fluxo.jsonl").read_text())

    assert linha["capacidade_observada"] is None
    assert linha["modo"] == "rapido"
    assert linha["motivo_transicao"] == "executar_compra"


def test_eventos_do_fluxo_nao_interfere_nos_jsonl_existentes(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    horario = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)

    telemetria.registrar_ouro(1, 500, 10.25, horario)
    telemetria.registrar_intervalo(1, proximo_inicio=10.4, espera_ms=50.0, intervalo_ms=400.0)
    telemetria.registrar_evento_fluxo(
        1, 10.4, horario, EstadoFluxo(), unidades_listadas=0,
        acao=AcaoFluxo.CONTINUAR_COMPRA,
    )

    arquivos = sorted(caminho.name for caminho in tmp_path.iterdir())
    assert arquivos == [
        "eventos-do-fluxo.jsonl",
        "telemetria-ouro.jsonl",
        "tempos-do-laco.jsonl",
    ]

    ouro = json.loads((tmp_path / "telemetria-ouro.jsonl").read_text())
    assert ouro["ouro"] == 500
    intervalo = json.loads((tmp_path / "tempos-do-laco.jsonl").read_text())
    assert intervalo["espera_efetiva_ms"] == 50.0
