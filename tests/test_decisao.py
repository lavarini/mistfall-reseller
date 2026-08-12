import pytest
from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.tipos import ItemAlvo, Listagem

def cfg(**alvos):
    return Config(
        precos_alvo={ItemAlvo[k.upper()]: v for k, v in alvos.items()},
        fracao_sanidade=0.25,
    )

def lst(item, preco, linha=0, coluna=0):
    return Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)

def test_compra_abaixo_do_preco_alvo():
    escolhida = escolher([lst(ItemAlvo.BROCHE, 150)], cfg(broche=200))
    assert escolhida.preco_unitario == 150

def test_compra_exatamente_no_preco_alvo():
    assert escolher([lst(ItemAlvo.BROCHE, 200)], cfg(broche=200)) is not None

def test_ignora_acima_do_preco_alvo():
    assert escolher([lst(ItemAlvo.BROCHE, 201)], cfg(broche=200)) is None

def test_ignora_o_que_nao_e_item_alvo():
    assert escolher([lst(None, 10)], cfg(broche=200)) is None

def test_ignora_item_sem_preco_alvo_configurado():
    assert escolher([lst(ItemAlvo.ADAGA, 10)], cfg(broche=200)) is None

def test_ignora_preco_ilegivel():
    assert escolher([lst(ItemAlvo.BROCHE, None)], cfg(broche=200)) is None

def test_lista_vazia_nao_escolhe_nada():
    assert escolher([], cfg(broche=200)) is None

def test_escolhe_a_de_maior_margem():
    escolhida = escolher(
        [lst(ItemAlvo.BROCHE, 190, linha=0), lst(ItemAlvo.ADAGA, 120, linha=1)],
        cfg(broche=200, adaga=200),
    )
    assert escolhida.item is ItemAlvo.ADAGA

def test_empate_de_margem_escolhe_o_primeiro_em_ordem_de_leitura():
    escolhida = escolher(
        [lst(ItemAlvo.ADAGA, 150, linha=3), lst(ItemAlvo.BROCHE, 150, linha=1)],
        cfg(broche=200, adaga=200),
    )
    assert escolhida.linha == 1

def test_preco_absurdamente_baixo_e_leitura_falha_nao_pechincha():
    # 19 e menos de 25% de 200: OCR provavelmente comeu um digito
    assert escolher([lst(ItemAlvo.BROCHE, 19)], cfg(broche=200)) is None

def test_preco_na_fronteira_da_sanidade_e_aceito():
    assert escolher([lst(ItemAlvo.BROCHE, 50)], cfg(broche=200)) is not None
