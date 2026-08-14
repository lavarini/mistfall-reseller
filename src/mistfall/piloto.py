"""Orquestra uma unica Compra: varre, decide, clica, confere e aperta Espaco.

Uma Compra e para. Sem loop, sem Reset — esses sao a #6 e a #7.

Nao sabe se fala com o Windows ou com um duble: toda a fronteira de IO
passa pelos protocolos Tela e Mao.
"""

import json
import random
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

import cv2
import numpy as np

from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.estado import identificar_estado
from mistfall.geometria import caixa_slot
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_preco_total_da_janela, ler_quantidade_da_janela,
    pontuar_icone_da_janela,
)
from mistfall.leilao import varrer
from mistfall.ouro import ler_ouro
from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.tipos import EstadoTela, ItemAlvo, Listagem

@dataclass(frozen=True)
class Ritmo:
    """Todos os tempos do piloto, num lugar so e injetaveis.

    Existem como parametro, e nao como constante de modulo, para os testes
    poderem rodar sem esperar de verdade. Sem isso a suite paga ~25s so em
    sleep.
    """

    pausa_antes_do_clique: tuple[float, float] = (0.2, 0.6)
    intervalo_entre_perguntas: float = 0.1
    # 10 s, como na spec. Ha informacao verbal de que o modal e instantaneo,
    # mas ela nao vale a viagem: esperar de graca custa 10 s numa execucao
    # unica, e abortar por uma primeira carga de UI mais lenta custa o dia.
    teto_espera_janela: float = 10.0
    espera_apos_espaco: float = 2.0
    teto_espera_ouro: float = 5.0

    @classmethod
    def instantaneo(cls) -> "Ritmo":
        """Para testes: nao espera nada, mas mantem os tetos positivos para
        os lacos de enquete continuarem executando ao menos uma volta."""
        return cls(
            pausa_antes_do_clique=(0.0, 0.0),
            intervalo_entre_perguntas=0.0,
            teto_espera_janela=0.05,
            espera_apos_espaco=0.0,
            teto_espera_ouro=0.05,
        )


RITMO_PADRAO = Ritmo()


class Desfecho(Enum):
    COMPROU = "comprou"
    # Apertamos Espaco e o Ouro nao se moveu. Nao e Compra, e nao pode sair
    # com o mesmo codigo de COMPROU: "o Espaco nao registrou" e exatamente a
    # pergunta que a execucao no Windows existe para responder.
    OURO_NAO_CAIU = "ouro_nao_caiu"
    NADA_COMPRAVEL = "nada_compravel"
    # Separado de NADA_COMPRAVEL: o roteiro usa "nada_compravel" como portao
    # ("se nao bater, pare aqui"), e uma simulacao bem-sucedida imprimindo
    # esse desfecho convida o operador ao erro.
    SIMULOU = "simulou"
    ABORTOU = "abortou"


@dataclass
class Resultado:
    desfecho: Desfecho
    motivo: str = ""
    listagem: Listagem | None = None
    ouro_antes: int | None = None
    ouro_depois: int | None = None
    preco_total_esperado: int | None = None
    segundos_ate_a_janela: float | None = None
    # Tudo que foi lido dentro da Janela, gravado mesmo quando aborta: e o
    # diagnostico que volta da maquina Windows, onde ninguem pode depurar.
    item_no_modal: str | None = None
    preco_no_modal: int | None = None
    quantidade_no_modal: int | None = None
    escala_do_icone: float | None = None
    scores_do_icone: dict[str, float] | None = None
    capturas: list[str] = field(default_factory=list)


class _Diario:
    """Salva cada captura numerada e o que o bot leu nela."""

    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.nomes: list[str] = []

    def registrar(self, img: np.ndarray, rotulo: str) -> None:
        nome = f"{len(self.nomes):02d}-{rotulo}.png"
        cv2.imwrite(str(self.pasta / nome), img)
        self.nomes.append(nome)

    def fechar(self, resultado: Resultado) -> None:
        resultado.capturas = list(self.nomes)
        dados = asdict(resultado)
        dados["desfecho"] = resultado.desfecho.value
        if resultado.listagem is not None:
            dados["listagem"] = {
                "linha": resultado.listagem.linha,
                "coluna": resultado.listagem.coluna,
                "item": resultado.listagem.item.value if resultado.listagem.item else None,
                "preco_unitario": resultado.listagem.preco_unitario,
            }
        (self.pasta / "relatorio.json").write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _esperar_janela(tela: Tela, diario: _Diario,
                    ritmo: Ritmo) -> tuple[np.ndarray | None, float]:
    inicio = time.monotonic()
    primeira_volta = True
    while primeira_volta or time.monotonic() - inicio < ritmo.teto_espera_janela:
        primeira_volta = False
        img = tela.capturar()
        if identificar_estado(img) is EstadoTela.JANELA_CONFIRMACAO:
            diario.registrar(img, "janela")
            return img, time.monotonic() - inicio
        time.sleep(ritmo.intervalo_entre_perguntas)
    return None, time.monotonic() - inicio


def _nome(item: ItemAlvo | None) -> str:
    """Nome de dominio, nunca o Enum cru: e a linha que o operador le."""
    return item.value if item is not None else "nenhum Item-alvo reconhecido"


def _conferir_a_janela(modal: np.ndarray, escolhida: Listagem,
                       r: Resultado) -> str | None:
    """Le a Janela inteira, guarda tudo no Resultado e devolve a primeira
    divergencia contra a Listagem escolhida — None quando esta tudo certo.

    Le antes de conferir, e grava antes de decidir: mesmo abortando, o
    relatorio tem de dizer o que o bot viu. Cada leitura ilegivel tem ramo
    proprio porque a mensagem e o unico diagnostico que atravessa a viagem.
    """
    item = ler_item_da_janela(modal)
    r.item_no_modal = item.value if item is not None else None
    r.escala_do_icone, scores = pontuar_icone_da_janela(modal)
    r.scores_do_icone = {alvo.value: round(score, 4)
                         for alvo, score in scores.items()}
    r.preco_no_modal = ler_preco_da_janela(modal)
    r.quantidade_no_modal = ler_quantidade_da_janela(modal)
    r.preco_total_esperado = ler_preco_total_da_janela(modal)

    if item is not escolhida.item:
        return (f"o modal mostra {_nome(item)}, "
                f"decidimos comprar {_nome(escolhida.item)}")
    if r.preco_no_modal is None:
        return "Preco Unitario ilegivel no modal"
    if r.preco_no_modal != escolhida.preco_unitario:
        return (f"o modal cobra {r.preco_no_modal}, "
                f"a Listagem dizia {escolhida.preco_unitario}")
    if r.quantidade_no_modal is None:
        return "Quantidade ilegivel no modal"
    if r.quantidade_no_modal != 1:
        return f"a Quantidade e {r.quantidade_no_modal}, esperava 1"
    if r.preco_total_esperado is None:
        return "Preco Total ilegivel no modal"
    if r.preco_total_esperado != r.preco_no_modal:
        # Redundancia de graca com Quantidade 1: pega o OCR que perde um
        # digito da Quantidade e le 1 onde o modal mostra outra coisa.
        return (f"o Preco Total e {r.preco_total_esperado}, "
                f"e 1 unidade a {r.preco_no_modal} nao fecha com isso")
    return None


def _esperar_o_ouro_cair(tela: Tela, diario: _Diario, r: Resultado,
                         ritmo: Ritmo) -> None:
    """Enquete o Ouro ate a queda bater com o Preco Total, guardando sempre a
    ultima leitura legivel.

    Nao para na primeira leitura legivel: o Ouro quase sempre e legivel, entao
    parar ali le o valor *antigo* se o jogo ainda nao debitou, e o bot reporta
    Compra com queda zero. Tambem nao para em "mudou de valor": um frame de
    OCR ruidoso encerraria a espera com um numero inventado. O alvo e a queda
    exata; nao alcanca-la custa `teto_espera_ouro` numa execucao que ja deu
    errado de qualquer jeito.
    """
    ultima = None
    inicio = time.monotonic()
    primeira_volta = True
    while primeira_volta or time.monotonic() - inicio < ritmo.teto_espera_ouro:
        primeira_volta = False
        ultima = tela.capturar()
        lido = ler_ouro(ultima)
        if lido is not None:
            r.ouro_depois = lido
            if r.ouro_antes - lido == r.preco_total_esperado:
                break
        time.sleep(ritmo.intervalo_entre_perguntas)
    if ultima is not None:
        diario.registrar(ultima, "apos-espaco")


def executar(tela: Tela, mao: Mao, config: Config, pasta: Path,
             simular: bool = False, ritmo: Ritmo = RITMO_PADRAO) -> Resultado:
    diario = _Diario(Path(pasta))
    r = Resultado(Desfecho.ABORTOU, "explodiu antes da primeira captura")

    def encerrar(desfecho: Desfecho, motivo: str = "") -> Resultado:
        r.desfecho, r.motivo = desfecho, motivo
        return r

    # O relatorio e o produto desta execucao, e o bot clica no meio dela: sem
    # o finally, uma excecao inesperada deixa o operador com PNGs soltos
    # depois de ja ter mexido no jogo.
    try:
        inicial = tela.capturar()
        diario.registrar(inicial, "pre-voo")

        estado = identificar_estado(inicial)
        if estado is not EstadoTela.LISTA:
            return encerrar(Desfecho.ABORTOU,
                            f"pre-voo viu {estado.value}, esperava lista")

        r.ouro_antes = ler_ouro(inicial)
        if r.ouro_antes is None:
            return encerrar(Desfecho.ABORTOU, "Ouro inicial ilegivel")

        escolhida = escolher(varrer(inicial), config)
        if escolhida is None:
            return encerrar(Desfecho.NADA_COMPRAVEL,
                            "nenhuma Listagem abaixo do Preco-alvo")
        r.listagem = escolhida

        if simular:
            return encerrar(Desfecho.SIMULOU, "modo simulado: nao clicou")

        x0, y0, x1, y1 = caixa_slot(escolhida.linha, escolhida.coluna)
        time.sleep(random.uniform(*ritmo.pausa_antes_do_clique))
        mao.clicar((x0 + x1) // 2, (y0 + y1) // 2)

        modal, r.segundos_ate_a_janela = _esperar_janela(tela, diario, ritmo)
        if modal is None:
            return encerrar(Desfecho.ABORTOU, "a Janela de Confirmacao nao abriu")

        divergencia = _conferir_a_janela(modal, escolhida, r)
        if divergencia is not None:
            mao.apertar_esc()
            return encerrar(Desfecho.ABORTOU, divergencia)

        mao.apertar_espaco()
        time.sleep(ritmo.espera_apos_espaco)
        _esperar_o_ouro_cair(tela, diario, r, ritmo)

        if r.ouro_depois is None:
            return encerrar(Desfecho.ABORTOU,
                            "Ouro final ilegivel: Compra indeterminada")

        caiu = r.ouro_antes - r.ouro_depois
        if caiu == r.preco_total_esperado:
            return encerrar(Desfecho.COMPROU)
        if caiu == 0:
            return encerrar(
                Desfecho.OURO_NAO_CAIU,
                f"apertamos Espaco e o Ouro continua em {r.ouro_depois} depois "
                f"de {ritmo.teto_espera_ouro:.0f}s: ou o Espaco nao registrou, "
                "ou a Compra nao foi debitada")
        return encerrar(Desfecho.COMPROU,
                        f"Ouro caiu {caiu}, esperava {r.preco_total_esperado}")
    except Exception as erro:
        r.desfecho = Desfecho.ABORTOU
        r.motivo = f"explodiu: {type(erro).__name__}: {erro}"
        raise
    finally:
        diario.fechar(r)
