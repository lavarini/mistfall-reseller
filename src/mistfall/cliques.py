"""Sorteio puro de pontos dentro de areas seguras de clique."""

import random

AreaClique = tuple[int, int, int, int]


def sortear_ponto(
    area: AreaClique,
    sorteio: random.Random,
) -> tuple[int, int]:
    x0, y0, x1, y1 = area
    if x0 > x1 or y0 > y1:
        raise ValueError(f"area de clique invertida: {area}")
    return sorteio.randint(x0, x1), sorteio.randint(y0, y1)
