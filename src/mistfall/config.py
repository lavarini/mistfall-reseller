import tomllib
from dataclasses import dataclass
from pathlib import Path
from mistfall.tipos import ItemAlvo

FRACAO_SANIDADE_PADRAO = 0.25

@dataclass(frozen=True)
class Config:
    precos_alvo: dict[ItemAlvo, int]
    fracao_sanidade: float

def carregar_config(caminho: str | Path = "config.toml") -> Config:
    """Le os Precos-alvo e a fracao de sanidade do arquivo de configuracao.

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
    if not isinstance(dados["precos_alvo"], dict):
        raise ValueError(f"{arquivo}: [precos_alvo] precisa ser uma secao, nao um valor solto")

    precos_alvo = {}
    for nome, valor in dados["precos_alvo"].items():
        try:
            item = ItemAlvo(nome)
        except ValueError as erro:
            conhecidos = ", ".join(alvo.value for alvo in ItemAlvo)
            raise ValueError(
                f"{arquivo}: [precos_alvo] tem '{nome}', que nao e Item-alvo. "
                f"Os Itens-alvo sao: {conhecidos}"
            ) from erro
        if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
            raise ValueError(
                f"{arquivo}: [precos_alvo] {nome} = {valor!r}; "
                "o Preco-alvo tem de ser um inteiro de ouro maior que zero"
            )
        precos_alvo[item] = valor

    fracao = dados.get("fracao_sanidade", FRACAO_SANIDADE_PADRAO)
    if not isinstance(fracao, (int, float)) or isinstance(fracao, bool):
        raise ValueError(f"{arquivo}: fracao_sanidade = {fracao!r}; esperava um numero")
    if not 0.0 < fracao < 1.0:
        raise ValueError(
            f"{arquivo}: fracao_sanidade = {fracao!r}; "
            "e a fracao do Preco-alvo abaixo da qual a leitura vira suspeita, "
            "entao tem de ficar entre 0 e 1"
        )

    return Config(precos_alvo=precos_alvo, fracao_sanidade=float(fracao))
