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


class Interruptor(Protocol):
    """O par F2/F3 visto pelo bot.

    Terceira fronteira de IO, pela mesma razao das outras duas: a decisao de
    parar e testavel no macOS, e so a leitura da tecla mora no Windows.
    """

    def esperar_inicio(self) -> None:
        """Bloqueia ate o operador pedir para comecar."""
        ...

    def pediram_parada(self) -> bool:
        """Foi pedida parada desde a ultima pergunta?

        E pergunta com trinco, nao leitura instantanea: uma tecla apertada e
        solta enquanto o bot dormia continua registrada na pergunta seguinte.
        Sem isso o F3 so pegaria se fosse segurado no instante da checagem.
        """
        ...
