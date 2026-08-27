"""Política pura do fluxo coordenado de Compra e Venda.

Este módulo não captura telas, clica nem dorme. Ele apenas transforma eventos
observados em um novo estado e na próxima ação estratégica.
"""

from dataclasses import dataclass, replace
from enum import Enum

from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES


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
    ESTOQUE_RECONCILIADO = "estoque_reconciliado"
    OURO_ABAIXO_DO_PISO = "ouro_abaixo_do_piso"
    VENDA_ENCERRADA = "venda_encerrada"
    JANELA_DE_VENDA_ABERTA = "janela_de_venda_aberta"


@dataclass(frozen=True)
class EventoFluxo:
    """Evento já observado por uma camada de execução.

    As constantes cobrem eventos sem dados; as fábricas permitem transportar
    unidades e capacidade sem tornar o estado mutável.
    """

    tipo: _TipoEvento
    unidades: int = 0
    capacidade: tuple[int, int] | None = None
    resta_lote_cheio: bool = False

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

    @classmethod
    def ouro_abaixo_do_piso(cls) -> "EventoFluxo":
        """O Ouro caiu abaixo do piso que permite comprar.

        O numero do piso vive na configuracao e a comparacao e do coordenador:
        a politica continua pura e sem conhecer precos.
        """
        return cls(_TipoEvento.OURO_ABAIXO_DO_PISO)

    @classmethod
    def venda_encerrada(cls, resta_lote_cheio: bool) -> "EventoFluxo":
        """Uma Venda acabou, e disse se sobrou lote cheio no Armazem.

        Quem responde e a propria Venda, que le o Armazem: a resposta e
        independente do Estoque estimado, que subconta.
        """
        return cls(
            _TipoEvento.VENDA_ENCERRADA, resta_lote_cheio=resta_lote_cheio
        )

    @classmethod
    def janela_de_venda_aberta(cls) -> "EventoFluxo":
        """A Janela venceu e o regime lento pode voltar a vender.

        O intervalo vive na configuracao e o relogio e do coordenador: a
        politica continua pura, como no piso de Ouro.
        """
        return cls(_TipoEvento.JANELA_DE_VENDA_ABERTA)

    @classmethod
    def retorno_compra(cls) -> "EventoFluxo":
        return cls(_TipoEvento.RETORNO_COMPRA)

    @classmethod
    def estoque_reconciliado(cls, unidades: int) -> "EventoFluxo":
        if unidades < 0:
            raise ValueError("estoque reconciliado não pode ser negativo")
        return cls(_TipoEvento.ESTOQUE_RECONCILIADO, unidades=unidades)


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
EventoFluxo.OURO_ABAIXO_DO_PISO = EventoFluxo.ouro_abaixo_do_piso()
EventoFluxo.RETORNO_COMPRA = EventoFluxo.retorno_compra()
EventoFluxo.ESTOQUE_RECONCILIADO = EventoFluxo.estoque_reconciliado(0)
EventoFluxo.JANELA_DE_VENDA_ABERTA = EventoFluxo.janela_de_venda_aberta()


class AcaoFluxo(Enum):
    CONTINUAR_COMPRA = "continuar_compra"
    EXECUTAR_COMPRA = "executar_compra"
    VENDER_POR_INVENTARIO_CHEIO = "vender_por_inventario_cheio"
    VENDER_POR_FLUXO_LENTO = "vender_por_fluxo_lento"
    VENDER_POR_RETOMADA = "vender_por_retomada"
    VENDER_POR_OURO_BAIXO = "vender_por_ouro_baixo"
    CONTINUAR_VENDA = "continuar_venda"
    ENCERRAR = "encerrar"


@dataclass(frozen=True)
class EstadoFluxo:
    estoque_estimado: int = 0
    intencoes_desde_reset: int = 0
    resets_desde_intencao: int = 0
    intervalos_lentos_consecutivos: int = 0
    pontos_de_pressa: int = 0
    resets_consecutivos: int = 0
    modo: ModoFluxo = ModoFluxo.RAPIDO
    compra_pendente: bool = False
    capacidade_observada: tuple[int, int] | None = None
    # A ultima Venda saiu por Capacidade cheia deixando lote cheio para tras.
    # E o que distingue drenagem interrompida de fim de lote.
    retomada_pendente: bool = False


def estado_inicial(
    *,
    estoque_estimado: int = 0,
    modo: ModoFluxo = ModoFluxo.RAPIDO,
) -> EstadoFluxo:
    return EstadoFluxo(estoque_estimado=estoque_estimado, modo=modo)


def _acao_por_saldo(estado: EstadoFluxo) -> AcaoFluxo:
    if (
        estado.modo is ModoFluxo.LENTO
        and estado.estoque_estimado >= LOTE_DE_VENDA_EM_UNIDADES
    ):
        return AcaoFluxo.VENDER_POR_FLUXO_LENTO
    return AcaoFluxo.CONTINUAR_COMPRA


def aplicar_evento(
    estado: EstadoFluxo, evento: EventoFluxo
) -> tuple[EstadoFluxo, AcaoFluxo]:
    """Aplica um evento sem modificar ``estado`` e retorna estado/ação novos."""

    tipo = evento.tipo
    if tipo is _TipoEvento.INTENCAO_DETECTADA:
        intervalo = estado.resets_desde_intencao
        if intervalo >= 3:
            intervalos = estado.intervalos_lentos_consecutivos + 1
        else:
            intervalos = 0
        # O mesmo intervalo pontua no sentido contrario. Duas Intencoes coladas
        # (intervalo zero) valem os dois pontos sozinhas; um Reset entre elas
        # vale um, e sao precisos dois desses. Dois Resets nao dizem nada nem a
        # favor nem contra, entao nao somam e nao zeram.
        pontos = estado.pontos_de_pressa
        if intervalo == 0:
            pontos = min(pontos + 2, 2)
        elif intervalo == 1:
            pontos = min(pontos + 1, 2)
        elif intervalo >= 3:
            pontos = 0
        modo = (
            ModoFluxo.LENTO
            if intervalos >= 3 or estado.resets_consecutivos >= 5
            else estado.modo
        )
        if modo is ModoFluxo.LENTO and pontos >= 2:
            modo = ModoFluxo.RAPIDO
            pontos = 0
        transicionou_para_lento = (
            estado.modo is ModoFluxo.RAPIDO and modo is ModoFluxo.LENTO
        )
        novo = replace(
            estado,
            intencoes_desde_reset=estado.intencoes_desde_reset + 1,
            resets_desde_intencao=0,
            intervalos_lentos_consecutivos=intervalos,
            pontos_de_pressa=pontos,
            resets_consecutivos=0,
            modo=modo,
        )
        acao = (
            AcaoFluxo.VENDER_POR_FLUXO_LENTO
            if transicionou_para_lento
            else AcaoFluxo.EXECUTAR_COMPRA
        )
        return novo, acao

    if tipo is _TipoEvento.RESET_EXECUTADO:
        consecutivos = estado.resets_consecutivos + 1
        modo = ModoFluxo.LENTO if consecutivos >= 5 else estado.modo
        transicionou_para_lento = (
            estado.modo is ModoFluxo.RAPIDO and modo is ModoFluxo.LENTO
        )
        novo = replace(
            estado,
            intencoes_desde_reset=0,
            resets_desde_intencao=estado.resets_desde_intencao + 1,
            resets_consecutivos=consecutivos,
            modo=modo,
        )
        acao = (
            AcaoFluxo.VENDER_POR_FLUXO_LENTO
            if transicionou_para_lento
            else AcaoFluxo.CONTINUAR_COMPRA
        )
        return novo, acao

    if tipo is _TipoEvento.OURO_ABAIXO_DO_PISO:
        # Sinal, nao Compra nem Reset: nao pode contaminar a cadencia que
        # decide rapido/lento, entao o estado passa intacto.
        return estado, AcaoFluxo.VENDER_POR_OURO_BAIXO

    if tipo is _TipoEvento.COMPRA_ENVIADA:
        return replace(estado, compra_pendente=True), AcaoFluxo.CONTINUAR_COMPRA

    if tipo in (_TipoEvento.COMPRA_CONFIRMADA, _TipoEvento.COMPRA_INCONCLUSIVA):
        if not estado.compra_pendente:
            return estado, _acao_por_saldo(estado)
        # Nao usar `or 1`: em Python `0 or 1` e 1, e isso engolia o
        # `compra_inconclusiva(unidades=0)` que significa "o Ouro estava
        # legivel e nao caiu". As fabricas ja default 1 quando ninguem
        # informa, entao a defesa aqui so servia para desfazer o zero.
        unidades = evento.unidades
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
        # O Estoque estimado é contagem interna otimista, nunca relida do
        # Armazém: ele subconta sempre que uma Compra acontece sem queda de
        # Ouro legível. Listar mais do que ele contava é informação sobre a
        # divergência, não erro de programação — o Crítico se corrige por
        # saturação. Levantar aqui matava a sessão no caminho canônico do
        # regime rápido, onde o Estoque começa em 0 e a única Venda é a do
        # toast de inventário cheio.
        novo = replace(
            estado,
            estoque_estimado=max(0, estado.estoque_estimado - evento.unidades),
        )
        return novo, AcaoFluxo.CONTINUAR_VENDA

    if tipo is _TipoEvento.CAPACIDADE_ATUALIZADA:
        return (
            replace(estado, capacidade_observada=evento.capacidade),
            AcaoFluxo.CONTINUAR_VENDA,
        )

    # Sem chamador fora dos testes, de propósito: não existe hoje leitura dos
    # stacks restantes no Baú que sirva de fonte de verdade para reconciliar o
    # Estoque estimado com o Armazém real. `varrer_armazem` só enxerga o Baú
    # aberto no momento, e a Venda parcial nem chega a percorrer todos. Ligar
    # este evento exige trabalho de visão que não está feito; o ramo fica
    # implementado e testado para quando estiver.
    if tipo is _TipoEvento.ESTOQUE_RECONCILIADO:
        novo = replace(estado, estoque_estimado=evento.unidades)
        return novo, _acao_por_saldo(novo)

    if tipo is _TipoEvento.RETORNO_COMPRA:
        return estado, AcaoFluxo.CONTINUAR_COMPRA

    if tipo is _TipoEvento.VENDA_ENCERRADA:
        novo = replace(estado, retomada_pendente=evento.resta_lote_cheio)
        return novo, AcaoFluxo.CONTINUAR_COMPRA

    if tipo is _TipoEvento.JANELA_DE_VENDA_ABERTA:
        # Reavaliacao que nao depende de Compra nenhuma. Sem ela, o gatilho
        # por saldo so e consultado nos ramos de Compra, e o Fluxo Completo
        # reseta indefinidamente com o Armazem cheio e o Leilao seco.
        if estado.modo is not ModoFluxo.LENTO:
            return estado, AcaoFluxo.CONTINUAR_COMPRA
        if estado.estoque_estimado >= LOTE_DE_VENDA_EM_UNIDADES:
            return estado, AcaoFluxo.VENDER_POR_FLUXO_LENTO
        if estado.retomada_pendente:
            return estado, AcaoFluxo.VENDER_POR_RETOMADA
        return estado, AcaoFluxo.CONTINUAR_COMPRA

    raise ValueError(f"evento desconhecido: {tipo!r}")
