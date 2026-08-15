# Design: randomização de todos os cliques da Compra

## Objetivo

Evitar que o fluxo de Compra clique sempre nas mesmas coordenadas. Todos os cliques desse fluxo
passam a variar dentro de áreas centrais conservadoras e específicas para cada alvo, sem alterar
a decisão de Compra, os tempos, as capturas ou o fluxo de Venda.

“Todos os cliques da Compra” significa:

1. a Listagem escolhida;
2. a Categoria alternativa do Reset, Forja ou Chave;
3. o retorno do Reset para Material de Construção.

Teclas não são cliques: Espaço, F2 e F3 permanecem inalterados.

## Áreas seguras

Os limites são inclusivos nos dois eixos.

### Listagem

A geometria existente devolve a caixa da Listagem com `caixa_slot(linha, coluna)`. O ponto atual
é o centro inteiro dessa caixa:

```text
cx = (x0 + x1) // 2
cy = (y0 + y1) // 2
```

O clique passa a ser sorteado em:

```text
X: cx - 20 .. cx + 20
Y: cy - 26 .. cy + 26
```

A Listagem mede 1011×154 px. Essa área de 41×53 px fica longe das bordas, das Listagens vizinhas
e da divisão entre colunas. Ela é deliberadamente conservadora e usa a mesma meia-largura e
meia-altura escolhidas para o clique no stack da Venda.

### Categorias do Reset

As coordenadas existentes em `mistfall.geometria` continuam sendo os centros de Material de
Construção, Material de Forja e Chave. Para qualquer uma delas, o clique passa a ser sorteado em:

```text
X: cx - 60 .. cx + 60
Y: cy - 18 .. cy + 18
```

As linhas de Categoria têm centros separados por 72 px. A variação vertical total ocupa 37 px,
deixando 35 px entre as áreas de linhas vizinhas. A variação horizontal fica dentro da faixa
central do menu usada pelo reconhecimento da Categoria.

## Arquitetura

### Helper compartilhado

Um novo módulo `mistfall.cliques` contém uma função pura:

```python
AreaClique = tuple[int, int, int, int]

def sortear_ponto(
    area: AreaClique,
    sorteio: random.Random,
) -> tuple[int, int]:
    ...
```

Ela recebe `(x0, y0, x1, y1)` e sorteia X e Y com `randint`, portanto inclui os quatro limites.
Não conhece Listagem, Categoria, Compra ou Venda. Também não consulta o estado global de
`random`.

As funções de geometria constroem as áreas; o helper somente sorteia um ponto dentro delas. A
separação evita colocar aleatoriedade dentro de `MaoWindows`, que não conhece o alvo do clique e
não poderia decidir uma margem segura.

O fluxo de Venda não muda neste trabalho. Seu plano de randomização pode consumir o mesmo helper
quando for implementado, mas nenhuma assinatura ou teste da Venda entra nesta entrega.

### Gerador da sessão

`executar_ciclo` já recebe `sorteio: random.Random | None`. Quando o argumento for `None`, o
ciclo cria exatamente uma instância de `random.Random()` antes da primeira Volta. Essa mesma
instância é repassada para:

- `executar`, que já a usa na escolha entre Listagens empatadas e nas esperas aleatórias;
- `resetar_categoria`, que passa a usá-la nos dois cliques do Reset.

Uma sessão não recria o gerador a cada Volta nem a cada Reset. Isso produz variação contínua e
permite reproduzir uma sessão de teste com uma semente.

`executar` e `resetar_categoria` continuam utilizáveis isoladamente. Se chamados sem gerador,
cada função cria uma instância local de `random.Random()` uma vez no começo da chamada.

## Fluxo de dados

### Compra com Listagem

1. O ciclo obtém ou cria o gerador da sessão.
2. O piloto usa o gerador para decidir entre candidatos empatados.
3. Calcula o centro da caixa da Listagem escolhida.
4. Constrói a área `±20/±26`.
5. Sorteia um ponto imediatamente antes do clique.
6. A Mão clica nesse ponto e o restante do fluxo permanece igual.

O modo simulado encerra antes de construir ou sortear o ponto. Assim ele continua sem clique e
não consome aleatoriedade de coordenada que nunca será usada.

### Reset

1. O ciclo entrega o mesmo gerador a `resetar_categoria`.
2. O Reset escolhe Forja ou Chave pela alternância existente; isso não vira sorteio.
3. Constrói e sorteia a área `±60/±18` da Categoria alternativa e clica.
4. Depois da conferência existente, constrói e sorteia a área de Material de Construção e clica.
5. As capturas, esperas e conferências das duas transições permanecem iguais.

Se a primeira transição falhar, o comportamento atual é preservado: o Reset ainda tenta voltar
para Material de Construção. Portanto, os dois pontos são sorteados quando seus respectivos
cliques são alcançados, independentemente do resultado visual intermediário.

## Erros e segurança

- Áreas são constantes derivadas de centros e margens conhecidas; não entram em configuração.
- A função pura valida `x0 <= x1` e `y0 <= y1`. Área invertida levanta `ValueError` antes de
  tocar a Mão.
- Coordenadas sorteadas não alteram resolução, OCR, decisão ou guardas da Compra.
- O Interruptor continua sendo consultado nos mesmos pontos. Não se acrescenta consulta entre
  clique e Espaço.
- Nenhuma coordenada sorteada é persistida em `relatorio.json` ou nos JSONL da sessão.
- A faixa temporal e o número de chamadas de clique permanecem os mesmos.

## Testes

### Helper

- inclui os quatro limites usando um dublê controlado de `randint`;
- rejeita área invertida em X ou Y;
- não usa `random.seed` nem funções do módulo global.

### Listagem

- toda Compra enviada produz um clique dentro de `cx±20`, `cy±26`;
- sementes variadas produzem mais de um ponto;
- a mesma semente reproduz o ponto;
- alterar o estado global de `random` não muda execução com gerador injetado;
- modo simulado não clica e não sorteia coordenada;
- nenhum ponto sai da caixa da Listagem escolhida.

### Reset

- Forja, Chave e Material de Construção usam `cx±60`, `cy±18`;
- os dois cliques recebem a mesma instância injetada;
- sementes variadas produzem pontos diferentes;
- a mesma semente reproduz a sequência dos dois cliques;
- continuam existindo exatamente dois cliques por tentativa de Reset;
- sucesso e falha das transições mantêm a semântica atual.

### Ciclo

- uma única instância é repassada a todas as Voltas e Resets da sessão;
- a alternância Forja/Chave permanece determinística e independente do sorteio;
- nenhum teste exige coordenada central exata onde agora existe uma área segura;
- a suíte do fluxo de Venda continua verde sem modificação.

## Documentação operacional

O README passa a dizer que todos os cliques da Compra variam dentro de áreas centrais seguras:
Listagens e Categorias do Reset. Deve distinguir isso do sorteio entre Listagens empatadas e das
esperas aleatórias, que já existiam.

Não se adiciona opção de CLI ou chave de configuração. O operador não precisa calibrar essas
áreas nesta etapa.

## Fora de escopo

- alterar o plano ou o código da randomização dos cliques da Venda;
- randomizar Espaço, F2, F3 ou qualquer duração de tecla/mouse;
- ampliar as áreas além das margens aprovadas;
- pesos, distribuições não uniformes ou curvas gaussianas;
- persistir coordenadas sorteadas;
- configurar margens por TOML ou CLI;
- randomizar a alternância Forja/Chave;
- mudar esperas, OCR, decisão, Reset ou regras de segurança.
