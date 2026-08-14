import random

import pytest

from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.tipos import ItemAlvo, Listagem

def cfg(**alvos):
    return Config(precos_alvo={ItemAlvo[k.upper()]: v for k, v in alvos.items()})

def lst(item, preco, linha=0, coluna=0):
    return Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)

def sorteio():
    return random.Random(20260813)

def test_compra_no_preco_exato():
    escolhida = escolher([lst(ItemAlvo.BROCHE, 188)], cfg(broche=188), sorteio())
    assert escolhida is not None

def test_ignora_um_acima_do_corte():
    assert escolher([lst(ItemAlvo.BROCHE, 189)], cfg(broche=188), sorteio()) is None

def test_ignora_um_abaixo_do_corte():
    # Os Itens-alvo nunca ficam abaixo do corte: isso e leitura suspeita,
    # nao pechincha.
    assert escolher([lst(ItemAlvo.BROCHE, 187)], cfg(broche=188), sorteio()) is None

def test_ignora_muito_abaixo_do_corte():
    assert escolher([lst(ItemAlvo.BROCHE, 19)], cfg(broche=188), sorteio()) is None

def test_ignora_o_que_nao_e_item_alvo():
    assert escolher([lst(None, 188)], cfg(broche=188), sorteio()) is None

def test_ignora_item_sem_corte_configurado():
    assert escolher([lst(ItemAlvo.ADAGA, 199)], cfg(broche=188), sorteio()) is None

def test_ignora_preco_ilegivel():
    assert escolher([lst(ItemAlvo.BROCHE, None)], cfg(broche=188), sorteio()) is None

def test_lista_vazia_nao_escolhe_nada():
    assert escolher([], cfg(broche=188), sorteio()) is None

def test_um_unico_candidato_e_sempre_o_escolhido():
    so_um = [lst(ItemAlvo.BROCHE, 188, linha=0), lst(ItemAlvo.ADAGA, 300, linha=1)]
    for _ in range(20):
        assert escolher(so_um, cfg(broche=188, adaga=199), sorteio()).item is ItemAlvo.BROCHE

def test_com_semente_fixa_a_escolha_e_deterministica():
    candidatos = [lst(ItemAlvo.BROCHE, 188, linha=0),
                  lst(ItemAlvo.ADAGA, 199, linha=1),
                  lst(ItemAlvo.REDE, 260, linha=2)]
    config = cfg(broche=188, adaga=199, rede=260)
    primeira = escolher(candidatos, config, random.Random(7)).item
    for _ in range(5):
        assert escolher(candidatos, config, random.Random(7)).item is primeira

def test_o_sorteio_alcanca_todos_os_candidatos():
    # Pega a implementacao que diz sortear e devolve sempre o mesmo — foi
    # exatamente o vies que motivou esta mudanca.
    candidatos = [lst(ItemAlvo.BROCHE, 188, linha=0),
                  lst(ItemAlvo.ADAGA, 199, linha=1),
                  lst(ItemAlvo.REDE, 260, linha=2)]
    config = cfg(broche=188, adaga=199, rede=260)
    rng = random.Random(20260813)
    vistos = {escolher(candidatos, config, rng).item for _ in range(200)}
    assert vistos == {ItemAlvo.BROCHE, ItemAlvo.ADAGA, ItemAlvo.REDE}

def test_o_sorteio_nao_privilegia_a_ordem_de_leitura():
    # Com 2 candidatos e 400 sorteios, uma implementacao que devolvesse o
    # primeiro daria 400 para ele. Exigimos que nenhum passe de 70%.
    candidatos = [lst(ItemAlvo.BROCHE, 188, linha=0),
                  lst(ItemAlvo.REDE, 260, linha=5)]
    config = cfg(broche=188, rede=260)
    rng = random.Random(20260813)
    contagem = {ItemAlvo.BROCHE: 0, ItemAlvo.REDE: 0}
    for _ in range(400):
        contagem[escolher(candidatos, config, rng).item] += 1
    assert max(contagem.values()) < 280, contagem

def test_config_nao_tem_mais_fracao_de_sanidade():
    # A regra de igualdade exata ja rejeita tudo abaixo do corte, entao a
    # fracao virou config inalcancavel — e config que parece protecao e nao
    # protege e pior que config nenhuma.
    assert not hasattr(cfg(broche=188), "fracao_sanidade")
