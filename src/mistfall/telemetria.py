import json
from datetime import datetime
from pathlib import Path


class TelemetriaSessao:
    def __init__(self, pasta: Path, inicio_monotonico: float) -> None:
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.inicio_monotonico = inicio_monotonico

    @staticmethod
    def _acrescentar(caminho: Path, dados: dict) -> None:
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(dados, ensure_ascii=False) + "\n")

    def registrar_ouro(
        self,
        volta: int,
        ouro: int | None,
        instante: float,
        horario: datetime,
    ) -> None:
        self._acrescentar(
            self.pasta / "telemetria-ouro.jsonl",
            {
                "volta": volta,
                "instante_monotonico_ms": round(
                    (instante - self.inicio_monotonico) * 1000, 1
                ),
                "horario": horario.isoformat(),
                "ouro": ouro,
                "origem": "pre_voo",
            },
        )

    def registrar_intervalo(
        self,
        volta: int,
        proximo_inicio: float,
        espera_ms: float,
        intervalo_ms: float,
    ) -> None:
        self._acrescentar(
            self.pasta / "tempos-do-laco.jsonl",
            {
                "volta": volta,
                "proximo_inicio_monotonico_ms": round(
                    (proximo_inicio - self.inicio_monotonico) * 1000, 1
                ),
                "espera_efetiva_ms": round(espera_ms, 1),
                "intervalo_entre_inicios_ms": round(intervalo_ms, 1),
            },
        )
