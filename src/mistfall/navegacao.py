"""Navegacao confirmada entre as abas Comprar e Vender."""

import time
from dataclasses import dataclass
from typing import Callable, TypeAlias

import numpy as np

from mistfall.compra_visao import filtro_roxo_ativo
from mistfall.estado import identificar_estado
from mistfall.geometria import CATEGORIA_MATERIAL_CONSTRUCAO
from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.tipos import BAU_INICIAL, EstadoTela
from mistfall.venda import RitmoVenda
from mistfall.venda_visao import (
    CENTRO_ABA_ARMAZEM,
    PainelItens,
    centro_bau,
    eh_tela_venda,
    ler_bau_selecionado,
    ler_painel_itens,
)


CENTRO_ABA_COMPRAR = (150, 140)
CENTRO_ABA_VENDER = (300, 140)
CENTRO_CATEGORIA_MATERIAL_CONSTRUCAO = CATEGORIA_MATERIAL_CONSTRUCAO
CENTRO_FILTRO_ROXO = (800, 230)

# A spec manda: "falhas transitorias geram nova tentativa; falhas persistentes
# encerram o modo completo com diagnostico". O jogo perde cliques de aba e de
# filtro; sem re-clicar, todo clique perdido virava falha persistente e
# derrubava a sessao inteira com ABORTOU.
TENTATIVAS_DE_CLIQUE = 3

Frame: TypeAlias = np.ndarray
PredicadoFrame: TypeAlias = Callable[[Frame], bool]


@dataclass(frozen=True)
class ResultadoNavegacao:
    sucesso: bool
    frame: np.ndarray | None
    motivo: str


def _esperar(
    tela: Tela,
    ritmo: RitmoVenda,
    predicado: PredicadoFrame,
) -> tuple[Frame | None, Frame | None]:
    inicio = time.monotonic()
    primeiro = True
    ultimo = None
    while primeiro or time.monotonic() - inicio < ritmo.teto_espera_fechamento:
        primeiro = False
        ultimo = tela.capturar()
        if predicado(ultimo):
            return ultimo, ultimo
        time.sleep(ritmo.intervalo_entre_perguntas)
    return None, ultimo


def _aguardar(
    tela: Tela,
    ritmo: RitmoVenda,
    predicado: PredicadoFrame,
    motivo: str,
) -> ResultadoNavegacao:
    frame, ultimo = _esperar(tela, ritmo, predicado)
    if frame is None:
        return ResultadoNavegacao(False, ultimo, motivo)
    return ResultadoNavegacao(True, frame, "")


def _clicar_ate_confirmar(
    tela: Tela,
    mao: Mao,
    ritmo: RitmoVenda,
    alvo: tuple[int, int],
    predicado: PredicadoFrame,
    motivo: str,
) -> ResultadoNavegacao:
    """Clica e espera a confirmacao, re-clicando ate `TENTATIVAS_DE_CLIQUE`.

    Esgotadas as tentativas, devolve a ultima falha — com o motivo — em vez de
    tentar para sempre: falha persistente continua encerrando o modo completo
    com diagnostico.
    """
    resultado = ResultadoNavegacao(False, None, motivo)
    for _ in range(TENTATIVAS_DE_CLIQUE):
        mao.clicar(*alvo)
        resultado = _aguardar(tela, ritmo, predicado, motivo)
        if resultado.sucesso:
            return resultado
    return resultado


def ir_para_venda(tela: Tela, mao: Mao, ritmo: RitmoVenda) -> ResultadoNavegacao:
    inventario = _clicar_ate_confirmar(
        tela,
        mao,
        ritmo,
        CENTRO_ABA_VENDER,
        lambda frame: eh_tela_venda(frame)
        and ler_painel_itens(frame) is PainelItens.INVENTARIO,
        "Venda nao confirmou Inventario",
    )
    if not inventario.sucesso:
        return inventario

    armazem = _clicar_ate_confirmar(
        tela,
        mao,
        ritmo,
        CENTRO_ABA_ARMAZEM,
        lambda frame: eh_tela_venda(frame)
        and ler_painel_itens(frame) is PainelItens.ARMAZEM,
        "Venda nao confirmou Armazem",
    )
    if not armazem.sucesso:
        return armazem

    return _clicar_ate_confirmar(
        tela,
        mao,
        ritmo,
        centro_bau(BAU_INICIAL),
        lambda frame: eh_tela_venda(frame)
        and ler_painel_itens(frame) is PainelItens.ARMAZEM
        and ler_bau_selecionado(frame) == BAU_INICIAL,
        "Venda nao confirmou Bau 2",
    )


def garantir_filtro_roxo(tela: Tela, mao: Mao, ritmo: RitmoVenda) -> ResultadoNavegacao:
    # A Categoria e ASSUMIDA, nao validada: nao existe detector de Categoria
    # hoje, e `identificar_estado` so distingue LISTA de Janela de Confirmacao
    # e de outra Categoria pelo brilho do menu. Por isso os motivos abaixo
    # dizem "nao confirmou LISTA", que e o que de fato foi verificado, e nao
    # "nao confirmou Material de Construcao", que seria diagnostico
    # mentiroso — um clique de Categoria perdido passa por aqui sem alarme.
    compra = _aguardar(
        tela,
        ritmo,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA,
        "tela de Compra nao confirmou LISTA",
    )
    if not compra.sucesso:
        return compra
    assert compra.frame is not None
    if filtro_roxo_ativo(compra.frame):
        return compra

    return _clicar_ate_confirmar(
        tela,
        mao,
        ritmo,
        CENTRO_FILTRO_ROXO,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA
        and filtro_roxo_ativo(frame),
        "Compra nao confirmou filtro roxo",
    )


def ir_para_compra(tela: Tela, mao: Mao, ritmo: RitmoVenda) -> ResultadoNavegacao:
    compra = _clicar_ate_confirmar(
        tela,
        mao,
        ritmo,
        CENTRO_ABA_COMPRAR,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA,
        "Compra nao confirmou aba Comprar",
    )
    if not compra.sucesso:
        return compra

    # Mesma limitacao de `garantir_filtro_roxo`: o predicado so sabe dizer que
    # a tela e LISTA, entao um clique de Categoria perdido passa daqui sem ser
    # notado. O motivo diz o que foi verificado, e nada alem disso.
    material = _clicar_ate_confirmar(
        tela,
        mao,
        ritmo,
        CENTRO_CATEGORIA_MATERIAL_CONSTRUCAO,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA,
        "tela de Compra nao confirmou LISTA depois da Categoria",
    )
    if not material.sucesso:
        return material
    return garantir_filtro_roxo(tela, mao, ritmo)
