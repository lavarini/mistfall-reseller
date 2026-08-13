"""Conferem que as fixtures sinteticas contem o que dizem conter.

**Estas fixtures nao sao prova de visao.** Sao prints reais com numeros
colados por cima e icones colados dentro, geradas por
`ferramentas/sintetizar_fixtures.py` porque nao existe print de modal com
Item-alvo dentro nem de lista com o Ouro ja debitado. Verde aqui significa
"o sintetizador escreveu o que prometeu, e o OCR le de volta" — nada sobre
o jogo. O unico negativo real do modal e images/janela.png, em
tests/test_janela.py.
"""

import cv2
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_preco_total_da_janela, ler_quantidade_da_janela,
)
from mistfall.ouro import ler_ouro
from mistfall.tipos import ItemAlvo

JANELA_DRAGAO = "fixtures/sinteticas/janela-dragao-246.png"
LISTA_DEBITADA = "fixtures/sinteticas/lista-ouro-65914.png"

def test_modal_sintetico_mostra_dragao():
    assert ler_item_da_janela(cv2.imread(JANELA_DRAGAO)) is ItemAlvo.DRAGAO

def test_modal_sintetico_le_246_no_preco_unitario():
    assert ler_preco_da_janela(cv2.imread(JANELA_DRAGAO)) == 246

def test_modal_sintetico_le_246_no_preco_total():
    assert ler_preco_total_da_janela(cv2.imread(JANELA_DRAGAO)) == 246

def test_modal_sintetico_preserva_a_quantidade_original():
    # A Quantidade nao foi mexida: continua vindo do print real.
    assert ler_quantidade_da_janela(cv2.imread(JANELA_DRAGAO)) == 1

def test_lista_sintetica_tem_o_ouro_debitado():
    assert ler_ouro(cv2.imread(LISTA_DEBITADA)) == 65914

def test_lista_sintetica_com_ouro_apagado_nao_le_ouro():
    assert ler_ouro(cv2.imread("fixtures/sinteticas/lista-ouro-ilegivel.png")) is None


ICONE_MENOR = "fixtures/sinteticas/janela-dragao-246-icone-092x.png"
ICONE_MAIOR = "fixtures/sinteticas/janela-dragao-246-icone-108x.png"

# Estas duas nao colam o template: colam o Dragao recortado de um print real
# da lista, reescalado. Nao provam que o jogo desenha assim — provam que uma
# diferenca de escala entre a lista e o modal deixa de derrubar o casamento.
# Sem a varredura de ESCALAS_DO_ICONE, as duas devolvem None.

def test_modal_com_icone_8_por_cento_menor_ainda_e_dragao():
    assert ler_item_da_janela(cv2.imread(ICONE_MENOR)) is ItemAlvo.DRAGAO

def test_modal_com_icone_8_por_cento_maior_ainda_e_dragao():
    assert ler_item_da_janela(cv2.imread(ICONE_MAIOR)) is ItemAlvo.DRAGAO
