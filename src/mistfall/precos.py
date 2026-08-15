import time

import cv2
import numpy as np
import pytesseract

_CONFIG_UM = "--psm 7 -c tessedit_char_whitelist=0123456789"
_CONFIG_FOLHA = "--psm 6 -c tessedit_char_whitelist=0123456789"

# Altura da faixa preta entre dois recortes na folha. Medido contra o corpus:
# 30 a 60 px acertam 84 de 84. Fora disso piora nos dois sentidos — 5 px cola
# digito de slots vizinhos (82/84), 120 px faz o --psm 6 parar de ver um bloco
# unico e tratar os pedacos como regioes separadas (69/84), que e justamente o
# contexto entre linhas que faz a folha ler melhor que os recortes isolados.
# 40 e o centro do plato: erra por 10 px para qualquer lado sem mudar nada.
SEPARADOR = 40


def _preparar(recorte: np.ndarray) -> np.ndarray:
    """Cinza, ampliacao 4x e Otsu — o preparo que as duas leituras dividem."""
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(
        ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binaria


def ler_preco(recorte: np.ndarray) -> int | None:
    """Le um recorte sozinho, com --psm 7.

    Nao tem chamador em producao. Era `varrer_bruto`, que passou a usar
    `ler_precos`. A Janela de Confirmacao nunca usou esta funcao: `janela.py`
    tem o proprio `_numero`, com preparo diferente. Fica como contraparte de um
    recorte so, util na bancada e nos testes — a #20 decide se sai junto com o
    helper de paralelismo."""
    texto = pytesseract.image_to_string(_preparar(recorte), config=_CONFIG_UM).strip()
    return int(texto) if texto.isdigit() else None


def ler_precos(
    recortes: list[np.ndarray], tempos: dict[str, float] | None = None
) -> list[int | None]:
    """Le varios recortes numa chamada so, empilhados numa folha.

    O pytesseract nao faz OCR em Python: grava a imagem num arquivo temporario
    e executa o binario do tesseract. Doze recortes eram doze execucoes, e na
    maquina do jogo isso custava 5729 ms contra 477 ms no Mac — criar processo
    no Windows e caro. Uma chamada paga esse custo uma vez.

    E le melhor, nao so mais rapido: com --psm 7 cada recorte e julgado como
    linha solta, sem contexto. Empilhados, o --psm 6 compara altura de digito,
    alinhamento e espessura entre as linhas. E a mesma informacao que faz um
    humano ler 241 onde um digito isolado pareceria 24. No corpus sobe de 79
    para 84 acertos em 84 slots.

    A correspondencia volta por POSICAO, nunca pela ordem em que os numeros
    saem: um recorte ilegivel produziria onze numeros em vez de doze e
    deslocaria a correspondencia inteira — o slot 6 receberia o preco do 7, e
    um erro num slot viraria erro em todos. Como sabemos em que faixa vertical
    cada recorte foi empilhado, cada numero volta ao seu indice pela caixa que
    o image_to_data devolve, e recorte ilegivel vira None no lugar certo.
    """
    if not recortes:
        if tempos is not None:
            tempos["preparo_folha"] = 0.0
            tempos["tesseract_precos"] = 0.0
        return []

    inicio = time.monotonic()
    pilha = [_preparar(recorte) for recorte in recortes]
    pecas: list[np.ndarray] = []
    faixas: list[tuple[int, int]] = []
    topo = 0
    for preparado in pilha:
        pecas.append(preparado)
        faixas.append((topo, topo + preparado.shape[0]))
        topo += preparado.shape[0]
        pecas.append(np.zeros((SEPARADOR, preparado.shape[1]), dtype=np.uint8))
        topo += SEPARADOR

    folha = np.vstack(pecas)
    if tempos is not None:
        tempos["preparo_folha"] = (time.monotonic() - inicio) * 1000

    inicio = time.monotonic()
    dados = pytesseract.image_to_data(
        folha, config=_CONFIG_FOLHA,
        output_type=pytesseract.Output.DICT,
    )
    if tempos is not None:
        tempos["tesseract_precos"] = (time.monotonic() - inicio) * 1000

    # Duas passadas: primeiro junta os numeros de cada faixa, depois decide.
    # Faixa com mais de um numero e leitura duvidosa, nao um preco com um
    # vizinho: significa que o tesseract partiu o preco (241 virando "24" e
    # "1") ou colou lixo ao lado. Ficar com o primeiro devolveria 24 onde o
    # preco e 241 — um preco MENOR que o verdadeiro, e preco menor aqui e
    # leitura errada, nao pechincha. O --psm 7 antigo devolvia None nesse
    # caso, porque conferia isdigit() na linha inteira; manter esse None e
    # nao perder a rede que ele era.
    por_faixa: list[list[int]] = [[] for _ in recortes]
    for texto, y, altura in zip(dados["text"], dados["top"], dados["height"]):
        texto = texto.strip()
        if not texto.isdigit():
            continue
        centro = y + altura / 2
        for indice, (inicio, fim) in enumerate(faixas):
            if inicio <= centro < fim:
                por_faixa[indice].append(int(texto))
                break
    return [numeros[0] if len(numeros) == 1 else None for numeros in por_faixa]
