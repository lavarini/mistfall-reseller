"""Política pura do fluxo coordenado de Compra e Venda.

Este módulo não captura telas, clica nem dorme. Ele apenas transforma eventos
observados em um novo estado e na próxima ação estratégica.
"""

from dataclasses import dataclass, replace
from enum import Enum


class ModoFluxo(Enum):
    RAPIDO = "rapido"
    LENTO = "lento"


class _TipoEvento(Enum):
    INTENCAO_DETECTADA = "intencao_detectada"
    COMPRA_ENVIADA = "compra_enviada"
    COMPRA_CONFIRMADA = "compra_confirmada"
    COMPRA_INCONCLUSIVA = "compra_inconclusiva"
    RESET_EXECUTADO = "reset_executado"
    MENSAGEM_INVENTARIO_CHEIO = "mensagem_inventario_cheio"
    UNIDADES_LISTADAS = "unidades_listadas"
    CAPACIDADE_ATUALIZADA = "capacidade_atualizada"
    RETORNO_COMPRA = "retorno_compra"


@dataclass(frozen=True)
class EventoFluxo:
    """Evento já observado por uma camada de execução.

    As constantes cobrem eventos sem dados; as fábricas permitem transportar
    unidades e capacidade sem tornar o estado mutável.
    """

    tipo: _TipoEvento
    unidades: int = 0
    capacidade: tuple[int, int] | None = None

    @classmethod
    def intencao_detectada(cls) -> "EventoFluxo":
        return cls(_TipoEvento.INTENCAO_DETECTADA)

    @classmethod
    def compra_enviada(cls) -> "EventoFluxo":
        return cls(_TipoEvento.COMPRA_ENVIADA)

    @classmethod
    def compra_confirmada(cls, unidades: int = 1) -> "EventoFluxo":
        return cls(_TipoEvento.COMPRA_CONFIRMADA, unidades=unidades)

    @classmethod
    def compra_inconclusiva(cls, unidades: int = 1) -> "EventoFluxo":
        return cls(_TipoEvento.COMPRA_INCONCLUSIVA, unidades=unidades)

    @classmethod
    def reset_executado(cls) -> "EventoFluxo":
        return cls(_TipoEvento.RESET_EXECUTADO)

    @classmethod
    def unidades_listadas(cls, unidades: int) -> "EventoFluxo":
        return cls(_TipoEvento.UNIDADES_LISTADAS, unidades=unidades)

    @classmethod
    def capacidade_atualizada(cls, ocupadas: int, limite: int) -> "EventoFluxo":
        return cls(
            _TipoEvento.CAPACIDADE_ATUALIZADA,
            capacidade=(ocupadas, limite),
        )


EventoFluxo.INTENCAO = EventoFluxo.intencao_detectada()
EventoFluxo.INTENCAO_DETECTADA = EventoFluxo.intencao_detectada()
EventoFluxo.COMPRA_ENVIADA = EventoFluxo.compra_enviada()
EventoFluxo.COMPRA_CONFIRMADA = EventoFluxo.compra_confirmada()
EventoFluxo.COMPRA_INCONCLUSIVA = EventoFluxo.compra_inconclusiva()
EventoFluxo.RESET = EventoFluxo.reset_executado()
EventoFluxo.RESET_EXECUTADO = EventoFluxo.reset_executado()
EventoFluxo.MENSAGEM_INVENTARIO_CHEIO = EventoFluxo(
    _TipoEvento.MENSAGEM_INVENTARIO_CHEIO
)


class AcaoFluxo(Enum):
    CONTINUAR_COMPRA = "continuar_compra"
    EXECUTAR_COMPRA = "executar_compra"
    EXECUTAR_RESET = "executar_reset"
    VENDER_POR_INVENTARIO_CHEIO = "vender_por_inventario_cheio"
    VENDER_POR_FLUXO_LENTO = "vender_por_fluxo_lento"
    CONTINUAR_VENDA = "continuar_venda"
    ENCERRAR = "encerrar"


@dataclass(frozen=True)
class EstadoFluxo:
    estoque_estimado: int = 0
    intencoes_desde_reset: int = 0
    resets_desde_intencao: int = 0
    intervalos_lentos_consecutivos: int = 0
    resets_consecutivos: int = 0
    modo: ModoFluxo = ModoFluxo.RAPIDO
    compra_pendente: bool = False
    capacidade_observada: tuple[int, int] | None = None


def estado_inicial(
    *,
    estoque_estimado: int = 0,
    modo: ModoFluxo = ModoFluxo.RAPIDO,
) -> EstadoFluxo:
    return EstadoFluxo(estoque_estimado=estoque_estimado, modo=modo)


def _acao_por_saldo(estado: EstadoFluxo) -> AcaoFluxo:
    if estado.modo is ModoFluxo.LENTO and estado.estoque_estimado >= 45:
        return AcaoFluxo.VENDER_POR_FLUXO_LENTO
    return AcaoFluxo.CONTINUAR_COMPRA


def aplicar_evento(
    estado: EstadoFluxo, evento: EventoFluxo
) -> tuple[EstadoFluxo, AcaoFluxo]:
    """Aplica um evento sem modificar ``estado`` e retorna estado/ação novos."""

    tipo = evento.tipo
    if tipo is _TipoEvento.INTENCAO_DETECTADA:
        intervalos = estado.intervalos_lentos_consecutivos
        if estado.resets_desde_intencao >= 3:
            intervalos += 1
        modo = (
            ModoFluxo.LENTO
            if intervalos >= 3 or estado.resets_consecutivos >= 5
            else estado.modo
        )
        novo = replace(
            estado,
            intencoes_desde_reset=estado.intencoes_desde_reset + 1,
            resets_desde_intencao=0,
            intervalos_lentos_consecutivos=intervalos,
            resets_consecutivos=0,
            modo=modo,
        )
        return novo, AcaoFluxo.EXECUTAR_COMPRA

    if tipo is _TipoEvento.RESET_EXECUTADO:
        consecutivos = estado.resets_consecutivos + 1
        modo = ModoFluxo.LENTO if consecutivos >= 5 else estado.modo
        novo = replace(
            estado,
            resets_desde_intencao=estado.resets_desde_intencao + 1,
            resets_consecutivos=consecutivos,
            modo=modo,
        )
        return novo, AcaoFluxo.CONTINUAR_COMPRA

    if tipo is _TipoEvento.COMPRA_ENVIADA:
        return replace(estado, compra_pendente=True), AcaoFluxo.CONTINUAR_COMPRA

    if tipo in (_TipoEvento.COMPRA_CONFIRMADA, _TipoEvento.COMPRA_INCONCLUSIVA):
        unidades = evento.unidades or 1
        novo = replace(
            estado,
            estoque_estimado=estado.estoque_estimado + unidades,
            compra_pendente=False,
        )
        return novo, _acao_por_saldo(novo)

    if tipo is _TipoEvento.MENSAGEM_INVENTARIO_CHEIO:
        novo = replace(estado, compra_pendente=False)
        return novo, AcaoFluxo.VENDER_POR_INVENTARIO_CHEIO

    if tipo is _TipoEvento.UNIDADES_LISTADAS:
        if evento.unidades < 0:
            raise ValueError("unidades listadas não podem ser negativas")
        novo = replace(
            estado,
            estoque_estimado=estado.estoque_estimado - evento.unidades,
        )
        return novo, AcaoFluxo.CONTINUAR_VENDA

    if tipo is _TipoEvento.CAPACIDADE_ATUALIZADA:
        return (
            replace(estado, capacidade_observada=evento.capacidade),
            AcaoFluxo.CONTINUAR_VENDA,
        )

    return estado, AcaoFluxo.CONTINUAR_COMPRA
