# Mistfall Reseller

Bot que observa a Casa de Leilão do jogo Mistfall e compra automaticamente itens-alvo
quando o preço está no valor desejado, com o objetivo de revendê-los com lucro.

## Language

**Leilão**:
A interface de mercado do jogo (tela "LEILÃO"), com as abas Comprar, Vender e Registro
de Trocas. O bot opera na aba Comprar.
_Avoid_: Mercado, Loja, Auction House.

**Listagem**:
Uma oferta de venda individual dentro do Leilão, composta por ícone, nome do item,
estoque e preço unitário. A tela mostra várias Listagens em duas colunas.
_Avoid_: Oferta, Anúncio, Item (o Item é o conteúdo, a Listagem é a oferta).

**Item-alvo**:
Um dos itens que o bot monitora para comprar (Broche, Adaga, Lanterna, Orbe, Dragão,
Rede, Códice). Cada Item-alvo tem um Preço-alvo associado.
_Avoid_: Item desejado, Produto.

**Preço-alvo**:
O preço unitário exato pelo qual compramos um Item-alvo. O bot compra uma Listagem
quando o Preço-unitário dela é **igual** ao Preço-alvo — nem acima, nem abaixo.
Os Itens-alvo não ficam abaixo desse valor: ele é chão de mercado, e um preço menor
é leitura errada, não pechincha.
_Avoid_: Preço-limite, Valor, Preço-máximo (todos aliases; usar Preço-alvo).

**Preço-unitário**:
O custo em ouro de uma unidade da Listagem, exibido à direita com o ícone de moeda.
_Avoid_: Preço, Custo.

**Estoque**:
A quantidade de unidades disponíveis em uma Listagem (ex.: `x800`).
_Avoid_: Quantidade disponível.

**Compra**:
A ação de adquirir unidades de uma Listagem. Fluxo: clicar na Listagem abre a Janela de
Confirmação (após um pequeno delay); apertar Espaço aciona o botão "Comprar". Sempre
compramos 1 unidade e sempre pelo Preço-unitário exibido na Listagem (nunca por outro
valor). Por ora compramos 1 unidade por Compra, para manter a interação com a Janela de
Confirmação simples na v1 — alterar a Quantidade é interação nova e não testada, e não
queremos isso no mesmo passo em que estamos provando a detecção. Velocidade não é o motivo:
ritmo humano basta, e comprar mais unidades por Compra é candidato natural a v2.
_Avoid_: Transação, Aquisição.

**Janela de Confirmação**:
O modal "Comprar" que abre ao clicar numa Listagem. Mostra o item, o Preço-unitário, a
Quantidade e o botão Comprar (acionado por Espaço). Cobre a lista de fundo, então o bot
não consegue varrer Listagens enquanto ela está aberta.
_Avoid_: Modal, Popup, Dialog.

**Tendência de Mercado**:
Painel informativo dentro da Janela de Confirmação com o book de preços (Menor Preço,
Preço Médio) do item. Fora do escopo da v1 — não influencia a decisão de Compra, mas
será útil para a estratégia de revenda no futuro.
_Avoid_: Book, Order book, Histórico.

**Ouro**:
A moeda do jogo, exibida no topo direito do Leilão. Cada Compra reduz o Ouro disponível.
_Avoid_: Dinheiro, Saldo, Moeda.

**Categoria**:
Agrupamento de itens no menu lateral do Leilão (Arma, Armadura, Item → Consumível,
Material de Construção, Material de Forja, Chave, etc.). Os Itens-alvo ficam em
Material de Construção.
_Avoid_: Filtro, Aba (as abas são Comprar/Vender/Registro de Trocas).

**Reset**:
A ação de forçar a recarga da lista trocando para outra Categoria e voltando para
Material de Construção. Só é necessário quando não há nenhum Item-alvo comprável na
tela — uma Compra (ou tentativa de Compra) já recarrega a lista automaticamente.
_Avoid_: Refresh, Recarga, Atualizar.

**Volta**:
Uma iteração do laço de Compra: uma varredura e, conforme o desfecho, uma Compra ou um
Reset. A sessão do bot é uma sequência de Voltas, e cada uma guarda a própria pasta de
prints e relatório.
_Avoid_: Iteração, Ciclo, Rodada.

**Interruptor**:
O par de teclas com que o operador liga e desliga o bot. Na Compra e na Venda, F3 começa e F4 para.
É a terceira fronteira de IO, ao lado da Tela e da Mão. Na Compra, o F4 é consultado antes de cada clique. Não é consultado entre o clique e o
Espaço, onde já não há o que abortar, nem existe espera pós-Espaço: o Ouro é apenas
telemetria observacional do frame inicial. Na Venda, o F4 é consultado antes de cada Venda
e antes da troca de Baú.
_Avoid_: Hotkey, Atalho, Tecla de pânico.

**Venda**:
A ação de criar uma Listagem a partir de um stack de 3 unidades de um Item-alvo no
Armazém. Uma Venda consome uma posição da Capacidade de Venda. O bot preenche o Preço
de Venda e a Quantidade 3 na Janela de Confirmação e clica em "Listar para Venda".
_Avoid_: Transação, Publicação.

**Preço de Venda**:
O Preço-unitário fixo pelo qual um Item-alvo é listado. Vem de `[precos_venda]` e não
é inferido da Tendência de Mercado nem relido da Janela de Confirmação.
_Avoid_: Preço sugerido, Menor preço.

**Capacidade de Venda**:
O par `X/Y` mostrado em "Listar para Venda X/Y": `X` são as posições ocupadas e `Y`
é o limite atual do NPC. Ambos são lidos da tela porque o limite muda com o nível do
NPC e pode resetar entre seasons.
_Avoid_: Limite configurado, Vagas fixas.

**Baú**:
Uma das quatro abas do Armazém abaixo do título "Armazém". O ciclo de Venda começa no
Baú selecionado, processa sua imagem uma vez e avança somente para a direita.
_Avoid_: Stash, Página, Guia.

**Filtro Roxo**:
O filtro de raridade roxa da lista do Leilão, ativado por um clique fixo ao lado da
Categoria. O Fluxo Completo garante essa ativação antes de cada Compra e depois de
cada Venda.
_Avoid_: Filtro de raridade, Filtro épico.

**Intenção**:
Uma Listagem de Item-alvo visível no Preço-alvo. Existe independente de a Compra ter
sido enviada ou confirmada — é a unidade que o Fluxo Completo usa para medir ritmo.
_Avoid_: Oportunidade, Sinal de compra.

**Regime do Fluxo**:
O ritmo — rápido ou lento — em que o Fluxo Completo está operando, medido pela
cadência de Resets entre Intenções. Começa rápido; vira lento após três intervalos de
três Resets entre Intenções seguidos, ou após cinco Resets seguidos sem nenhuma
Intenção. Só o regime lento dispara Venda por saldo — o regime rápido só vende quando
o Inventário e o Armazém acusam estar cheios.
_Avoid_: Modo (reservado para os comandos `mistfall-bot`/`mistfall-venda`/
`mistfall-completo`), Velocidade.

**Estoque estimado**:
A contagem interna que o Fluxo Completo mantém do que está no Armazém: soma 1 a cada
Compra confirmada ou inconclusiva e subtrai as unidades de cada Venda. Nunca é relido
do Armazém depois do estado inicial. Quando o Ouro sai ilegível com uma Compra
pendente, a soma acontece do mesmo jeito — uma unidade otimista, para não perder o
sinal — e nunca é revista depois. Em sessões longas com OCR de Ouro instável, isso
pode deixar o Estoque estimado divergir do Armazém real; não há reconciliação
persistente implementada.
_Avoid_: Saldo, Inventário (o Inventário é a aba do jogo).

**Fluxo Completo**:
O modo coordenado por trás de `mistfall-completo`, que alterna Compra e Venda sozinho
sem intervenção manual entre abas. Começa em Comprar, Item → Material de Construção,
com o Filtro Roxo garantido e o Estoque estimado assumido em zero.
_Avoid_: Modo automático, Modo misto.
