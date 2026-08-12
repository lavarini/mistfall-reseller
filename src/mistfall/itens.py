import functools
import pathlib
import cv2
import numpy as np
from mistfall.tipos import ItemAlvo

LIMIAR = 0.70

# O melhor score tambem precisa ganhar do segundo colocado por esta margem.
# So o limiar absoluto nao basta: em images/janela.png, com a lista coberta pelo
# modal, o slot (3,0) dava dragao=0.7411 com codice=0.6459 logo atras — margem
# 0.0952, cara ou coroa. Confundir Broche (alvo 188) com Codice (alvo 281) faz o
# bot pagar 275 achando que esta comprando barato: o preco foi lido certo, o item
# e que estava errado, e a fracao de sanidade nao olha para item.
#
# Medido nos 84 slots dos 7 prints de Leilao: dos 49 slots que sao Item-alvo, o
# de pior margem tem 0.383 e o melhor 0.477. Nenhum chega perto deste piso.
# Medido em images/janela.png: o falso positivo de margem mais folgada e o slot
# (0,0), com broche=0.7378 contra lanterna=0.5379 — margem 0.199928. Por isso
# 0.25 e nao 0.20: 0.20 rejeitaria esse caso por 7 decimos de milesimo, o que e
# folga de arredondamento, nao de decisao. 0.25 fica a 0.050 do pior falso
# positivo conhecido e a 0.133 do pior acerto conhecido.
MARGEM_MINIMA = 0.25

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
    """Item-alvo do slot, ou None quando a identificacao nao e segura.

    Exige as duas coisas: score acima de LIMIAR e MARGEM_MINIMA de vantagem
    sobre o segundo colocado. Empate tecnico e desconhecido, nao palpite.
    """
    scores = pontuar(regiao)
    melhor_item = max(scores, key=scores.get)
    melhor, segundo = sorted(scores.values(), reverse=True)[:2]
    if melhor < LIMIAR or melhor - segundo < MARGEM_MINIMA:
        return None
    return melhor_item
