from dataclasses import dataclass
from enum import Enum

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

@dataclass(frozen=True)
class Listagem:
    linha: int
    coluna: int
    item: ItemAlvo | None
    preco_unitario: int | None
