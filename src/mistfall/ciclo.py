"""O laco: repete a Compra ate o operador pedir parada.

Nao duplica nada do piloto nem do reset — compoe os dois. O piloto continua
sendo "uma Compra e para"; quem sabe que existe uma proxima Volta e este
modulo.

So o F3 encerra o laco. Nenhuma falha o encerra, por mais que se repita:
decisao do dono do projeto, registrada na spec junto com o que ela deixa em
aberto. A `espera_entre_voltas` e o que impede uma tela errada de virar um
laco em rotacao maxima.
"""

import itertools
import random
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from mistfall.config import Config
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.piloto import RITMO_PADRAO, Desfecho, Resultado, Ritmo, executar
from mistfall.reset import CategoriaAlternativa, resetar_categoria
from mistfall.telemetria import TelemetriaSessao

# Sem acento e sem cor. O projeto inteiro escreve saida de console assim, por
# causa da pagina de codigo do console do Windows: um mojibake na unica
# superficie que o operador ve enquanto o bot roda custa caro e nao avisa.
ROTULO_POR_DESFECHO = {
    Desfecho.COMPRA_ENVIADA: "compra enviada",
    Desfecho.NADA_COMPRAVEL: "nada",
    Desfecho.ABORTOU: "abortou",
    Desfecho.SIMULOU: "simulou",
    Desfecho.PAROU: "parou",
}

# A ordem e a alternancia: um Reset usa uma Categoria alternativa, e o
# proximo usa a outra. Nunca as duas no mesmo Reset.
ALTERNANCIA = (CategoriaAlternativa.FORJA, CategoriaAlternativa.CHAVE)

# Desfechos cuja Volta vale guardar inteira. O complemento — NADA_COMPRAVEL —
# e o caso comum e o unico que nao carrega diagnostico nenhum.
DESFECHOS_QUE_VALEM_PRINT = frozenset({
    Desfecho.COMPRA_ENVIADA, Desfecho.ABORTOU, Desfecho.PAROU,
})


@dataclass
class Sessao:
    """O acumulado da sessao, e nao a lista de Voltas.

    Guardar cada Resultado faria a memoria crescer sem teto numa sessao
    longa, que e exatamente o caso de uso.
    """

    voltas: int = 0
    compras_enviadas: int = 0


def texto_do_console(texto: str) -> str:
    # A pagina de codigo do console do Windows pode rejeitar acentos. O motivo
    # pode carregar texto de excecao vindo do sistema operacional.
    return unicodedata.normalize("NFKD", texto).encode(
        "ascii", "ignore").decode("ascii")


def linha_da_volta(numero: int, resultado: Resultado,
                   resetou: CategoriaAlternativa | None,
                   relogio: str,
                   reset_falhou: CategoriaAlternativa | None = None) -> str:
    # Sem default no lookup: desfecho novo tem de estourar aqui, e nao virar
    # uma linha muda no meio de uma sessao longa.
    # Quatro digitos, como a pasta da Volta: a ~7 s por Volta, mil Voltas sao
    # duas horas de sessao, e tres digitos estourariam antes do fim do dia.
    partes = [f"[{numero:04d}]", relogio, ROTULO_POR_DESFECHO[resultado.desfecho]]

    if (resultado.desfecho is Desfecho.COMPRA_ENVIADA
            and resultado.listagem is not None):
        item = resultado.listagem.item
        partes.append(item.value if item is not None else "?")
        partes.append(f"{resultado.listagem.preco_unitario}g")
    if resetou is not None:
        partes.append(f"-> Reset ({resetou.value})")
    if reset_falhou is not None:
        partes.append(f"-> Reset falhou ({reset_falhou.value})")
    if resultado.motivo:
        partes.append(texto_do_console(resultado.motivo))

    return "  ".join(partes)


def linhas_do_fecho(sessao: Sessao) -> list[str]:
    return [
        "",
        f"parado. {sessao.voltas} Voltas, "
        f"{sessao.compras_enviadas} Compras enviadas",
    ]


def executar_ciclo(tela: Tela, mao: Mao, config: Config, pasta: Path,
                   interruptor: Interruptor, ritmo: Ritmo = RITMO_PADRAO,
                   sorteio: random.Random | None = None) -> Sessao:
    if sorteio is None:
        sorteio = random.Random()

    interruptor.esperar_inicio()

    sessao = Sessao()
    categorias = itertools.cycle(ALTERNANCIA)
    proxima_categoria = next(categorias)
    sem_aborto_anterior = object()
    ultimo_motivo_de_aborto: str | object = sem_aborto_anterior
    pasta = Path(pasta)
    inicio_da_sessao = time.monotonic()
    telemetria = TelemetriaSessao(pasta, inicio_da_sessao)
    inicio_anterior = None
    espera_anterior = None
    volta_anterior = None

    while not interruptor.pediram_parada():
        inicio_da_volta = time.monotonic()
        if inicio_anterior is not None:
            telemetria.registrar_intervalo(
                volta_anterior,
                inicio_da_volta,
                espera_anterior * 1000,
                (inicio_da_volta - inicio_anterior) * 1000,
            )

        sessao.voltas += 1
        pasta_da_volta = pasta / f"volta-{sessao.voltas:04d}"

        def registrar_ouro(ouro, instante, horario) -> None:
            telemetria.registrar_ouro(
                sessao.voltas, ouro, instante, horario
            )

        resultado = executar(tela, mao, config, pasta_da_volta, ritmo=ritmo,
                             sorteio=sorteio, interruptor=interruptor,
                             observador_ouro=registrar_ouro)
        _contabilizar(sessao, resultado)

        resetou = None
        reset_falhou = None
        if resultado.desfecho is Desfecho.NADA_COMPRAVEL:
            if resetar_categoria(
                tela, mao, ritmo, categoria_alternativa=proxima_categoria,
                sorteio=sorteio,
            ):
                resetou = proxima_categoria
                proxima_categoria = next(categorias)
            else:
                reset_falhou = proxima_categoria

        aborto_repetido = (
            resultado.desfecho is Desfecho.ABORTOU
            and ultimo_motivo_de_aborto == resultado.motivo
        )
        volta_de_rotina = (
            resultado.desfecho not in DESFECHOS_QUE_VALEM_PRINT
            and reset_falhou is None
        )
        if aborto_repetido or volta_de_rotina:
            _descartar_os_prints(pasta_da_volta)

        if resultado.desfecho is Desfecho.ABORTOU:
            ultimo_motivo_de_aborto = resultado.motivo
        else:
            ultimo_motivo_de_aborto = sem_aborto_anterior

        print(linha_da_volta(sessao.voltas, resultado, resetou,
                             time.strftime("%H:%M:%S"), reset_falhou),
              flush=True)

        if resultado.desfecho is Desfecho.PAROU:
            break

        inicio_anterior = inicio_da_volta
        volta_anterior = sessao.voltas
        inicio_espera = time.monotonic()
        time.sleep(ritmo.espera_entre_voltas)
        espera_anterior = time.monotonic() - inicio_espera

    for linha in linhas_do_fecho(sessao):
        print(linha, flush=True)

    return sessao


def _contabilizar(sessao: Sessao, resultado: Resultado) -> None:
    if resultado.desfecho is not Desfecho.COMPRA_ENVIADA:
        return
    sessao.compras_enviadas += 1


def _descartar_os_prints(pasta: Path) -> None:
    """Apaga so os PNGs, nunca o relatorio.

    O descarte e do ciclo, e nao do piloto: quem sabe que a Volta foi rotina
    e quem viu o desfecho. O piloto continua gravando tudo e segue ignorante
    do laco.
    """
    for png in pasta.glob("*.png"):
        png.unlink()
