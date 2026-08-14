import dataclasses
import numpy as np
from mistfall.geometria import TODOS_OS_SLOTS, regiao_icone, recorte_preco
from mistfall.itens import identificar_item
from mistfall.precos import ler_precos
from mistfall.tipos import Listagem

def varrer_bruto(img: np.ndarray) -> list[Listagem]:
    """Le os doze slots como estao, sem conferir nada entre eles.

    Existe separada de `varrer` para o corpus de regressao poder documentar o
    que o OCR entrega de fato. Quem decide Compra usa `varrer`.

    Os doze precos saem de UMA chamada ao tesseract, com os recortes empilhados
    numa folha — nao ha `trabalhadores` aqui porque nao ha o que paralelizar.
    O helper de paralelismo continua no projeto e continua servindo as tres
    leituras da Janela de Confirmacao; `config.trabalhadores` alimenta aquele
    caminho, nao este.
    """
    icones = [regiao_icone(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    precos = [recorte_preco(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    itens = [identificar_item(icone) for icone in icones]
    lidos = ler_precos(precos)
    return [
        Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)
        for (linha, coluna), item, preco in zip(TODOS_OS_SLOTS, itens, lidos)
    ]

def conferir_ordenacao(listagens: list[Listagem]) -> list[Listagem]:
    """Invalida o Preco-unitario de todo slot que contraria a ordenacao.

    O Leilao lista por Preco-unitario crescente em ordem de leitura. Isso foi
    verificado slot a slot: a verdade humana dos 7 prints do corpus e
    nao-decrescente em 84 de 84 slots.

    Regra: olhando so os precos nao-None, um preco e confiavel se for >= todos
    os anteriores e <= todos os posteriores. Quem violar vira None, e `decisao`
    ja ignora None — entao nao compra.

    Isto pega justamente a falha que a fracao de sanidade nao pega: ela so
    detecta queda de ordem de grandeza, e a janela perigosa e a troca de um
    digito. Tambem pega o numero truncado, que sai sempre menor e por isso
    quebra a ordenacao.

    A regra e deliberadamente contagiosa: um preco errado invalida tambem os
    vizinhos com que ele conflita — em images/lanterna-dragao-orbe-rede.png um
    unico 293 espurio derruba 9 dos 12 slots. Isso e o trade certo aqui: o
    custo de descartar uma tela e um Reset, e o custo de comprar caro e ouro.
    """
    precos = [listagem.preco_unitario for listagem in listagens]
    conferidas = []
    for posicao, listagem in enumerate(listagens):
        preco = listagem.preco_unitario
        anteriores = [p for p in precos[:posicao] if p is not None]
        posteriores = [p for p in precos[posicao + 1 :] if p is not None]
        confiavel = (
            preco is not None
            and all(preco >= anterior for anterior in anteriores)
            and all(preco <= posterior for posterior in posteriores)
        )
        conferidas.append(
            listagem if confiavel else dataclasses.replace(listagem, preco_unitario=None)
        )
    return conferidas

def varrer(img: np.ndarray) -> list[Listagem]:
    """Imagem do Leilao -> doze Listagens ja conferidas contra a ordenacao."""
    return conferir_ordenacao(varrer_bruto(img))
