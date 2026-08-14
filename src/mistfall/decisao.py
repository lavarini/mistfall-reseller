import random

from mistfall.config import Config
from mistfall.tipos import Listagem


def _comprável(listagem: Listagem, config: Config) -> bool:
    """Compravel e o que esta EXATAMENTE no corte.

    Os Itens-alvo nunca ficam abaixo do corte — verificado em 49 observacoes
    do corpus, zero abaixo. Entao preco menor que o corte e leitura suspeita,
    nao pechincha, e a regra de igualdade encolhe a janela de erro perigoso de
    "todo o intervalo abaixo" para "um unico valor".
    """
    if listagem.item is None or listagem.preco_unitario is None:
        return False
    alvo = config.precos_alvo.get(listagem.item)
    if alvo is None:
        return False
    return listagem.preco_unitario == alvo


def escolher(listagens: list[Listagem], config: Config,
             sorteio: random.Random) -> Listagem | None:
    """Sorteia uma entre as Listagens que estao no corte.

    Com igualdade exata todos os candidatos empatam, entao nao existe criterio
    natural de desempate. Ordem de leitura seria o pior possivel: a lista e
    ordenada por preco crescente, entao ela premiaria sempre os cortes mais
    baratos — medido no corpus, Orbe e Codice nunca seriam comprados.

    O sorteador vem de fora para os testes poderem fixar a semente.
    """
    candidatas = [l for l in listagens if _comprável(l, config)]
    if not candidatas:
        return None
    return sorteio.choice(candidatas)
