# Randomização segura dos cliques da Venda

## Objetivo

Variar levemente a posição dos cliques que escolhem um Item-alvo no Armazém e que
confirmam "Listar para Venda". A variação reduz a repetição mecânica sem aproximar o cursor
das bordas das áreas clicáveis.

Esta mudança vale somente para a Venda. O fluxo de Compra está em refatoração separada e
fica explicitamente fora do escopo.

## Escopo

Somente dois cliques passam a variar:

1. o clique no stack de quantidade 3 do Item-alvo;
2. o clique no botão "Listar para Venda" da Janela de Confirmação.

Os cliques nos Baús, no campo Preço de Venda e no campo Quantidade continuam usando as
coordenadas fixas atuais.

Como correção de dado no mesmo contexto de Venda, o Preço de Venda da Adaga passa de 240
para 239. O Preço-alvo de Compra da Adaga não muda.

## Áreas seguras

O projeto permanece acoplado à resolução 2560×1440, conforme ADR-0002. Por isso as áreas
seguras são constantes no código, sem novas opções no `config.toml`.

### Slot do Armazém

Cada slot mede 83×106 pixels. A área segura é um retângulo de 41×53 pixels centrado no
slot. Dado o centro inteiro `(cx, cy)` já calculado pela geometria atual, os limites
inclusivos são `cx - 20 .. cx + 20` e `cy - 26 .. cy + 26`. Portanto eles acompanham a
linha e a coluna do candidato sem chegar às extremidades.

### Botão "Listar para Venda"

Na fixture real da Janela de Confirmação, a área segura fixa é:

- X entre 1500 e 1900, inclusive;
- Y entre 1010 e 1040, inclusive.

Esse retângulo fica integralmente dentro do botão e mantém uma margem ampla das bordas.

## Sorteio e dependências

Uma função pura recebe um retângulo seguro e uma instância de `random.Random`, sorteando X
e Y uniformemente e de forma independente dentro dos limites inclusivos.

O fluxo de uma Venda recebe o gerador por injeção. O ciclo de Venda cria `random.Random()`
por padrão e repassa a mesma instância para cada Venda da sessão. Testes podem fornecer uma
instância com semente fixa, tornando toda a sequência reproduzível sem depender do estado
global de `random`.

Cada ação sorteia um ponto novo. O deslocamento do clique no Item-alvo não é reaproveitado
no botão final nem em Vendas posteriores.

## Fluxo e falhas

O sorteio ocorre imediatamente antes de cada um dos dois cliques. Ele não provoca captura
adicional, não altera a detecção da Janela de Confirmação e não muda os tetos de espera.

Os desfechos atuais permanecem iguais: se a Janela não abrir ou não fechar, a Venda aborta
com seu motivo e suas evidências. As coordenadas sorteadas não entram no relatório nesta
versão, pois não são necessárias para decidir o desfecho nem diagnosticar as transições de
tela.

## Testes

Os testes devem demonstrar que:

- o ponto de um Item-alvo sempre pertence à metade central do seu slot;
- o ponto final sempre pertence ao retângulo seguro do botão;
- uma amostra com várias sementes produz mais de uma coordenada em cada área;
- a mesma semente reproduz a mesma sequência de cliques;
- alterar o estado global de `random` não altera uma execução com gerador injetado;
- Baús, Preço de Venda e Quantidade continuam usando coordenadas fixas;
- os comportamentos de sucesso e aborto da Venda permanecem inalterados.

## Fora do escopo

- qualquer mudança no fluxo de Compra;
- randomização de tempo adicional;
- randomização de cliques nos Baús ou nos campos de input;
- configuração das margens pelo operador;
- persistência das coordenadas sorteadas nos relatórios.
- qualquer alteração em `[precos_alvo]`, inclusive o Preço-alvo da Adaga.
