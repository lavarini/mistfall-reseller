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
        if resultado.desfecho not in DESFECHOS_QUE_VALEM_PRINT:
            _descartar_os_prints(pasta_da_volta)

        if resultado.desfecho is Desfecho.NADA_COMPRAVEL:
            resetar_categoria(tela, mao, ritmo,
                              categoria_alternativa=next(categorias))

        time.sleep(ritmo.espera_entre_voltas)

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
