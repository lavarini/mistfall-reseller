import numpy as np
from mistfall.cliques import AreaClique
from mistfall.tipos import Listagem, ItemAlvo, EstadoTela  # noqa: F401

RESOLUCAO = (2560, 1440)
SLOT_TOPO = 287
SLOT_PASSO = 178.6
SLOT_COLUNAS = (459, 1470)
SLOT_LARGURA = 1011
SLOT_ALTURA = 154
LINHAS = 6
MEIA_LARGURA_CLIQUE_SLOT = 20
MEIA_ALTURA_CLIQUE_SLOT = 26
MEIA_LARGURA_CLIQUE_CATEGORIA = 60
MEIA_ALTURA_CLIQUE_CATEGORIA = 18

# Regiao de BUSCA do icone. O template e menor que ela (ver MARGEM_TEMPLATE),
# para o matchTemplate poder deslizar e absorver o arredondamento de SLOT_PASSO.
BUSCA_ICONE_REL = (69, 29, 197, 145)
MARGEM_TEMPLATE = 14
PRECO_REL = (931, 98, 1011, 143)

# Centros das linhas do menu lateral medidos nos prints 2560x1440. O x=220
# fica no centro da faixa horizontal 80-360 usada para reconhecer a Categoria;
# as linhas vizinhas mantem o mesmo x e avancam 72 px em y.
CATEGORIA_MATERIAL_CONSTRUCAO = (220, 705)
CATEGORIA_MATERIAL_FORJA = (220, 777)
CATEGORIA_CHAVE = (220, 849)

TODOS_OS_SLOTS = [(linha, coluna) for linha in range(LINHAS) for coluna in range(2)]

def conferir_resolucao(img: np.ndarray) -> None:
    """Recusa qualquer imagem que nao seja 2560x1440.

    Ponto unico do contrato de resolucao: geometria, ouro e estado passam por
    aqui. Resolucao diferente e erro, nao caso a tratar (ADR-0002) — devolver
    None seria indistinguivel de uma leitura legitimamente vazia.
    """
    altura, largura = img.shape[:2]
    if (largura, altura) != RESOLUCAO:
        raise ValueError(
            f"esperava 2560x1440, recebi {largura}x{altura}; "
            "a deteccao e acoplada a essa resolucao (ADR-0002)"
        )

def caixa_slot(linha: int, coluna: int) -> tuple[int, int, int, int]:
    x0 = SLOT_COLUNAS[coluna]
    y0 = int(SLOT_TOPO + SLOT_PASSO * linha)
    return x0, y0, x0 + SLOT_LARGURA, y0 + SLOT_ALTURA

def area_clique_slot(linha: int, coluna: int) -> AreaClique:
    x0, y0, x1, y1 = caixa_slot(linha, coluna)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    return (
        cx - MEIA_LARGURA_CLIQUE_SLOT,
        cy - MEIA_ALTURA_CLIQUE_SLOT,
        cx + MEIA_LARGURA_CLIQUE_SLOT,
        cy + MEIA_ALTURA_CLIQUE_SLOT,
    )

def area_clique_categoria(centro: tuple[int, int]) -> AreaClique:
    cx, cy = centro
    return (
        cx - MEIA_LARGURA_CLIQUE_CATEGORIA,
        cy - MEIA_ALTURA_CLIQUE_CATEGORIA,
        cx + MEIA_LARGURA_CLIQUE_CATEGORIA,
        cy + MEIA_ALTURA_CLIQUE_CATEGORIA,
    )

def _recorte(img, linha, coluna, rel):
    conferir_resolucao(img)
    x0, y0, _, _ = caixa_slot(linha, coluna)
    dx0, dy0, dx1, dy1 = rel
    return img[y0 + dy0 : y0 + dy1, x0 + dx0 : x0 + dx1]

def regiao_icone(img: np.ndarray, linha: int, coluna: int) -> np.ndarray:
    """Regiao de busca do icone — maior que o template, de proposito."""
    return _recorte(img, linha, coluna, BUSCA_ICONE_REL)

def recorte_preco(img: np.ndarray, linha: int, coluna: int) -> np.ndarray:
    return _recorte(img, linha, coluna, PRECO_REL)
