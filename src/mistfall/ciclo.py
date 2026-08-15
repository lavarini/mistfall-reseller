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
from dataclasses import dataclass
from pathlib import Path

from mistfall.config import Config
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.piloto import RITMO_PADRAO, Desfecho, Resultado, Ritmo, executar
from mistfall.reset import CategoriaAlternativa, resetar_categoria

# Sem acento e sem cor. O projeto inteiro escreve saida de console assim, por
# causa da pagina de codigo do console do Windows: um mojibake na unica
# superficie que o operador ve enquanto o bot roda custa caro e nao avisa.
ROTULO_POR_DESFECHO = {
    Desfecho.COMPROU: "comprou",
    Desfecho.NADA_COMPRAVEL: "nada",
    Desfecho.OURO_NAO_CAIU: "OURO NAO CAIU",
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
    Desfecho.COMPROU, Desfecho.OURO_NAO_CAIU, Desfecho.ABORTOU, Desfecho.PAROU,
})


@dataclass
class Sessao:
    """O acumulado da sessao, e nao a lista de Voltas.

    Guardar cada Resultado faria a memoria crescer sem teto numa sessao
    longa, que e exatamente o caso de uso.
    """

    voltas: int = 0
    compras: int = 0
    ouro_gasto: int = 0


def linha_da_volta(numero: int, resultado: Resultado,
                   resetou: CategoriaAlternativa | None,
                   relogio: str) -> str:
    # Sem default no lookup: desfecho novo tem de estourar aqui, e nao virar
    # uma linha muda no meio de uma sessao longa.
    # Quatro digitos, como a pasta da Volta: a ~7 s por Volta, mil Voltas sao
    # duas horas de sessao, e tres digitos estourariam antes do fim do dia.
    partes = [f"[{numero:04d}]", relogio, ROTULO_POR_DESFECHO[resultado.desfecho]]

    if resultado.desfecho is Desfecho.COMPROU and resultado.listagem is not None:
        item = resultado.listagem.item
        partes.append(item.value if item is not None else "?")
        partes.append(f"{resultado.listagem.preco_unitario}g")
    if resultado.ouro_antes is not None and resultado.ouro_depois is not None:
        partes.append(f"Ouro {resultado.ouro_antes} -> {resultado.ouro_depois}")
    if resetou is not None:
        partes.append(f"-> Reset ({resetou.value})")
    if resultado.motivo:
        partes.append(resultado.motivo)

    return "  ".join(partes)


def linhas_do_fecho(sessao: Sessao) -> list[str]:
    return [
        "",
        f"parado. {sessao.voltas} Voltas, {sessao.compras} Compras, "
        f"{sessao.ouro_gasto} de Ouro gasto",
    ]


def executar_ciclo(tela: Tela, mao: Mao, config: Config, pasta: Path,
                   interruptor: Interruptor, ritmo: Ritmo = RITMO_PADRAO,
                   sorteio: random.Random | None = None) -> Sessao:
    interruptor.esperar_inicio()

    sessao = Sessao()
    categorias = itertools.cycle(ALTERNANCIA)
    pasta = Path(pasta)

    while not interruptor.pediram_parada():
        sessao.voltas += 1
        pasta_da_volta = pasta / f"volta-{sessao.voltas:04d}"
        resultado = executar(tela, mao, config, pasta_da_volta, ritmo=ritmo,
                             sorteio=sorteio, interruptor=interruptor)
        _contabilizar(sessao, resultado)

        resetou = None
        if resultado.desfecho is Desfecho.NADA_COMPRAVEL:
            resetou = next(categorias)
            resetar_categoria(tela, mao, ritmo, categoria_alternativa=resetou)

        if resultado.desfecho not in DESFECHOS_QUE_VALEM_PRINT:
            _descartar_os_prints(pasta_da_volta)

        print(linha_da_volta(sessao.voltas, resultado, resetou,
                             time.strftime("%H:%M:%S")), flush=True)

        time.sleep(ritmo.espera_entre_voltas)

    for linha in linhas_do_fecho(sessao):
        print(linha, flush=True)

    return sessao


def _contabilizar(sessao: Sessao, resultado: Resultado) -> None:
    if resultado.desfecho is not Desfecho.COMPROU:
        return
    sessao.compras += 1
    if resultado.ouro_antes is not None and resultado.ouro_depois is not None:
        sessao.ouro_gasto += resultado.ouro_antes - resultado.ouro_depois


def _descartar_os_prints(pasta: Path) -> None:
    """Apaga so os PNGs, nunca o relatorio.

    O descarte e do ciclo, e nao do piloto: quem sabe que a Volta foi rotina
    e quem viu o desfecho. O piloto continua gravando tudo e segue ignorante
    do laco.
    """
    for png in pasta.glob("*.png"):
        png.unlink()
