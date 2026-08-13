"""A fronteira de IO do bot.

Tudo o que sabe que existe um mouse, um teclado e uma tela mora atras
destes dois protocolos. O orquestrador nao sabe se fala com o Windows ou
com um duble.
"""

from typing import Protocol

import numpy as np


class Tela(Protocol):
    def capturar(self) -> np.ndarray:
        """Devolve a tela atual como BGR 2560x1440."""
        ...


class Mao(Protocol):
    def clicar(self, x: int, y: int) -> None: ...

    def apertar_espaco(self) -> None: ...

    def apertar_esc(self) -> None:
        """Desfaz: fecha a Janela de Confirmacao sem comprar."""
        ...
