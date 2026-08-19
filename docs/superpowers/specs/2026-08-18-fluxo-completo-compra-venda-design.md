# Fluxo completo de Compra e Venda

## Objetivo

Adicionar um modo coordenado que alterna entre Compra e Venda de forma adaptativa,
preservando os comandos isolados existentes. O modo novo deve aproveitar os fluxos
de Compra e Venda já validados, coordenando navegação, saúde do ritmo e saldo
estimado do Armazém.

## Modos de operação

- `mistfall-bot`: somente Compra, comportamento atual preservado.
- `mistfall-venda`: somente Venda, comportamento atual preservado.
- novo comando de fluxo completo: coordenador Compra/Venda.

Todos os modos usam F3 para iniciar e F4 para parar. O F2 deixa de ser usado.

## Estado inicial e navegação

O fluxo completo começa com:

- aba Comprar;
- Categoria Item → Material de Construção selecionada;
- filtro de raridade roxo validado; se não estiver ativo, ativá-lo;
- `estoque_estimado = 0` por convenção operacional. O operador deve iniciar sem
  stacks no Armazém ou executar o fluxo de Venda antes.

Ao iniciar uma Venda:

1. clicar na aba Vender;
2. reconhecer que a tela abre no Inventário;
3. trocar para Armazém;
4. começar no segundo Baú, ignorando o primeiro;
5. preencher os slots de Venda disponíveis com stacks exatos de 3.

Após a Venda, retornar para Comprar, restaurar Item → Material de Construção e
garantir novamente o filtro roxo. As demais seleções são consideradas persistentes.

## Modelo de eventos e estado

O coordenador mantém uma máquina de estados com os modos `rapido` e `lento`, além
dos estados operacionais de Compra, preparação de Venda, Venda e retorno à Compra.

Estado mínimo:

- modo do ritmo;
- `estoque_estimado`;
- intenções desde o último Reset;
- Resets desde a última intenção;
- quantidade de intervalos lentos consecutivos;
- Resets consecutivos;
- Compra enviada pendente de confirmação;
- Capacidade de Venda observada.

Eventos de Compra incluem `intencao_detectada`, `compra_enviada`,
`compra_confirmada`, `compra_inconclusiva`, `reset_executado` e
`mensagem_inventario_cheio`. Eventos de Venda incluem unidade listada,
capacidade atualizada e retorno à tela de Compra.

## Ritmo de Compra

Uma intenção existe quando uma Listagem de Item-alvo está no Preço-alvo. Não é
necessário que a Compra seja efetivamente debitada para medir o ritmo.

- 0–2 Resets entre intenções: fluxo rápido.
- 3 Resets entre intenções: intervalo lento.
- três intervalos lentos consecutivos: fluxo lento confirmado.
- cinco Resets consecutivos: fluxo lento imediato.

Não se força Reset após toda Compra: primeiro se aproveita a atualização natural
da lista. O Reset só ocorre quando a lista não oferece nova intenção.

## Confirmação e saldo de Compra

A captura da próxima Volta já ocorre depois da espera normal de atualização da
lista, portanto não é adicionada uma captura exclusiva ao caminho crítico.

- mensagem de sucesso ou queda do Ouro exatamente pelo Preço-unitário: Compra
  confirmada;
- Ouro ilegível ou ambíguo após uma Compra enviada: adicionar uma unidade
  provisória ao saldo;
- mensagem de inventário cheio ou ausência de queda do Ouro confirmada: não
  adicionar unidade;
- uma Venda reconcilia o saldo com o Armazém sempre que os slots puderem ser
  lidos.

O saldo não é zerado depois de uma Venda. Exemplo: 100 unidades, menos 45
listadas, deixam `estoque_estimado = 55`.

## Estratégia de Venda

No modo rápido, não há Venda voluntária: o coordenador continua Comprando até
detectar inventário cheio.

Ao detectar a transição para lento, o coordenador faz uma Venda parcial imediata,
preenchendo o máximo de slots disponíveis naquele momento. Não precisa esperar
45 novas unidades.

No modo lento contínuo, inicia Venda quando `estoque_estimado >= 45`. O limite
representa 15 espaços de 3 unidades e mantém o Armazém relativamente vazio.

Durante a Venda, após cada Listagem:

1. reler `X/Y`;
2. continuar se uma vaga foi liberada por uma Venda externa;
3. se `X == Y` e a capacidade não mudar por aproximadamente 3 segundos, voltar
   para Comprar.

A sessão não tenta esvaziar todo o Armazém: usa a capacidade atual de Venda e
retorna à Compra. Se o fluxo continuar lento, o saldo remanescente provoca uma
nova Venda sem exigir o acúmulo de outras 45 unidades.

## Detecção de inventário cheio

A mensagem visual “O Inventário e o Armazém estão cheios.” é detectada na região
fixa da mensagem. A mensagem visual de sucesso (“Compra realizada, item guardado
no Armazém.”) é outra classe do mesmo detector. A mensagem é um sinal de estratégia,
não um guardrail isolado: a decisão também usa Ouro, saldo estimado e Venda posterior.

## Guardrails e falhas

Guardrails de resolução, estado de tela, aba, Baú, capacidade e transição de
navegação são confirmados por mais de um frame quando aplicável. Falhas
transitórias geram nova tentativa; falhas persistentes encerram o modo completo
com diagnóstico. Os modos isolados preservam seus comportamentos atuais.

Sinais estratégicos ambíguos — toast, Ouro, intenção e quantidade estimada — são
registrados e combinados, não encerram o programa por um único resultado.

## Testes e telemetria

A política pura será testada com sequências de eventos para os regimes rápido e
lento, os limites 3/5, inventário cheio, transição, saldo parcial e capacidade
que muda durante a Venda.

A navegação será testada com Tela e Mão falsas. Os testes atuais dos comandos
isolados permanecem como regressão.

O modo completo registrará intenções, Resets, regime, saldo estimado, unidades
listadas, capacidade observada e motivo de cada transição, permitindo recalibrar
os limites sem alterar os executores.
