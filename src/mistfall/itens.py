import functools
import pathlib
import cv2
import numpy as np
from mistfall.tipos import ItemAlvo

LIMIAR = 0.70
# Resolvida a partir do arquivo, nunca do diretorio corrente: a camada de visao
# e importada por ferramentas e pelo loop, que nao rodam necessariamente da raiz.
_PASTA = pathlib.Path(__file__).resolve().parents[2] / "templates"

@functools.cache
def _templates() -> dict[ItemAlvo, np.ndarray]:
    carregados = {}
    for item in ItemAlvo:
        caminho = _PASTA / f"{item.value}.png"
        if not caminho.exists():
            raise FileNotFoundError(
                f"template ausente: {caminho}. "
                "Rode: .venv/bin/python -m ferramentas.extrair_templates"
            )
        carregados[item] = cv2.imread(str(caminho))
    return carregados

def pontuar(regiao: np.ndarray) -> dict[ItemAlvo, float]:
    """Score de cada Item-alvo para a regiao de busca.

    O template e menor que a regiao, entao matchTemplate desliza e devolve
    o melhor alinhamento — e assim absorve o deslocamento do arredondamento
    de SLOT_PASSO.
    """
    return {
        item: float(cv2.matchTemplate(regiao, template, cv2.TM_CCOEFF_NORMED).max())
        for item, template in _templates().items()
    }

def identificar_item(regiao: np.ndarray) -> ItemAlvo | None:
    scores = pontuar(regiao)
    melhor_item = max(scores, key=scores.get)
    return melhor_item if scores[melhor_item] >= LIMIAR else None
