"""Aplica uma funcao a varios itens em paralelo, preservando a ordem.

Existe porque 96% do custo da varredura e OCR de preco, e o pytesseract nao
faz OCR em Python: ele grava a imagem em arquivo temporario e roda o binario
do tesseract como subprocesso. O GIL nao e o gargalo, entao threads escalam —
12 OCRs caem de 1725 ms para 578 ms com quatro trabalhadores.

Mora num lugar so de proposito: ThreadPoolExecutor solto em cada chamador
viraria a quarta copia de logica repetida neste projeto.
"""

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

# Quatro da ganho de 3x e sobra CPU para o jogo, que roda na mesma maquina e
# precisa desenhar a tela que o bot vai capturar. Doze renderia mais 165 ms e
# disputaria tudo.
TRABALHADORES_PADRAO = 4

E = TypeVar("E")
S = TypeVar("S")


def mapear(funcao: Callable[[E], S], itens: Iterable[E],
           trabalhadores: int = TRABALHADORES_PADRAO) -> list[S]:
    """Devolve os resultados na ordem da entrada, sempre.

    Com `trabalhadores=1` roda de verdade na thread do chamador — e a saida
    para depurar e para isolar a paralelizacao de qualquer suspeita.
    """
    if trabalhadores < 1:
        raise ValueError(f"trabalhadores precisa ser >= 1, recebi {trabalhadores}")
    itens = list(itens)
    if trabalhadores == 1 or not itens:
        return [funcao(item) for item in itens]
    with ThreadPoolExecutor(max_workers=trabalhadores) as executor:
        return list(executor.map(funcao, itens))
