"""Gera os frames sinteticos do caminho feliz do piloto.

Eles NAO substituem print real: existem so para exercitar a orquestracao,
porque nao temos modal com Item-alvo dentro nem lista com o Ouro debitado.
Rode uma vez e versione a saida.
"""

import pathlib

import cv2

from mistfall.geometria import regiao_icone
from mistfall.janela import (
    ICONE_JANELA_REL,
    PRECO_TOTAL_REL,
    PRECO_UNITARIO_REL,
    QUANTIDADE_REL,
)
from mistfall.ouro import CAIXA_OURO

DESTINO = pathlib.Path("fixtures/sinteticas")
FONTE_JANELA = "images/janela.png"
FONTE_LISTA = "images/broche-dragao-orbe-codice-padrao.png"
# Slot do Dragao no print de lista acima — e um Dragao desenhado pelo jogo,
# nao o template. Serve de icone "real" para as fixtures de escala.
SLOT_DO_DRAGAO = (2, 1)

PRETO = (0, 0, 0)
CLARO = (220, 220, 220)


def _apagar(img, regiao) -> None:
    """Pinta a regiao de preto: o campo fica ilegivel para o OCR."""
    x0, y0, x1, y1 = regiao
    cv2.rectangle(img, (x0, y0), (x1, y1), PRETO, -1)


def _escrever_numero(img, regiao, texto: str) -> None:
    _apagar(img, regiao)
    x0, y0, x1, y1 = regiao
    (largura, altura), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
    orig_x = x0 + ((x1 - x0) - largura) // 2
    orig_y = y0 + ((y1 - y0) + altura) // 2
    cv2.putText(img, texto, (orig_x, orig_y), cv2.FONT_HERSHEY_SIMPLEX, 1.4, CLARO, 3)


def _colar_no_icone(img, recorte) -> None:
    """Centraliza `recorte` na regiao do icone do modal.

    Recorte maior que a regiao e aparado pelo centro — e o que acontece de
    verdade quando o modal desenha o icone maior do que a lista.
    """
    x0, y0, x1, y1 = ICONE_JANELA_REL
    alvo = img[y0:y1, x0:x1]
    sobra_y = max(0, recorte.shape[0] - alvo.shape[0]) // 2
    sobra_x = max(0, recorte.shape[1] - alvo.shape[1]) // 2
    recorte = recorte[sobra_y:sobra_y + alvo.shape[0],
                      sobra_x:sobra_x + alvo.shape[1]]
    dy = (alvo.shape[0] - recorte.shape[0]) // 2
    dx = (alvo.shape[1] - recorte.shape[1]) // 2
    alvo[dy:dy + recorte.shape[0], dx:dx + recorte.shape[1]] = recorte


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


def janela_com_dragao_a_999() -> None:
    # Item bate (Dragao), Preco diverge (999 contra os 246 decididos).
    # Isola a conferencia de Preco Unitario.
    img = cv2.imread(FONTE_JANELA)
    template = cv2.imread("templates/dragao.png")
    x0, y0, x1, y1 = ICONE_JANELA_REL
    alvo = img[y0:y1, x0:x1]
    dy = (alvo.shape[0] - template.shape[0]) // 2
    dx = (alvo.shape[1] - template.shape[1]) // 2
    alvo[dy:dy + template.shape[0], dx:dx + template.shape[1]] = template
    _escrever_numero(img, PRECO_UNITARIO_REL, "999")
    _escrever_numero(img, PRECO_TOTAL_REL, "999")
    cv2.imwrite(str(DESTINO / "janela-dragao-999.png"), img)


def janela_com_dragao_a_246_qtd_5() -> None:
    # Item e Preco Unitario batem, Quantidade diverge (5 em vez de 1).
    # Isola a conferencia de Quantidade.
    img = cv2.imread(FONTE_JANELA)
    template = cv2.imread("templates/dragao.png")
    x0, y0, x1, y1 = ICONE_JANELA_REL
    alvo = img[y0:y1, x0:x1]
    dy = (alvo.shape[0] - template.shape[0]) // 2
    dx = (alvo.shape[1] - template.shape[1]) // 2
    alvo[dy:dy + template.shape[0], dx:dx + template.shape[1]] = template
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, QUANTIDADE_REL, "5")
    _escrever_numero(img, PRECO_TOTAL_REL, "1230")
    cv2.imwrite(str(DESTINO / "janela-dragao-246-qtd-5.png"), img)


def janela_com_orbe_a_246() -> None:
    # Preco bate (246), Item diverge (Orbe em vez do Dragao decidido).
    # Isola a conferencia de Item.
    img = cv2.imread(FONTE_JANELA)
    template = cv2.imread("templates/orbe.png")
    x0, y0, x1, y1 = ICONE_JANELA_REL
    alvo = img[y0:y1, x0:x1]
    dy = (alvo.shape[0] - template.shape[0]) // 2
    dx = (alvo.shape[1] - template.shape[1]) // 2
    alvo[dy:dy + template.shape[0], dx:dx + template.shape[1]] = template
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, PRECO_TOTAL_REL, "246")
    cv2.imwrite(str(DESTINO / "janela-orbe-246.png"), img)


def janela_com_dragao_a_246_total_250() -> None:
    # Item, Preco Unitario e Quantidade batem; so o Preco Total nao fecha
    # com 1 x 246. Isola a conferencia de Preco Total contra o unitario.
    img = cv2.imread(FONTE_JANELA)
    _colar_no_icone(img, cv2.imread("templates/dragao.png"))
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, PRECO_TOTAL_REL, "250")
    cv2.imwrite(str(DESTINO / "janela-dragao-246-total-250.png"), img)


def _janela_com_dragao_e_campo_apagado(regiao, nome: str) -> None:
    img = cv2.imread(FONTE_JANELA)
    _colar_no_icone(img, cv2.imread("templates/dragao.png"))
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, PRECO_TOTAL_REL, "246")
    _apagar(img, regiao)
    cv2.imwrite(str(DESTINO / nome), img)


def janelas_com_campo_ilegivel() -> None:
    # Um campo apagado de cada vez: cada uma isola uma conferencia de
    # "leitura ilegivel -> aborta", que sem elas nao tem teste que morda.
    _janela_com_dragao_e_campo_apagado(
        PRECO_UNITARIO_REL, "janela-dragao-preco-ilegivel.png")
    _janela_com_dragao_e_campo_apagado(
        QUANTIDADE_REL, "janela-dragao-quantidade-ilegivel.png")
    _janela_com_dragao_e_campo_apagado(
        PRECO_TOTAL_REL, "janela-dragao-total-ilegivel.png")


def janela_com_espelho_a_246() -> None:
    # Icone intocado: o print real mostra Espelho Adornado, que nao e
    # Item-alvo e nao e reconhecido. Os numeros batem com a Listagem, entao
    # a unica divergencia possivel e o icone.
    img = cv2.imread(FONTE_JANELA)
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, PRECO_TOTAL_REL, "246")
    cv2.imwrite(str(DESTINO / "janela-espelho-246.png"), img)


def lista_com_ouro_ilegivel() -> None:
    img = cv2.imread(FONTE_LISTA)
    _apagar(img, CAIXA_OURO)
    cv2.imwrite(str(DESTINO / "lista-ouro-ilegivel.png"), img)


def janelas_com_icone_fora_de_escala() -> None:
    """Modal com o Dragao desenhado maior e menor do que na lista.

    O icone colado NAO e o template: e o recorte do Dragao como o jogo o
    desenha na lista, reescalado. Ninguem sabe em que escala o modal
    desenha o icone, e um erro de 5% ja derrubava o casamento para None.
    """
    lista = cv2.imread(FONTE_LISTA)
    icone = regiao_icone(lista, *SLOT_DO_DRAGAO)
    for fator, nome in ((0.92, "janela-dragao-246-icone-092x.png"),
                        (1.08, "janela-dragao-246-icone-108x.png")):
        img = cv2.imread(FONTE_JANELA)
        interpolacao = cv2.INTER_AREA if fator < 1 else cv2.INTER_CUBIC
        _colar_no_icone(img, cv2.resize(icone, None, fx=fator, fy=fator,
                                        interpolation=interpolacao))
        _escrever_numero(img, PRECO_UNITARIO_REL, "246")
        _escrever_numero(img, PRECO_TOTAL_REL, "246")
        cv2.imwrite(str(DESTINO / nome), img)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    janela_com_dragao_a_246()
    lista_com_ouro_debitado()
    janela_com_dragao_a_999()
    janela_com_dragao_a_246_qtd_5()
    janela_com_orbe_a_246()
    janela_com_dragao_a_246_total_250()
    janelas_com_campo_ilegivel()
    janela_com_espelho_a_246()
    lista_com_ouro_ilegivel()
    janelas_com_icone_fora_de_escala()
    print("gerados em", DESTINO)


if __name__ == "__main__":
    main()
