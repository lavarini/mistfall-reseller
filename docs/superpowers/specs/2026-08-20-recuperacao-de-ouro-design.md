# Recuperação de Ouro no Fluxo Completo

**Problema:** [#24](https://github.com/lavarini/mistfall-reseller/issues/24) — com o Ouro
esgotado, `mistfall-completo` gira para sempre: clica em Listagens, não compra nada, não
vende nada e nunca para. Só o F4 encerra.

A causa é que os dois gatilhos de Venda existentes são inalcançáveis nesse estado. O
regime nunca vira lento, porque as Listagens no Preço-alvo continuam aparecendo e cada
Intenção zera os contadores de Reset. E o Inventário nunca enche, porque nada é
comprado.

## O que muda

O Ouro deixa de ser telemetria puramente observacional **no modo coordenado** e passa a
ter um piso. Abaixo dele, o coordenador para de comprar e entra num modo de recuperação
na tela de Venda.

Nos modos isolados nada muda: `mistfall-bot` e `mistfall-venda` preservam estratégia,
defaults e comportamento.

## Uma premissa que precisa ficar escrita

**Vender não devolve Ouro na hora.** Uma Venda cria uma Listagem; o Ouro só chega quando
outro jogador a compra, e aí aparece como Recuperável. Quem converte Recuperável em Ouro
é o Resgatar.

Portanto o modo de recuperação não funciona por vender — funciona por **vender e
resgatar repetidamente** enquanto o mercado consome as Listagens. Um desenho que só
vendesse não recuperaria Ouro nenhum.

## Decisões

| Decisão | Valor | Por quê |
|---|---|---|
| Piso que dispara a recuperação | Ouro < **300** | Acima do maior Preço-alvo (281, códice). Abaixo disso o bot não consegue comprar o Item-alvo mais caro, e continuar varrendo é desperdício. |
| Alvo para voltar a comprar | Ouro ≥ **10.000**, configurável | Sair no piso faria o bot voltar à Venda quase imediatamente. A folga evita o vaivém. |
| Resgatar durante a recuperação | A cada rodada | É o único caminho que converte Listagem vendida em Ouro disponível. |
| Encerrar | Armazém esgotado **e** slots de Venda vazios **e** Ouro abaixo do alvo | Sem estoque e sem Listagem pendente, não há Ouro a caminho. É a única condição genuinamente terminal. |

## Desenho

### Política — `fluxo.py`

Ganha um evento e uma ação:

- `EventoFluxo.ouro_abaixo_do_piso()` — emitido pelo coordenador, que faz a comparação.
  O número fica na configuração, não na política: a política continua pura e sem
  conhecer preços.
- `AcaoFluxo.VENDER_POR_OURO_BAIXO` — separada de `VENDER_POR_INVENTARIO_CHEIO` e de
  `VENDER_POR_FLUXO_LENTO` para a telemetria distinguir os três motivos, como já faz
  com os outros dois.

### Coordenador — `ciclo_completo.py`

Lê o Ouro de cada Volta (já disponível em `Resultado.ouro_observado`) e emite o evento
quando cai abaixo do piso. Ao receber `VENDER_POR_OURO_BAIXO`, navega para a Venda e
entra no laço de recuperação:

1. `executar_venda_parcial(...)` — lista o que couber
2. lê o Ouro de um frame novo (`ler_ouro` funciona na tela de Venda; medido em quatro
   fixtures reais)
3. Ouro ≥ alvo → volta para Comprar e retoma o ciclo normal
4. Armazém esgotado **e** capacidade ocupada zero → encerra com desfecho e motivo
5. senão → resgata se o botão estiver dourado, espera, repete

O laço vive no coordenador, e não dentro de `ciclo_venda`, por um motivo concreto: o
`_esperar_vaga` que serviria de base é compartilhado com `mistfall-venda`, e mexer nele
mudaria o modo isolado. Manter a permanência no coordenador deixa a Venda intocada.

### Configuração

`config.toml` ganha `ouro_alvo_recuperacao` (default 10000) e `piso_ouro` (default 300).

## Interação com a #25

A [#25](https://github.com/lavarini/mistfall-reseller/issues/25) registra que a
supressão do livelock só cobre `CAPACIDADE_CHEIA`: uma Venda que volta com
`ARMAZEM_ESGOTADO` e zero unidades não suprime o gatilho por saldo.

O gatilho novo entra no mesmo ponto e reabriria o mesmo laço. **Os dois se resolvem
juntos:** a supressão passa a valer para qualquer Venda que não liste unidade nenhuma,
qualquer que seja o desfecho.

## Fora de escopo

- Ler o valor numérico do Recuperável. O bot só detecta se o botão está dourado, e isso
  basta para decidir clicar.
- Resgatar dentro de `mistfall-venda`. O modo isolado segue sem resgatar.
- Piso de Ouro no `mistfall-bot`. A [#8](https://github.com/lavarini/mistfall-reseller/issues/8)
  continua aberta para isso.

## Testes

Contra dublês para o laço de recuperação, e contra fixtures reais para a leitura de Ouro
na tela de Venda. Os casos que precisam falhar sem o código novo:

- Ouro abaixo do piso dispara Venda mesmo com regime rápido e Inventário vazio
- o laço não sai enquanto o Ouro estiver abaixo do alvo
- Armazém esgotado com capacidade zero encerra, em vez de girar
- uma Venda sem unidades listadas suprime o gatilho por saldo, qualquer que seja o
  desfecho (#25)
- `mistfall-venda` e `mistfall-bot` não mudam de comportamento
