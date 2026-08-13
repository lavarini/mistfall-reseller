"""Gera os frames sinteticos do caminho feliz do piloto.

Eles NAO substituem print real: existem so para exercitar a orquestracao,
porque nao temos modal com Item-alvo dentro nem lista com o Ouro debitado.
Rode uma vez e versione a saida.
"""

import pathlib

import cv2

from mistfall.janela import (
    ICONE_JANELA_REL,
    PRECO_TOTAL_REL,
    PRECO_UNITARIO_REL,
)
from mistfall.ouro import CAIXA_OURO

DESTINO = pathlib.Path("fixtures/sinteticas")
FONTE_JANELA = "images/janela.png"
FONTE_LISTA = "images/broche-dragao-orbe-codice-padrao.png"

PRETO = (0, 0, 0)
CLARO = (220, 220, 220)


def _escrever_numero(img, regiao, texto: str) -> None:
    x0, y0, x1, y1 = regiao
    cv2.rectangle(img, (x0, y0), (x1, y1), PRETO, -1)
    (largura, altura), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
    orig_x = x0 + ((x1 - x0) - largura) // 2
    orig_y = y0 + ((y1 - y0) + altura) // 2
    cv2.putText(img, texto, (orig_x, orig_y), cv2.FONT_HERSHEY_SIMPLEX, 1.4, CLARO, 3)


def janela_com_dragao_a_246() -> None:
    img = cv2.imread(FONTE_JANELA)
    template = cv2.imread("templates/dragao.png")
    x0, y0, x1, y1 = ICONE_JANELA_REL
    alvo = img[y0:y1, x0:x1]
    dy = (alvo.shape[0] - template.shape[0]) // 2
    dx = (alvo.shape[1] - template.shape[1]) // 2
    alvo[dy:dy + template.shape[0], dx:dx + template.shape[1]] = template
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, PRECO_TOTAL_REL, "246")
    cv2.imwrite(str(DESTINO / "janela-dragao-246.png"), img)


def lista_com_ouro_debitado() -> None:
    img = cv2.imread(FONTE_LISTA)
    _escrever_numero(img, CAIXA_OURO, "65914")
    cv2.imwrite(str(DESTINO / "lista-ouro-65914.png"), img)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    janela_com_dragao_a_246()
    lista_com_ouro_debitado()
    print("gerados em", DESTINO)


if __name__ == "__main__":
    main()
