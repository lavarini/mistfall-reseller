"""Desenha sobre o print o que a deteccao enxergou.

Uso: .venv/bin/python -m ferramentas.anotar images/algum.png saida.png
"""
import sys
import cv2
import numpy as np
from mistfall.geometria import caixa_slot
from mistfall.leilao import varrer
from mistfall.tipos import Listagem

VERDE = (0, 220, 0)
VERMELHO = (0, 0, 220)

def anotar(img: np.ndarray, listagens: list[Listagem]) -> np.ndarray:
    saida = img.copy()
    for listagem in listagens:
        x0, y0, x1, y1 = caixa_slot(listagem.linha, listagem.coluna)
        alvo = listagem.item is not None
        cor = VERDE if alvo else VERMELHO
        cv2.rectangle(saida, (x0, y0), (x1, y1), cor, 2)
        nome = listagem.item.value if alvo else "-"
        preco = listagem.preco_unitario
        cv2.putText(
            saida,
            f"{nome} {preco if preco is not None else '??'}",
            (x0 + 200, y0 + 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            cor,
            2,
        )
    return saida

def main() -> None:
    entrada, saida = sys.argv[1], sys.argv[2]
    img = cv2.imread(entrada)
    cv2.imwrite(saida, anotar(img, varrer(img)))
    print("gravado", saida)

if __name__ == "__main__":
    main()
