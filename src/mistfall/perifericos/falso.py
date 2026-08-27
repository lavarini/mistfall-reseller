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

    def mover(self, x: int, y: int) -> None:
        self.acoes.append(("mover", x, y))

    def clicar(self, x: int, y: int) -> None:
        self.acoes.append(("clicar", x, y))

    def apertar_espaco(self) -> None:
        self.acoes.append(("apertar_espaco",))

    def apertar_esc(self) -> None:
        self.acoes.append(("apertar_esc",))

    def selecionar_tudo(self) -> None:
        self.acoes.append(("selecionar_tudo",))

    def digitar_numero(self, numero: int) -> None:
        self.acoes.append(("digitar_numero", numero))


class InterruptorFalso:
    """Interruptor roteirizado: para na enesima pergunta, ou nunca.

    Conta perguntas e inicios para os testes do ciclo poderem afirmar quantas
    vezes o laco consultou a parada, e nao so o efeito dela.
    """

    def __init__(self, parar_na_pergunta: int | None = None,
                 encerrar_na_pergunta: int | None = None) -> None:
        self.perguntas = 0
        self.inicios = 0
        self._parar_na = parar_na_pergunta
        self._encerrar_na = encerrar_na_pergunta

    def esperar_inicio(self) -> None:
        self.inicios += 1

    def pediram_parada(self) -> bool:
        self.perguntas += 1
        return self._parar_na is not None and self.perguntas >= self._parar_na

    def pediu_encerramento(self) -> bool:
        self.perguntas += 1
        return self._encerrar_na is not None and self.perguntas >= self._encerrar_na
