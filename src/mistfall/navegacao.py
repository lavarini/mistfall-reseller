"""Navegacao confirmada entre as abas Comprar e Vender."""

import time
from dataclasses import dataclass
from typing import Callable, TypeAlias

import numpy as np

from mistfall.compra_visao import filtro_roxo_ativo
from mistfall.estado import identificar_estado
from mistfall.geometria import CATEGORIA_MATERIAL_CONSTRUCAO
from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.tipos import Bau, EstadoTela
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


def ir_para_venda(tela: Tela, mao: Mao, ritmo: RitmoVenda) -> ResultadoNavegacao:
    mao.clicar(*CENTRO_ABA_VENDER)
    inventario = _aguardar(
        tela,
        ritmo,
        lambda frame: eh_tela_venda(frame)
        and ler_painel_itens(frame) is PainelItens.INVENTARIO,
        "Venda nao confirmou Inventario",
    )
    if not inventario.sucesso:
        return inventario

    mao.clicar(*CENTRO_ABA_ARMAZEM)
    armazem = _aguardar(
        tela,
        ritmo,
        lambda frame: eh_tela_venda(frame)
        and ler_painel_itens(frame) is PainelItens.ARMAZEM,
        "Venda nao confirmou Armazem",
    )
    if not armazem.sucesso:
        return armazem

    mao.clicar(*centro_bau(Bau.SEGUNDO))
    return _aguardar(
        tela,
        ritmo,
        lambda frame: eh_tela_venda(frame)
        and ler_painel_itens(frame) is PainelItens.ARMAZEM
        and ler_bau_selecionado(frame) is Bau.SEGUNDO,
        "Venda nao confirmou Bau 2",
    )


def garantir_filtro_roxo(tela: Tela, mao: Mao, ritmo: RitmoVenda) -> ResultadoNavegacao:
    compra = _aguardar(
        tela,
        ritmo,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA,
        "Compra nao confirmou Material de Construcao",
    )
    if not compra.sucesso:
        return compra
    assert compra.frame is not None
    if filtro_roxo_ativo(compra.frame):
        return compra

    mao.clicar(*CENTRO_FILTRO_ROXO)
    return _aguardar(
        tela,
        ritmo,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA
        and filtro_roxo_ativo(frame),
        "Compra nao confirmou filtro roxo",
    )


def ir_para_compra(tela: Tela, mao: Mao, ritmo: RitmoVenda) -> ResultadoNavegacao:
    mao.clicar(*CENTRO_ABA_COMPRAR)
    compra = _aguardar(
        tela,
        ritmo,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA,
        "Compra nao confirmou aba Comprar",
    )
    if not compra.sucesso:
        return compra

    mao.clicar(*CENTRO_CATEGORIA_MATERIAL_CONSTRUCAO)
    material = _aguardar(
        tela,
        ritmo,
        lambda frame: identificar_estado(frame) is EstadoTela.LISTA,
        "Compra nao confirmou Material de Construcao",
    )
    if not material.sucesso:
        return material
    return garantir_filtro_roxo(tela, mao, ritmo)
