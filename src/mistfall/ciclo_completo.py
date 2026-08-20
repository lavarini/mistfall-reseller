"""Coordena Compra e Venda num unico laco adaptativo.

Compoe o que as Tasks 1-6 ja entregaram: `fluxo.py` decide o que fazer a
partir de eventos observados, `piloto.executar` roda uma Compra, `reset.py`
troca a Categoria quando nao ha o que comprar, `navegacao.py` confirma as
transicoes de aba/filtro, e `ciclo_venda.executar_venda_parcial` esvazia o
Bau 2 sem fechar a sessao de Venda. Este modulo nao inventa politica nova:
so decide QUANDO chamar cada um deles e junta os resultados num relatorio.

O toast da Compra anterior e o Ouro que confirma (ou nao) o seu envio sao
lidos do MESMO frame: `piloto.executar` chama `observador_frame_inicial`
com a captura de pre-voo antes de qualquer clique, e essa mesma captura
alimenta tanto `Resultado.ouro_observado` quanto `detectar_mensagem_compra`
aqui. Nao ha captura extra so para classificar o toast.

Confirmar uma Compra enviada depende de dois sinais, nesta ordem de
prioridade:

1. O toast "cheios" (`MensagemCompra.INVENTARIO_CHEIO`) sempre vale, mesmo
   sem Compra pendente: ele por si so manda vender.
2. Com Compra pendente, o toast "realizada"/"guardado" confirma; senao,
   compara-se o Ouro observado nesta Volta com o Ouro no momento do envio.
   Ouro legivel e sem queda vira `compra_inconclusiva(unidades=0)` — o
   contrato aceita a unidade provisoria, mas aqui o sinal diz "nao houve
   queda", entao nada e somado ao Estoque. Ouro ilegivel ou fora dessas
   duas leituras vira `compra_inconclusiva()` (a unidade default), porque
   nao ha evidencia contra a Compra ter acontecido.

Nenhum desses sinais isolados encerra o laco. So a falha persistente de
navegacao (depois das retentativas que `navegacao.py` ja faz sozinho), a
falha persistente de visao (`Desfecho.ABORTOU` do proprio `piloto.executar`
por `LIMITE_ABORTOS_CONSECUTIVOS` Voltas seguidas) e o F4 do operador — em
Compra ou em Venda — terminam a sessao.

Uma Volta `ABORTOU` conta para esse limite; qualquer Volta que nao seja
`ABORTOU` zera o contador, incluindo `Desfecho.SIMULOU` — SIMULOU e uma
simulacao bem-sucedida, nao falha, e contá-la junto derrubaria uma sessao
inteira rodada com `simular=True` na quinta Volta.
"""

import itertools
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np

from mistfall.ciclo_venda import DesfechoSessaoVenda, executar_venda_parcial
from mistfall.compra_visao import MensagemCompra, detectar_mensagem_compra
from mistfall.config import Config
from mistfall.fluxo import (
    AcaoFluxo,
    EstadoFluxo,
    EventoFluxo,
    aplicar_evento,
    estado_inicial,
)
from mistfall.navegacao import garantir_filtro_roxo, ir_para_compra, ir_para_venda
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.piloto import RITMO_PADRAO, Desfecho, Ritmo, executar
from mistfall.reset import CategoriaAlternativa, resetar_categoria
from mistfall.venda import RITMO_VENDA_PADRAO, RitmoVenda


# Um Reset usa uma Categoria alternativa, e o proximo usa a outra — mesma
# alternancia de `ciclo.py`, para nao gastar sempre a mesma Categoria de
# apoio.
_ALTERNANCIA_RESET = (CategoriaAlternativa.FORJA, CategoriaAlternativa.CHAVE)

_ACOES_DE_VENDA = (AcaoFluxo.VENDER_POR_INVENTARIO_CHEIO, AcaoFluxo.VENDER_POR_FLUXO_LENTO)

# Mesma ideia de `resets_consecutivos >= 5` que `fluxo.py` ja usa como
# limiar de persistencia — um so vocabulario de limiar para o modo completo.
# Falha de visao (ABORTOU) e uma queda cega do piloto, entao o limite vive
# aqui, fora do contrato puro de `fluxo.py`, que continua selado.
LIMITE_ABORTOS_CONSECUTIVOS = 5


class DesfechoSessaoCompleta(Enum):
    PAROU = "parou"
    ABORTOU = "abortou"


@dataclass
class SessaoCompleta:
    desfecho: DesfechoSessaoCompleta = DesfechoSessaoCompleta.ABORTOU
    motivo: str = ""
    estado: EstadoFluxo = field(default_factory=EstadoFluxo)
    compras_enviadas: int = 0
    unidades_listadas: int = 0
    # Trilha em memoria de cada EventoFluxo aplicado nesta sessao. A
    # telemetria persistente (JSONL) e da Task 8 — aqui fica so o
    # acumulado que o proprio processo consegue inspecionar.
    eventos: list[EventoFluxo] = field(default_factory=list)


def executar_ciclo_completo(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo_compra: Ritmo = RITMO_PADRAO,
    ritmo_venda: RitmoVenda = RITMO_VENDA_PADRAO,
    sorteio: random.Random | None = None,
) -> SessaoCompleta:
    if sorteio is None:
        sorteio = random.Random()
    pasta = Path(pasta)

    interruptor.esperar_inicio()

    sessao = SessaoCompleta(estado=estado_inicial())
    estado = sessao.estado

    def aplicar(evento: EventoFluxo) -> AcaoFluxo:
        nonlocal estado
        sessao.eventos.append(evento)
        estado, acao = aplicar_evento(estado, evento)
        sessao.estado = estado
        return acao

    def encerrar(desfecho: DesfechoSessaoCompleta, motivo: str = "") -> SessaoCompleta:
        sessao.desfecho = desfecho
        sessao.motivo = motivo
        sessao.estado = estado
        return sessao

    # O modo completo comeca em Comprar, Item -> Material de Construcao: a
    # unica coisa que falta confirmar antes do laco e o filtro roxo.
    filtro = garantir_filtro_roxo(tela, mao, ritmo_venda)
    if not filtro.sucesso:
        return encerrar(DesfechoSessaoCompleta.ABORTOU, filtro.motivo)

    categorias = itertools.cycle(_ALTERNANCIA_RESET)
    proxima_categoria = next(categorias)
    ouro_no_envio: int | None = None
    numero_da_volta = 0
    numero_da_venda = 0
    abortos_consecutivos = 0

    while True:
        if interruptor.pediram_parada():
            return encerrar(DesfechoSessaoCompleta.PAROU)

        numero_da_volta += 1
        pasta_da_volta = pasta / f"volta-{numero_da_volta:04d}"

        frame_inicial: np.ndarray | None = None

        def observar(frame: np.ndarray) -> None:
            nonlocal frame_inicial
            frame_inicial = frame

        resultado = executar(
            tela, mao, config, pasta_da_volta,
            ritmo=ritmo_compra, sorteio=sorteio, interruptor=interruptor,
            observador_frame_inicial=observar,
        )

        # F4 pode ter sido apertado dentro da propria Compra (antes do
        # clique). Nao e falha estrategica: encerra a sessao na hora.
        if resultado.desfecho is Desfecho.PAROU:
            return encerrar(DesfechoSessaoCompleta.PAROU)

        # Falha persistente de visao: SIMULOU nao conta (e sucesso, nao
        # falha), e qualquer Volta que nao seja ABORTOU zera o contador.
        if resultado.desfecho is Desfecho.ABORTOU:
            abortos_consecutivos += 1
            if abortos_consecutivos >= LIMITE_ABORTOS_CONSECUTIVOS:
                return encerrar(DesfechoSessaoCompleta.ABORTOU, resultado.motivo)
        else:
            abortos_consecutivos = 0

        mensagem = (
            detectar_mensagem_compra(frame_inicial)
            if frame_inicial is not None
            else MensagemCompra.NENHUMA
        )
        ouro_agora = resultado.ouro_observado

        # Confirmacao da Compra da Volta anterior, lida no mesmo frame que
        # abriu esta Volta.
        acao_confirmacao: AcaoFluxo | None = None
        if mensagem is MensagemCompra.INVENTARIO_CHEIO:
            acao_confirmacao = aplicar(EventoFluxo.MENSAGEM_INVENTARIO_CHEIO)
            ouro_no_envio = None
        elif estado.compra_pendente:
            confirmou = mensagem is MensagemCompra.SUCESSO or (
                ouro_agora is not None
                and ouro_no_envio is not None
                and ouro_agora < ouro_no_envio
            )
            sem_queda_legivel = (
                not confirmou
                and ouro_agora is not None
                and ouro_no_envio is not None
                and ouro_agora >= ouro_no_envio
            )
            if confirmou:
                acao_confirmacao = aplicar(EventoFluxo.compra_confirmada(unidades=1))
            elif sem_queda_legivel:
                acao_confirmacao = aplicar(EventoFluxo.compra_inconclusiva(unidades=0))
            else:
                acao_confirmacao = aplicar(EventoFluxo.compra_inconclusiva())
            ouro_no_envio = None

        # O que esta propria Volta encontrou: uma intencao (Listagem no
        # Preco-alvo, envie-se ou nao a Compra) ou nada compravel.
        if resultado.listagem is not None:
            acao_propria = aplicar(EventoFluxo.intencao_detectada())
            if resultado.desfecho is Desfecho.COMPRA_ENVIADA:
                sessao.compras_enviadas += 1
                aplicar(EventoFluxo.compra_enviada())
                ouro_no_envio = ouro_agora
        elif resultado.desfecho is Desfecho.NADA_COMPRAVEL:
            resetar_categoria(
                tela, mao, ritmo_compra,
                categoria_alternativa=proxima_categoria, sorteio=sorteio,
            )
            proxima_categoria = next(categorias)
            acao_propria = aplicar(EventoFluxo.reset_executado())
        else:
            # ABORTOU/SIMULOU isolado: sinal ambiguo, nao e terminal e nao
            # justifica Reset por si so.
            acao_propria = AcaoFluxo.CONTINUAR_COMPRA

        acao = acao_confirmacao if acao_confirmacao in _ACOES_DE_VENDA else acao_propria

        if acao not in _ACOES_DE_VENDA:
            time.sleep(ritmo_compra.espera_entre_voltas)
            continue

        nav_venda = ir_para_venda(tela, mao, ritmo_venda)
        if not nav_venda.sucesso:
            return encerrar(DesfechoSessaoCompleta.ABORTOU, nav_venda.motivo)

        numero_da_venda += 1
        pasta_da_venda = pasta / f"venda-{numero_da_venda:04d}"
        venda = executar_venda_parcial(
            tela, mao, config, pasta_da_venda, interruptor, ritmo_venda, sorteio,
        )
        sessao.unidades_listadas += venda.unidades_listadas
        if venda.unidades_listadas:
            aplicar(EventoFluxo.unidades_listadas(venda.unidades_listadas))

        # F4 tambem pode ter sido apertado dentro da Venda.
        if venda.desfecho is DesfechoSessaoVenda.PAROU:
            return encerrar(DesfechoSessaoCompleta.PAROU)

        nav_compra = ir_para_compra(tela, mao, ritmo_venda)
        if not nav_compra.sucesso:
            return encerrar(DesfechoSessaoCompleta.ABORTOU, nav_compra.motivo)

        if interruptor.pediram_parada():
            return encerrar(DesfechoSessaoCompleta.PAROU)
