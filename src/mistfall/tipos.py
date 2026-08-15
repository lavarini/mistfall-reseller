from dataclasses import dataclass
from enum import Enum, IntEnum

class ItemAlvo(Enum):
    BROCHE = "broche"
    ADAGA = "adaga"
    LANTERNA = "lanterna"
    ORBE = "orbe"
    DRAGAO = "dragao"
    REDE = "rede"
    CODICE = "codice"

class EstadoTela(Enum):
    LISTA = "lista"
    JANELA_CONFIRMACAO = "janela_confirmacao"
    OUTRA_CATEGORIA = "outra_categoria"
    DESCONHECIDO = "desconhecido"


class Bau(IntEnum):
    PRIMEIRO = 0
    SEGUNDO = 1
    TERCEIRO = 2
    QUARTO = 3


@dataclass(frozen=True)
class CapacidadeVenda:
    ocupadas: int
    limite: int


@dataclass(frozen=True)
class SlotArmazem:
    linha: int
    coluna: int
    item: ItemAlvo | None
    quantidade: int | None

@dataclass(frozen=True)
class Listagem:
    linha: int
    coluna: int
    item: ItemAlvo | None
    preco_unitario: int | None
