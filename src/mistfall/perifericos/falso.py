"""Dubles da fronteira de IO, para exercitar o piloto sem jogo nem Windows."""

import cv2
import numpy as np


class TelaFalsa:
    """Serve uma sequencia roteirizada de PNGs.

    Depois do ultimo frame, repete o ultimo indefinidamente — o piloto
    pergunta quantas vezes quiser sem estourar o roteiro.
    """

    def __init__(self, caminhos: list[str]) -> None:
        if not caminhos:
            raise ValueError("TelaFalsa precisa de pelo menos um frame")
        self._frames = [cv2.imread(c) for c in caminhos]
        for caminho, frame in zip(caminhos, self._frames):
            if frame is None:
                raise ValueError(f"nao consegui ler o frame {caminho}")
        self._proximo = 0
        self.capturas_feitas = 0

    def capturar(self) -> np.ndarray:
        frame = self._frames[min(self._proximo, len(self._frames) - 1)]
        self._proximo += 1
        self.capturas_feitas += 1
        return frame.copy()


class MaoFalsa:
    """Grava o que lhe pediram, sem fazer nada."""

    def __init__(self) -> None:
        self.acoes: list[tuple] = []

    def clicar(self, x: int, y: int) -> None:
        self.acoes.append(("clicar", x, y))

    def apertar_espaco(self) -> None:
        self.acoes.append(("apertar_espaco",))

    def apertar_esc(self) -> None:
        self.acoes.append(("apertar_esc",))
