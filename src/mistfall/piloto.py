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
)
from mistfall.leilao import varrer
from mistfall.ouro import ler_ouro
from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.tipos import EstadoTela, Listagem

@dataclass(frozen=True)
class Ritmo:
    """Todos os tempos do piloto, num lugar so e injetaveis.

    Existem como parametro, e nao como constante de modulo, para os testes
    poderem rodar sem esperar de verdade. Sem isso a suite paga ~25s so em
    sleep.
    """

    pausa_antes_do_clique: tuple[float, float] = (0.2, 0.6)
    intervalo_entre_perguntas: float = 0.1
    teto_espera_janela: float = 3.0
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
    NADA_COMPRAVEL = "nada_compravel"
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


def executar(tela: Tela, mao: Mao, config: Config, pasta: Path,
             simular: bool = False, ritmo: Ritmo = RITMO_PADRAO) -> Resultado:
    diario = _Diario(Path(pasta))

    def encerrar(r: Resultado) -> Resultado:
        diario.fechar(r)
        return r

    inicial = tela.capturar()
    diario.registrar(inicial, "pre-voo")

    estado = identificar_estado(inicial)
    if estado is not EstadoTela.LISTA:
        return encerrar(Resultado(Desfecho.ABORTOU,
                                  f"pre-voo viu {estado.value}, esperava lista"))

    ouro_antes = ler_ouro(inicial)
    if ouro_antes is None:
        return encerrar(Resultado(Desfecho.ABORTOU, "Ouro inicial ilegivel"))

    escolhida = escolher(varrer(inicial), config)
    if escolhida is None:
        return encerrar(Resultado(Desfecho.NADA_COMPRAVEL,
                                  "nenhuma Listagem abaixo do Preco-alvo",
                                  ouro_antes=ouro_antes))

    if simular:
        return encerrar(Resultado(Desfecho.NADA_COMPRAVEL,
                                  "modo simulado: nao clicou",
                                  listagem=escolhida, ouro_antes=ouro_antes))

    x0, y0, x1, y1 = caixa_slot(escolhida.linha, escolhida.coluna)
    time.sleep(random.uniform(*ritmo.pausa_antes_do_clique))
    mao.clicar((x0 + x1) // 2, (y0 + y1) // 2)

    modal, demorou = _esperar_janela(tela, diario, ritmo)
    if modal is None:
        return encerrar(Resultado(Desfecho.ABORTOU,
                                  "a Janela de Confirmacao nao abriu",
                                  listagem=escolhida, ouro_antes=ouro_antes,
                                  segundos_ate_a_janela=demorou))

    item_no_modal = ler_item_da_janela(modal)
    preco_no_modal = ler_preco_da_janela(modal)
    quantidade = ler_quantidade_da_janela(modal)
    total = ler_preco_total_da_janela(modal)

    divergencia = None
    if item_no_modal is not escolhida.item:
        divergencia = (f"o modal mostra {item_no_modal}, "
                       f"decidimos comprar {escolhida.item}")
    elif preco_no_modal != escolhida.preco_unitario:
        divergencia = (f"o modal cobra {preco_no_modal}, "
                       f"a Listagem dizia {escolhida.preco_unitario}")
    elif quantidade != 1:
        divergencia = f"a Quantidade e {quantidade}, esperava 1"
    elif total is None:
        divergencia = "Preco Total ilegivel"

    if divergencia is not None:
        mao.apertar_esc()
        return encerrar(Resultado(Desfecho.ABORTOU, divergencia,
                                  listagem=escolhida, ouro_antes=ouro_antes,
                                  segundos_ate_a_janela=demorou))

    mao.apertar_espaco()
    time.sleep(ritmo.espera_apos_espaco)

    ouro_depois = None
    inicio = time.monotonic()
    primeira_volta = True
    while primeira_volta or time.monotonic() - inicio < ritmo.teto_espera_ouro:
        primeira_volta = False
        depois = tela.capturar()
        ouro_depois = ler_ouro(depois)
        if ouro_depois is not None:
            diario.registrar(depois, "apos-espaco")
            break
        time.sleep(ritmo.intervalo_entre_perguntas)

    if ouro_depois is None:
        return encerrar(Resultado(Desfecho.ABORTOU,
                                  "Ouro final ilegivel: Compra indeterminada",
                                  listagem=escolhida, ouro_antes=ouro_antes,
                                  preco_total_esperado=total,
                                  segundos_ate_a_janela=demorou))

    caiu = ouro_antes - ouro_depois
    motivo = "" if caiu == total else f"Ouro caiu {caiu}, esperava {total}"
    return encerrar(Resultado(Desfecho.COMPROU, motivo, listagem=escolhida,
                              ouro_antes=ouro_antes, ouro_depois=ouro_depois,
                              preco_total_esperado=total,
                              segundos_ate_a_janela=demorou))
