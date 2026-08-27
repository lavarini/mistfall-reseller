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
    VENDA = "venda"
    JANELA_VENDA = "janela_venda"


# O Bau e um indice inteiro base zero, nao um enum: o numero de abas do
# Armazem muda entre seasons, entao fixar os membros aqui foi o que travou a
# leitura em quatro. Quem descobre quantos existem e `contar_baus`.
#
# A ordenacao automatica do jogo empurra equipamento para o primeiro Bau, entao
# a Venda comeca no segundo e o primeiro nunca e varrido.
BAU_INICIAL = 1

# Um stack de Item-alvo vai ate 3 unidades, e uma Venda lista um stack
# inteiro. O lote e o tanto que justifica uma ida a aba Vender: quinze
# stacks, quarenta e cinco unidades. Os dois numeros sao a mesma coisa em
# unidades diferentes, e por isso moram juntos — separados, divergem.
UNIDADES_POR_STACK = 3
LOTE_DE_VENDA_EM_STACKS = 15
LOTE_DE_VENDA_EM_UNIDADES = LOTE_DE_VENDA_EM_STACKS * UNIDADES_POR_STACK


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
