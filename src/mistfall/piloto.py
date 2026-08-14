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
from mistfall.leilao import conferir_ordenacao, varrer_bruto
from mistfall.ouro import ler_ouro
from mistfall.paralelo import mapear
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
    # 10 s, como na spec. Ha informacao verbal de que o modal e instantaneo,
    # mas ela nao vale a viagem: esperar de graca custa 10 s numa execucao
    # unica, e abortar por uma primeira carga de UI mais lenta custa o dia.
    teto_espera_janela: float = 10.0
    # A Janela abre com animacao e e detectavel antes de terminar de se
    # expandir. Esta e a espera entre detectar e capturar o frame que vai ser
    # validado. 1,5 s e generoso de proposito: velocidade nao e requisito, e
    # esperar de graca custa 1,5 s numa execucao unica.
    espera_para_o_modal_assentar: float = 1.5
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
            espera_para_o_modal_assentar=0.0,
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
    # As doze Listagens do pre-voo, com o preco antes e depois da conferencia
    # de ordenacao. Guardar so o conferido esconderia a leitura que derrubou a
    # tela; guardar so o bruto esconderia quais slots a regra invalidou.
    slots: list[dict] | None = None
    capturas: list[str] = field(default_factory=list)
    # Tempo de cada etapa, em milissegundos
    tempos: dict[str, float] = field(default_factory=dict)


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
            # Nao grava aqui: o frame que interessa ao relatorio e o que foi
            # de fato validado, e este ainda pode estar em renderizacao.
            return img, time.monotonic() - inicio
        time.sleep(ritmo.intervalo_entre_perguntas)
    return None, time.monotonic() - inicio


def _capturar_a_janela_assentada(tela: Tela, diario: _Diario, ritmo: Ritmo,
                                 detectado: np.ndarray) -> np.ndarray:
    """Devolve o frame da Janela que vale a pena validar, e o grava.

    A Janela abre com animacao: ela e reconhecivel como JANELA_CONFIRMACAO
    enquanto ainda esta se expandindo, e nessa fase os campos numericos estao
    a 69 px da posicao final — medido em `images/janela-em-animacao-rede-260`.
    As regioes fixas caem sobre fundo vazio, o OCR devolve None, e o piloto
    reprova uma Compra boa. Foi o que aconteceu na maquina do jogo (#18).

    A espera e fixa, e nao uma comparacao entre frames consecutivos. A
    tentativa anterior comparava as tres regioes numericas e concluia
    'assentado' quando duas capturas seguidas eram iguais — mas durante a
    animacao essas regioes estao sobre fundo liso, e preto igual a preto deu
    falso positivo em ~0,1 s. O laco saia cedo, entao aumentar o teto nao
    resolvia nada. Qualquer criterio de estabilidade tem de olhar pixel que
    muda durante a animacao; simplesmente esperar dispensa o criterio.

    Se a Janela sair de cena durante a espera, vale o frame detectado — senao
    o piloto valida a tela que ficou atras dela.
    """
    time.sleep(ritmo.espera_para_o_modal_assentar)
    assentado = tela.capturar()
    if identificar_estado(assentado) is not EstadoTela.JANELA_CONFIRMACAO:
        assentado = detectado
    diario.registrar(assentado, "janela")
    return assentado


def _conferir_a_janela(modal: np.ndarray, escolhida: Listagem,
                       r: Resultado, trabalhadores: int) -> str | None:
    """Le a Janela inteira, guarda tudo no Resultado e devolve a primeira
    divergencia contra a Listagem escolhida — None quando esta tudo certo.

    Le antes de conferir, e grava antes de decidir: mesmo abortando, o
    relatorio tem de dizer o que o bot viu. Cada leitura ilegivel tem ramo
    proprio porque a mensagem e o unico diagnostico que atravessa a viagem.

    O Icone e lido e pontuado, mas nao e portao: a varredura de escala
    0,85-1,15 de `ler_item_da_janela` e palpite calibrado, nao medida, e 5%
    de diferenca de escala ja derruba a identificacao para None. Na maquina
    real isso deu 100% de falso negativo (#18) — o piloto validava o
    primeiro frame em que o modal era detectavel, que e antes de o Icone
    estar desenhado, o template nao casava, e ele apertava Esc em vez de
    comprar. O Icone tambem nunca demonstrou valor: dos seis erros de OCR
    conhecidos do corpus, nenhum teria sido pego so pela conferencia do
    modal — os nulls e os absurdos sao pegos pela faixa de sanidade, e foi a
    conferencia de ordenacao que pegou o unico erro de slot errado (#17).
    Continua sendo lido e gravado no relatorio porque foi exatamente esse
    dado, a distancia, que permitiu diagnosticar a #18 sem ninguem na frente
    da maquina — nao reintroduza o ramo de aborto achando que foi esquecido.
    """
    item = ler_item_da_janela(modal)
    r.item_no_modal = item.value if item is not None else None
    r.escala_do_icone, scores = pontuar_icone_da_janela(modal)
    r.scores_do_icone = {alvo.value: round(score, 4)
                         for alvo, score in scores.items()}
    r.preco_no_modal, r.quantidade_no_modal, r.preco_total_esperado = mapear(
        lambda ler: ler(modal),
        (ler_preco_da_janela, ler_quantidade_da_janela, ler_preco_total_da_janela),
        trabalhadores,
    )

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
             simular: bool = False, ritmo: Ritmo = RITMO_PADRAO,
             sorteio: random.Random | None = None) -> Resultado:
    diario = _Diario(Path(pasta))
    r = Resultado(Desfecho.ABORTOU, "explodiu antes da primeira captura")
    if sorteio is None:
        sorteio = random.Random()

    def encerrar(desfecho: Desfecho, motivo: str = "") -> Resultado:
        r.desfecho, r.motivo = desfecho, motivo
        return r

    # O relatorio e o produto desta execucao, e o bot clica no meio dela: sem
    # o finally, uma excecao inesperada deixa o operador com PNGs soltos
    # depois de ja ter mexido no jogo.
    try:
        t_pre_voo = time.monotonic()
        inicial = tela.capturar()
        diario.registrar(inicial, "pre-voo")

        estado = identificar_estado(inicial)
        if estado is not EstadoTela.LISTA:
            return encerrar(Desfecho.ABORTOU,
                            f"pre-voo viu {estado.value}, esperava lista")

        r.ouro_antes = ler_ouro(inicial)
        if r.ouro_antes is None:
            return encerrar(Desfecho.ABORTOU, "Ouro inicial ilegivel")

        r.tempos["pre_voo"] = (time.monotonic() - t_pre_voo) * 1000

        # Em dois passos, e nao pelo `varrer`, para o relatorio poder mostrar
        # o que o OCR entregou ao lado do que a conferencia deixou passar.
        t_varredura = time.monotonic()
        brutas = varrer_bruto(inicial, config.trabalhadores)
        conferidas = conferir_ordenacao(brutas)
        r.slots = [
            {
                "linha": bruta.linha,
                "coluna": bruta.coluna,
                "item": bruta.item.value if bruta.item else None,
                "preco_bruto": bruta.preco_unitario,
                "preco_conferido": conferida.preco_unitario,
            }
            for bruta, conferida in zip(brutas, conferidas)
        ]

        escolhida = escolher(conferidas, config, sorteio)
        r.tempos["varredura"] = (time.monotonic() - t_varredura) * 1000

        if escolhida is None:
            return encerrar(Desfecho.NADA_COMPRAVEL,
                            "nenhuma Listagem no Preco-alvo")
        r.listagem = escolhida

        if simular:
            return encerrar(Desfecho.SIMULOU, "modo simulado: nao clicou")

        x0, y0, x1, y1 = caixa_slot(escolhida.linha, escolhida.coluna)
        time.sleep(random.uniform(*ritmo.pausa_antes_do_clique))
        mao.clicar((x0 + x1) // 2, (y0 + y1) // 2)

        t_modal = time.monotonic()
        modal, r.segundos_ate_a_janela = _esperar_janela(tela, diario, ritmo)
        if modal is None:
            return encerrar(Desfecho.ABORTOU, "a Janela de Confirmacao nao abriu")

        # segundos_ate_a_janela mede ate a DETECCAO, que e o numero que a #6
        # pede. A validacao acontece sobre o frame assentado, que vem depois.
        modal = _capturar_a_janela_assentada(tela, diario, ritmo, modal)

        divergencia = _conferir_a_janela(modal, escolhida, r, config.trabalhadores)
        r.tempos["modal"] = (time.monotonic() - t_modal) * 1000

        if divergencia is not None:
            mao.apertar_esc()
            return encerrar(Desfecho.ABORTOU, divergencia)

        t_confirmacao = time.monotonic()
        mao.apertar_espaco()
        time.sleep(ritmo.espera_apos_espaco)
        _esperar_o_ouro_cair(tela, diario, r, ritmo)
        r.tempos["confirmacao_do_ouro"] = (time.monotonic() - t_confirmacao) * 1000

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
    # BaseException, e nao Exception: o operador pode dar Ctrl+C no meio (nao
    # existe tecla de panico, e a #8 que traz), e o relatorio tem de dizer que
    # foi isso, nao ficar com o motivo de partida.
    except BaseException as erro:
        r.desfecho = Desfecho.ABORTOU
        r.motivo = f"explodiu: {type(erro).__name__}: {erro}"
        raise
    finally:
        diario.fechar(r)
