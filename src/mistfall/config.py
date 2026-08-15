import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from mistfall.paralelo import TRABALHADORES_PADRAO
from mistfall.tipos import ItemAlvo

@dataclass(frozen=True)
class Config:
    precos_alvo: dict[ItemAlvo, int]
    trabalhadores: int = TRABALHADORES_PADRAO
    precos_venda: dict[ItemAlvo, int] = field(default_factory=dict)


def _carregar_precos(dados: dict, secao: str, arquivo: Path) -> dict[ItemAlvo, int]:
    valores = dados.get(secao, {})
    if not isinstance(valores, dict):
        raise ValueError(f"{arquivo}: [{secao}] precisa ser uma secao, nao um valor solto")

    precos = {}
    for nome, valor in valores.items():
        try:
            item = ItemAlvo(nome)
        except ValueError as erro:
            conhecidos = ", ".join(alvo.value for alvo in ItemAlvo)
            raise ValueError(
                f"{arquivo}: [{secao}] tem '{nome}', que nao e Item-alvo. "
                f"Os Itens-alvo sao: {conhecidos}"
            ) from erro
        if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
            raise ValueError(
                f"{arquivo}: [{secao}] {nome} = {valor!r}; "
                "o preco tem de ser um inteiro de ouro maior que zero"
            )
        precos[item] = valor
    return precos


def validar_precos_venda(config: Config) -> None:
    faltantes = set(ItemAlvo) - set(config.precos_venda)
    if faltantes:
        nomes = ", ".join(sorted(item.value for item in faltantes))
        raise ValueError(f"faltam Precos de Venda para: {nomes}")

def carregar_config(caminho: str | Path = "config.toml") -> Config:
    """Le os Precos-alvo do arquivo de configuracao.

    Estes numeros decidem gasto de ouro real, entao todo erro sai dizendo qual
    arquivo e qual chave — nunca um KeyError ou ValueError cru, que obriga a
    caçar o problema no traceback.
    """
    arquivo = Path(caminho)
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except OSError as erro:
        raise ValueError(f"nao consegui ler a configuracao em {arquivo}: {erro}") from erro

    try:
        dados = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as erro:
        raise ValueError(f"{arquivo} nao e TOML valido: {erro}") from erro

    if "precos_alvo" not in dados:
        raise ValueError(
            f"{arquivo}: falta a secao [precos_alvo]; sem ela o bot nao sabe "
            "por quanto comprar nenhum Item-alvo"
        )
    precos_alvo = _carregar_precos(dados, "precos_alvo", arquivo)
    precos_venda = _carregar_precos(dados, "precos_venda", arquivo)

    trabalhadores = dados.get("trabalhadores", TRABALHADORES_PADRAO)
    if not isinstance(trabalhadores, int) or isinstance(trabalhadores, bool) or trabalhadores < 1:
        raise ValueError(
            f"{arquivo}: trabalhadores = {trabalhadores!r}; "
            "precisa ser um inteiro maior que zero"
        )

    return Config(
        precos_alvo=precos_alvo,
        trabalhadores=trabalhadores,
        precos_venda=precos_venda,
    )
