"""Visao pura da aba Vender com o Armazem aberto."""

import re
from enum import Enum

import cv2
import numpy as np
import pytesseract

from mistfall.geometria import conferir_resolucao
from mistfall.itens import identificar_item, pontuar
from mistfall.paralelo import TRABALHADORES_PADRAO, mapear
from mistfall.tipos import CapacidadeVenda, SlotArmazem


REGIAO_CAPACIDADE = (345, 200, 450, 250)
# As abas de Bau crescem para a direita a partir de um primeiro centro fixo. O
# numero delas muda entre seasons, entao a geometria e derivada do passo em vez
# de listada: `contar_baus` descobre quantas existem lendo a propria tela.
X_PRIMEIRO_BAU = 1723
PASSO_BAU = 64
Y_BAUS = 286
MEIA_CAIXA_BAU = 22
# Teto da varredura, nao promessa: e onde a faixa de abas esbarra na borda do
# painel do Armazem. A contagem para muito antes disso, na primeira ausente.
MAX_BAUS = 10
# Brilho medio da caixa da aba. Medido nas fixtures: 19 sem aba, 41 com aba nao
# selecionada, 115 com aba selecionada. O limiar fica no vale entre 19 e 41.
LIMIAR_PRESENCA_BAU = 30.0
CENTROS_BAUS = tuple(
    (X_PRIMEIRO_BAU + PASSO_BAU * i, Y_BAUS) for i in range(MAX_BAUS)
)
REGIOES_ABAS_ITENS = (
    (1570, 190, 1755, 240),  # Inventario
    (1770, 190, 1940, 240),  # Armazem
)
LIMIAR_DOURADO_ABA = 0.14
MARGEM_DOURADA_ABA = 0.03
CENTRO_ABA_ARMAZEM = (1845, 215)
CENTRO_ABA_INVENTARIO = (1650, 215)

SLOT_ESQUERDA = 1688
SLOT_TOPO = 333
SLOT_PASSO_X = 93.5
SLOT_PASSO_Y = 128
SLOT_LARGURA = 83
SLOT_ALTURA = 106
COLUNAS_ARMAZEM = 8
LINHAS_ARMAZEM = 7

LIMIAR_DOURADO = 0.50
MARGEM_DOURADA = 0.20

# Botao "Resgatar", ao lado de "Recuperavel:". So existe quando ha Ouro a
# recolher; sem nada a resgatar a regiao fica no fundo escuro do painel.
# Medido: 0.9485 de dourado com o botao contra 0.0163 sem ele.
REGIAO_BOTAO_RESGATAR = (1073, 205, 1472, 259)
CENTRO_BOTAO_RESGATAR = (1272, 232)
MATIZ_BOTAO_RESGATAR = (15, 40)
SATURACAO_MINIMA_BOTAO_RESGATAR = 90
VALOR_MINIMO_BOTAO_RESGATAR = 110
PROPORCAO_MINIMA_BOTAO_RESGATAR = 0.30
REGIAO_TITULO_JANELA_VENDA = (1000, 190, 1550, 300)
REGIAO_CENTRO_JANELA_VENDA = (400, 280, 2150, 1150)
_CONFIG_CAPACIDADE = "--psm 7 -c tessedit_char_whitelist=0123456789/"
_CONFIG_QUANTIDADE = "--psm 13 -c tessedit_char_whitelist=0123456789"
ESCALAS_SLOT = tuple(indice / 20 for indice in range(28, 41))
QUANTIDADE_REL = (50, 70, 83, 106)


class PainelItens(Enum):
    INVENTARIO = "inventario"
    ARMAZEM = "armazem"


def _recortar(img: np.ndarray, regiao: tuple[int, int, int, int]) -> np.ndarray:
    conferir_resolucao(img)
    x0, y0, x1, y1 = regiao
    return img[y0:y1, x0:x1]


def _ocr_capacidade(regiao: np.ndarray) -> str:
    cinza = cv2.cvtColor(regiao, cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(
        ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return pytesseract.image_to_string(binaria, config=_CONFIG_CAPACIDADE).strip()


def ler_capacidade(img: np.ndarray) -> CapacidadeVenda | None:
    texto = _ocr_capacidade(_recortar(img, REGIAO_CAPACIDADE))
    casamento = re.fullmatch(r"(\d+)/(\d+)", texto)
    if casamento is None:
        return None
    ocupadas, limite = map(int, casamento.groups())
    if limite <= 0 or not 0 <= ocupadas <= limite:
        return None
    return CapacidadeVenda(ocupadas=ocupadas, limite=limite)


def _proporcoes_douradas(img: np.ndarray) -> list[float]:
    conferir_resolucao(img)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    proporcoes = []
    for x, y in CENTROS_BAUS:
        recorte = hsv[
            y - MEIA_CAIXA_BAU:y + MEIA_CAIXA_BAU,
            x - MEIA_CAIXA_BAU:x + MEIA_CAIXA_BAU,
        ]
        dourado = (
            (recorte[:, :, 0] >= 10)
            & (recorte[:, :, 0] <= 35)
            & (recorte[:, :, 1] >= 80)
            & (recorte[:, :, 2] >= 80)
        )
        proporcoes.append(float(dourado.mean()))
    return proporcoes


def botao_resgatar_ativo(img: np.ndarray) -> bool:
    """Diz se ha Ouro recuperavel, pelo botao "Resgatar" estar dourado.

    A regiao fica na coluna da esquerda, fora do painel de itens, entao a
    leitura nao depende de Inventario ou Armazem estar aberto.
    """
    conferir_resolucao(img)
    hsv = cv2.cvtColor(_recortar(img, REGIAO_BOTAO_RESGATAR), cv2.COLOR_BGR2HSV)
    dourado = (
        (hsv[:, :, 0] >= MATIZ_BOTAO_RESGATAR[0])
        & (hsv[:, :, 0] <= MATIZ_BOTAO_RESGATAR[1])
        & (hsv[:, :, 1] >= SATURACAO_MINIMA_BOTAO_RESGATAR)
        & (hsv[:, :, 2] >= VALOR_MINIMO_BOTAO_RESGATAR)
    )
    return float(dourado.mean()) >= PROPORCAO_MINIMA_BOTAO_RESGATAR


def contar_baus(img: np.ndarray) -> int:
    """Conta as abas de Bau presentes, da esquerda para a direita.

    A varredura para na primeira posicao vazia em vez de contar todas as
    posicoes acesas: um brilho solto a direita da faixa nao vira Bau fantasma.
    """
    conferir_resolucao(img)
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    total = 0
    for x, y in CENTROS_BAUS:
        caixa = cinza[
            y - MEIA_CAIXA_BAU:y + MEIA_CAIXA_BAU,
            x - MEIA_CAIXA_BAU:x + MEIA_CAIXA_BAU,
        ]
        if caixa.size == 0 or caixa.mean() < LIMIAR_PRESENCA_BAU:
            break
        total += 1
    return total


def ler_bau_selecionado(img: np.ndarray) -> int | None:
    proporcoes = _proporcoes_douradas(img)
    ordem = sorted(range(len(proporcoes)), key=proporcoes.__getitem__, reverse=True)
    melhor, segundo = ordem[:2]
    if (
        proporcoes[melhor] < LIMIAR_DOURADO
        or proporcoes[melhor] - proporcoes[segundo] < MARGEM_DOURADA
    ):
        return None
    return melhor


def _proporcoes_douradas_abas(img: np.ndarray) -> list[float]:
    conferir_resolucao(img)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    resultado = []
    for x0, y0, x1, y1 in REGIOES_ABAS_ITENS:
        recorte = hsv[y0:y1, x0:x1]
        dourado = (
            (recorte[:, :, 0] >= 10)
            & (recorte[:, :, 0] <= 35)
            & (recorte[:, :, 1] >= 50)
            & (recorte[:, :, 2] >= 80)
        )
        resultado.append(float(dourado.mean()))
    return resultado


def ler_painel_itens(img: np.ndarray) -> PainelItens | None:
    proporcoes = _proporcoes_douradas_abas(img)
    melhor = max(range(2), key=proporcoes.__getitem__)
    outro = 1 - melhor
    if (
        proporcoes[melhor] < LIMIAR_DOURADO_ABA
        or proporcoes[melhor] - proporcoes[outro] < MARGEM_DOURADA_ABA
    ):
        return None
    return PainelItens.INVENTARIO if melhor == 0 else PainelItens.ARMAZEM


def centro_bau(bau: int) -> tuple[int, int]:
    return CENTROS_BAUS[bau]


def caixa_slot_armazem(linha: int, coluna: int) -> tuple[int, int, int, int]:
    if not 0 <= linha < LINHAS_ARMAZEM or not 0 <= coluna < COLUNAS_ARMAZEM:
        raise ValueError(f"slot do Armazem fora da grade: ({linha}, {coluna})")
    x0 = int(SLOT_ESQUERDA + SLOT_PASSO_X * coluna)
    y0 = SLOT_TOPO + SLOT_PASSO_Y * linha
    return x0, y0, x0 + SLOT_LARGURA, y0 + SLOT_ALTURA


def _recortar_slot(img: np.ndarray, linha: int, coluna: int) -> np.ndarray:
    return _recortar(img, caixa_slot_armazem(linha, coluna))


def _identificar_item_do_slot(slot: np.ndarray):
    candidatos = []
    for escala in ESCALAS_SLOT:
        ampliado = cv2.resize(
            slot, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC
        )
        scores = pontuar(ampliado)
        candidatos.append((max(scores.values()), ampliado))
    _, melhor_regiao = max(candidatos, key=lambda candidato: candidato[0])
    return identificar_item(melhor_regiao)


def _ler_quantidade(slot: np.ndarray) -> int | None:
    x0, y0, x1, y1 = QUANTIDADE_REL
    recorte = slot[y0:y1, x0:x1]
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(
        ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    texto = pytesseract.image_to_string(binaria, config=_CONFIG_QUANTIDADE).strip()
    return int(texto) if texto.isdigit() else None


def _ler_slot(tarefa):
    linha, coluna, regiao = tarefa
    item = _identificar_item_do_slot(regiao)
    quantidade = _ler_quantidade(regiao) if item is not None else None
    return SlotArmazem(linha, coluna, item, quantidade)


def varrer_armazem(img: np.ndarray) -> list[SlotArmazem]:
    conferir_resolucao(img)
    tarefas = [
        (linha, coluna, _recortar_slot(img, linha, coluna))
        for linha in range(LINHAS_ARMAZEM)
        for coluna in range(COLUNAS_ARMAZEM)
    ]
    return mapear(_ler_slot, tarefas, TRABALHADORES_PADRAO)


def escolher_slot_de_venda(slots: list[SlotArmazem]) -> SlotArmazem | None:
    return next(
        (slot for slot in slots if slot.item is not None and slot.quantidade == 3),
        None,
    )


def centro_slot_armazem(slot: SlotArmazem) -> tuple[int, int]:
    x0, y0, x1, y1 = caixa_slot_armazem(slot.linha, slot.coluna)
    return (x0 + x1) // 2, (y0 + y1) // 2


def eh_tela_venda(img: np.ndarray) -> bool:
    return ler_capacidade(img) is not None and ler_bau_selecionado(img) is not None


def eh_janela_venda(img: np.ndarray) -> bool:
    titulo = _recortar(img, REGIAO_TITULO_JANELA_VENDA)
    centro = _recortar(img, REGIAO_CENTRO_JANELA_VENDA)
    brilho_titulo = float(cv2.cvtColor(titulo, cv2.COLOR_BGR2GRAY).mean())
    brilho_centro = float(cv2.cvtColor(centro, cv2.COLOR_BGR2GRAY).mean())
    return brilho_titulo >= 25.0 and brilho_centro <= 12.0
