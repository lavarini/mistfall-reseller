"""Reset isolado da lista do Leilao por troca de Categoria."""

import time

from mistfall.estado import identificar_estado
from mistfall.geometria import (
    CATEGORIA_MATERIAL_CONSTRUCAO,
    CATEGORIA_MATERIAL_FORJA,
)
from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.piloto import RITMO_PADRAO, Ritmo
from mistfall.tipos import EstadoTela


def resetar_categoria(
    tela: Tela,
    mao: Mao,
    ritmo: Ritmo = RITMO_PADRAO,
) -> bool:
    """Troca para Material de Forja e volta para Material de Construcao.

    O retorno so e verdadeiro quando as duas transicoes foram observadas. A
    segunda captura e o portao para uma varredura futura: ela precisa provar
    que Material de Construcao voltou a estar selecionada.
    """
    mao.clicar(*CATEGORIA_MATERIAL_FORJA)
    time.sleep(ritmo.espera_categoria_carregar)
    foi_para_forja = (
        identificar_estado(tela.capturar()) is EstadoTela.OUTRA_CATEGORIA
    )

    mao.clicar(*CATEGORIA_MATERIAL_CONSTRUCAO)
    time.sleep(ritmo.espera_categoria_carregar)
    voltou_para_construcao = identificar_estado(tela.capturar()) is EstadoTela.LISTA

    return foi_para_forja and voltou_para_construcao
