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
