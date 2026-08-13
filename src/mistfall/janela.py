"""Leitura dentro da Janela de Confirmacao.

E visao pura — imagem para dado. Nao tem nada de IO, e por isso nao vive
em perifericos.

As regioes foram medidas contra images/janela.png, que le 237 no Preco
Unitario, 1 na Quantidade e 237 no Preco Total.
"""

import cv2
import numpy as np
import pytesseract

from mistfall.geometria import conferir_resolucao
from mistfall.itens import identificar_item, pontuar
from mistfall.tipos import ItemAlvo

PRECO_UNITARIO_REL = (1500, 628, 1900, 674)
QUANTIDADE_REL = (1500, 730, 1900, 776)
PRECO_TOTAL_REL = (1500, 826, 1900, 872)
# O recorte do icone tem 116x128 — exatamente a dimensao da regiao de busca
# da lista, entao os sete templates existentes servem sem adaptacao.
ICONE_JANELA_REL = (1390, 448, 1518, 564)

# Escalas em que o modal pode estar desenhando o icone, em relacao ao tamanho
# que ele tem na lista (de onde os templates foram extraidos).
#
# Ninguem tem print de modal com Item-alvo dentro, entao ninguem sabe se as
# duas escalas sao iguais. E o casamento nao perdoa: medido sobre um Dragao
# real da lista, 1.000x da 0.9358 e identifica, 0.950x cai para 0.7818 e
# devolve None. 5% de diferenca ja derruba o positivo.
#
# A varredura vive aqui, e nao em `itens`: la ela mexeria na deteccao da
# lista, que esta validada em 84/84 slots e nao tem duvida de escala nenhuma.
ESCALAS_DO_ICONE = (0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15)

_CONFIG_OCR = "--psm 7 -c tessedit_char_whitelist=0123456789"


def _numero(img: np.ndarray, regiao: tuple[int, int, int, int]) -> int | None:
    conferir_resolucao(img)
    x0, y0, x1, y1 = regiao
    cinza = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    texto = pytesseract.image_to_string(binaria, config=_CONFIG_OCR).strip()
    return int(texto) if texto.isdigit() else None


def ler_preco_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, PRECO_UNITARIO_REL)


def ler_quantidade_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, QUANTIDADE_REL)


def ler_preco_total_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, PRECO_TOTAL_REL)


def _regiao_do_icone(img: np.ndarray) -> np.ndarray:
    conferir_resolucao(img)
    x0, y0, x1, y1 = ICONE_JANELA_REL
    return img[y0:y1, x0:x1]


def _no_tamanho_da_lista(regiao: np.ndarray, escala: float) -> np.ndarray:
    """Desfaz a escala: se o modal desenha 1.10x, encolhe 1/1.10."""
    if escala == 1.0:
        return regiao
    return cv2.resize(regiao, None, fx=1 / escala, fy=1 / escala,
                      interpolation=cv2.INTER_CUBIC)


def _melhor_escala(regiao: np.ndarray) -> tuple[float, dict[ItemAlvo, float]]:
    """A escala que produziu o melhor score, e os sete scores nela.

    Decide por escala inteira, e nao pelo melhor score de cada item em sua
    escala predileta: o modal desenha o icone numa escala so, e um maximo por
    item inflaria a margem de quem casou por acaso em algum tamanho.
    """
    return max(((escala, pontuar(_no_tamanho_da_lista(regiao, escala)))
                for escala in ESCALAS_DO_ICONE),
               key=lambda candidato: max(candidato[1].values()))


def pontuar_icone_da_janela(img: np.ndarray) -> tuple[float, dict[ItemAlvo, float]]:
    """Escala vencedora e os sete scores nela — diagnostico para o relatorio.

    Um aborto por icone e o desfecho mais provavel da primeira execucao no
    Windows, e sem estes numeros o operador volta so com "o modal mostra None".
    """
    return _melhor_escala(_regiao_do_icone(img))


def ler_item_da_janela(img: np.ndarray) -> ItemAlvo | None:
    regiao = _regiao_do_icone(img)
    escala, _ = _melhor_escala(regiao)
    return identificar_item(_no_tamanho_da_lista(regiao, escala))
