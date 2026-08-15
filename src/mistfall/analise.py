import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from mistfall.leilao import varrer_bruto
from mistfall.ouro import ler_ouro
from mistfall.tipos import Listagem


@dataclass(frozen=True)
class AnaliseInicial:
    ouro_observado: int | None
    brutas: list[Listagem]
    tempos: dict[str, float]


def _ouro(img: np.ndarray) -> tuple[int | None, float]:
    inicio = time.monotonic()
    valor = ler_ouro(img)
    return valor, (time.monotonic() - inicio) * 1000


def _listagens(img: np.ndarray) -> tuple[list[Listagem], dict[str, float]]:
    tempos: dict[str, float] = {}
    inicio = time.monotonic()
    brutas = varrer_bruto(img, tempos)
    tempos["varredura_total"] = (time.monotonic() - inicio) * 1000
    return brutas, tempos


def analisar_inicial(img: np.ndarray, *, concorrente: bool = False) -> AnaliseInicial:
    inicio = time.monotonic()
    if concorrente:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_ouro = executor.submit(_ouro, img)
            futuro_listagens = executor.submit(_listagens, img)
            ouro_observado, tempo_ouro = futuro_ouro.result()
            brutas, tempos = futuro_listagens.result()
    else:
        ouro_observado, tempo_ouro = _ouro(img)
        brutas, tempos = _listagens(img)
    tempos["ouro"] = tempo_ouro
    tempos["analise_inicial_parede"] = (time.monotonic() - inicio) * 1000
    return AnaliseInicial(ouro_observado, brutas, tempos)
