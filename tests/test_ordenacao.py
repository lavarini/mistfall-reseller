"""O Leilao lista por Preco-unitario crescente; quem desobedece foi lido errado.

Testes com numeros escritos a mao, sem imagem: a regra e aritmetica pura.
"""
import pytest
from mistfall.leilao import conferir_ordenacao
from mistfall.tipos import ItemAlvo, Listagem

def listagens(precos, item=ItemAlvo.BROCHE):
    return [
        Listagem(linha=posicao // 2, coluna=posicao % 2, item=item, preco_unitario=preco)
        for posicao, preco in enumerate(precos)
    ]

def precos_de(listagens_conferidas):
    return [l.preco_unitario for l in listagens_conferidas]

def test_sequencia_crescente_passa_inteira():
    entrada = [188, 199, 234, 234, 237, 239, 250, 258, 260, 269, 295, 388]
    assert precos_de(conferir_ordenacao(listagens(entrada))) == entrada

def test_digito_trocado_para_baixo_e_invalidado():
    # A falha que a fracao de sanidade nao pega: 223 em vez de 293 passa no piso
    # (>= 25% do alvo) e cabe abaixo do Preco-alvo — o bot compraria pagando 293.
    conferidas = precos_de(conferir_ordenacao(listagens([195, 226, 223, 246, 260])))
    assert conferidas == [195, None, None, 246, 260]

def test_digito_trocado_para_cima_e_invalidado():
    conferidas = precos_de(conferir_ordenacao(listagens([195, 293, 226, 246, 260])))
    assert conferidas == [195, None, None, None, None]

def test_numero_truncado_e_invalidado():
    # Truncamento silencioso: 241 lido como 24. Numero cortado sai sempre menor,
    # entao sempre quebra a ordenacao.
    conferidas = precos_de(conferir_ordenacao(listagens([188, 215, 218, 24, 246])))
    assert conferidas == [None, None, None, None, 246]

def test_digito_grudado_e_invalidado():
    # 282 lido como 2892. Tudo que vem depois dele fica abaixo de 2892 e cai
    # junto: a regra e contagiosa de proposito.
    conferidas = precos_de(conferir_ordenacao(listagens([274, 281, 2892, 305, 318])))
    assert conferidas == [274, 281, None, None, None]

def test_none_do_ocr_nao_atrapalha_a_conferencia_dos_vizinhos():
    conferidas = precos_de(conferir_ordenacao(listagens([188, 215, None, 246, 253])))
    assert conferidas == [188, 215, None, 246, 253]

def test_empate_de_preco_e_ordenacao_valida():
    # Precos iguais em slots vizinhos acontecem no corpus (234, 234 e 281, 281).
    conferidas = precos_de(conferir_ordenacao(listagens([234, 234, 281, 281])))
    assert conferidas == [234, 234, 281, 281]

def test_nao_mexe_no_item_nem_na_posicao():
    conferidas = conferir_ordenacao(listagens([300, 100], item=ItemAlvo.CODICE))
    assert [(l.linha, l.coluna, l.item) for l in conferidas] == [
        (0, 0, ItemAlvo.CODICE),
        (0, 1, ItemAlvo.CODICE),
    ]

def test_lista_toda_ilegivel_continua_toda_ilegivel():
    assert precos_de(conferir_ordenacao(listagens([None, None, None]))) == [
        None,
        None,
        None,
    ]

def test_um_unico_preco_nao_tem_com_que_conflitar():
    assert precos_de(conferir_ordenacao(listagens([None, 1174, None]))) == [
        None,
        1174,
        None,
    ]
