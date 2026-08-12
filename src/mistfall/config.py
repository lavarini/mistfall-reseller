import tomllib
from dataclasses import dataclass
from pathlib import Path
from mistfall.tipos import ItemAlvo

@dataclass(frozen=True)
class Config:
    precos_alvo: dict[ItemAlvo, int]
    fracao_sanidade: float

def carregar_config(caminho: str | Path = "config.toml") -> Config:
    dados = tomllib.loads(Path(caminho).read_text(encoding="utf-8"))
    return Config(
        precos_alvo={
            ItemAlvo(nome): int(valor)
            for nome, valor in dados["precos_alvo"].items()
        },
        fracao_sanidade=float(dados.get("fracao_sanidade", 0.25)),
    )
