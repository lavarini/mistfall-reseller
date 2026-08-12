from mistfall.config import Config
from mistfall.tipos import Listagem

def _comprável(listagem: Listagem, config: Config) -> bool:
    if listagem.item is None or listagem.preco_unitario is None:
        return False
    alvo = config.precos_alvo.get(listagem.item)
    if alvo is None:
        return False
    if listagem.preco_unitario < alvo * config.fracao_sanidade:
        return False  # leitura falha, nao pechincha
    return listagem.preco_unitario <= alvo

def escolher(listagens: list[Listagem], config: Config) -> Listagem | None:
    candidatas = [l for l in listagens if _comprável(l, config)]
    if not candidatas:
        return None
    return max(
        candidatas,
        key=lambda l: (
            config.precos_alvo[l.item] - l.preco_unitario,
            -l.linha,
            -l.coluna,
        ),
    )
