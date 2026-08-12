import numpy as np
from mistfall.geometria import TODOS_OS_SLOTS, regiao_icone, recorte_preco
from mistfall.itens import identificar_item
from mistfall.precos import ler_preco
from mistfall.tipos import Listagem

def varrer(img: np.ndarray) -> list[Listagem]:
    listagens = []
    for linha, coluna in TODOS_OS_SLOTS:
        listagens.append(
            Listagem(
                linha=linha,
                coluna=coluna,
                item=identificar_item(regiao_icone(img, linha, coluna)),
                preco_unitario=ler_preco(recorte_preco(img, linha, coluna)),
            )
        )
    return listagens
