# Estabilização pós-venda

## Contexto

Após confirmar um anúncio, o cursor permanece sobre a região do botão
`Listar`. Quando o modal fecha, essa mesma coordenada passa a pertencer ao
painel do Armazém. Nas sessões reais isso deixou um item subjacente ativo e,
em outra execução, a interface terminou na aba Inventário. O fluxo então não
reconheceu a tela normal de Venda e abortou, apesar de o anúncio ter sido
aceito. Na `sessao-venda-3`, o décimo anúncio elevou a capacidade para `10/12`,
mas o bot encerrou contabilizando apenas nove vendas.

`Esc` não pode ser usado para recuperar a interface porque encerra a execução
no jogo.

## Objetivo

Depois de cada confirmação, retirar o cursor da área interativa e garantir que
o painel direito esteja no Armazém antes de continuar. Caso seja necessário
voltar do Inventário para o Armazém, o fluxo deve retomar a lista de candidatos
já calculada para o baú atual, sem nova leitura dos itens.

## Desenho

### Movimento sem clique

A fronteira `Mao` ganhará a operação `mover(x, y)`. A implementação Windows
enviará somente o movimento absoluto do mouse, sem eventos de botão. O método
`clicar` continuará com o comportamento atual e poderá reutilizar internamente
a mesma conversão de coordenadas.

O fluxo usará como ponto neutro fixo `(1620, 1100)`, na resolução suportada de
2560x1440. Esse ponto fica abaixo da coluna vertical de filtros do Armazém e no
espaço entre a listagem de anúncios e a grade de itens.

Imediatamente após o clique no botão `Listar`, antes de capturar quadros para
confirmar o fechamento do modal, o cursor será movido ao ponto neutro. O ponto
não será clicado.

### Identificação da aba direita

A visão distinguirá três estados do painel direito:

- Armazém selecionado;
- Inventário selecionado;
- estado ilegível.

A identificação será baseada na aparência selecionada dos títulos existentes,
usando capturas reais como regressão. A posição do título `Armazém` será exposta
como coordenada de clique somente para a recuperação.

### Recuperação

Após a confirmação de cada anúncio:

1. mover o cursor ao ponto neutro;
2. aguardar a tela normal de Venda;
3. se o Armazém estiver selecionado, concluir a venda normalmente;
4. se o Inventário estiver selecionado, clicar em `Armazém`, mover novamente o
   cursor ao ponto neutro e aguardar a tela normal de Venda;
5. se o estado continuar ilegível até o tempo limite, abortar e preservar a
   captura diagnóstica.

A recuperação pertence à execução de uma venda individual. Seu resultado só
será `VENDEU` quando a interface estiver novamente pronta no Armazém.

### Continuidade da varredura

O ciclo continuará usando a lista `candidatos` criada uma única vez para o baú
atual. A recuperação não chamará `varrer_armazem`, não alterará o baú
selecionado e não recalculará posições. Depois de voltar ao Armazém, o laço
prosseguirá no próximo candidato ainda não processado.

### Falhas e limites

- Nenhum `Esc` será enviado.
- Nenhum clique será feito no ponto neutro.
- A recuperação não avançará para outro baú.
- Se o clique em `Armazém` não restaurar uma tela legível dentro do limite de
  espera existente, a sessão abortará em vez de tentar cliques adicionais.
- Esta mudança não altera preços, quantidades nem a randomização dos cliques
  nos itens e no botão `Listar`.

## Testes

Os testes cobrirão:

- movimento Windows emitindo apenas `MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE`;
- clique mantendo sua sequência atual de mover, pressionar e soltar;
- cursor movido ao ponto neutro imediatamente após clicar em `Listar`;
- venda concluída diretamente quando o Armazém já está selecionado;
- detecção de Inventário, clique em `Armazém`, novo movimento neutro e retomada;
- aborto quando o painel direito permanece ilegível;
- ciclo retomando o próximo elemento da mesma lista em cache, sem nova
  varredura do baú.

As capturas de `sessao-venda-2` e `sessao-venda-3` servirão como referência
para os estados reais, sem serem adicionadas automaticamente ao repositório.
