import json
from datetime import datetime, timezone

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
