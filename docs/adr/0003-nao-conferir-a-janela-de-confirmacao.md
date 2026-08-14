# Não conferir a Janela de Confirmação

O desenho original tratava a Janela de Confirmação como o portão principal contra a pior
falha possível: comprar caro por leitura errada, sem ninguém olhando. Depois de clicar, o
piloto esperava a Janela ser detectada e conferia **quatro** coisas nela — o Ícone, o Preço
Unitário, a Quantidade e o Preço Total — apertando **Esc** a qualquer divergência.

**Essa conferência foi desativada.** Depois do clique o piloto espera um tempo sorteado numa
faixa curta e aperta Espaço. A Janela não é detectada, não é capturada e não é lida.

## Por quê

O portão nunca pagou o que custou.

**Nunca pegou uma Compra ruim.** Dos seis erros de OCR conhecidos do corpus, nenhum teria
sido pego pela conferência do modal. Os `null` e os absurdos são pegos pela regra de preço
exato e pela conferência de ordenação, ambas a montante.

**E derrubou Compras boas duas vezes**, as duas na máquina do jogo:

1. O Ícone reprovava por escala. A varredura de 0,85× a 1,15× de `ler_item_da_janela` é
   palpite calibrado, não medida, e 5% de diferença já derruba a identificação para `None`.
   Deu 100% de falso negativo.
2. Tirado o Ícone, o mesmo aconteceu com os números. A Janela abre com animação e é
   reconhecível como `JANELA_CONFIRMACAO` enquanto ainda se expande — 69 px acima da posição
   final, medido em `images/janela-em-animacao-rede-260.png`. As regiões fixas caíam sobre
   fundo vazio e o OCR devolvia `None` nos três campos. A [#18](https://github.com/lavarini/mistfall-reseller/issues/18)
   registra a medição.

O segundo caso mostrou que o problema não era um portão específico, e sim que **ler o modal
é intermitente**: às vezes lê, às vezes não. Um portão que reprova por não conseguir ler
transforma cada falha de leitura numa Compra perdida.

## O que fica descoberto

Vale registrar, porque a decisão é reversível e o custo dela precisa estar visível:

- **Quantidade diferente de 1.** Nada a montante conhece a Quantidade do modal. Se ele abrir
  com uma Quantidade lembrada de outra Compra, o bot paga por N unidades. É o risco mais
  concreto dos dois.
- **Clique no slot errado.** É falha de geometria, não de OCR, então nenhuma regra da
  varredura alcança.

## O que continua cobrindo

A decisão não deixa o bot cego. O que protege agora vive todo antes do clique, mais uma
conferência depois:

- `decisao._comprável` só aceita preço **exatamente** igual ao Preço-alvo. Leitura baixa não
  vira pechincha, e a janela de erro perigoso encolhe de "todo o intervalo abaixo" para um
  único valor.
- `leilao.conferir_ordenacao` invalida qualquer preço fora da ordem crescente do Leilão.
- **A queda do Ouro tem de bater com o Preço-unitário da Listagem escolhida.** Com o modal
  fora do caminho, esse valor passa a vir da Listagem, assumindo Quantidade 1. É a única
  conferência que sobrou no caminho, e ela acontece **depois** do Espaço: não impede a Compra
  errada, mas não deixa ela passar calada — o desfecho sai `comprou` com a divergência no
  motivo, ou `ouro_nao_caiu`.

## O código continua lá

`_esperar_janela`, `_capturar_a_janela_assentada` e `_conferir_a_janela` seguem em
`src/mistfall/piloto.py`, sem chamador, e continuam exercitados direto pelos testes em
`tests/test_piloto.py`. Estão **estacionados, não esquecidos**: se voltarem ao caminho, têm
de voltar funcionando.

**Não religue a conferência sem resolver antes o que a tirou de lá.** Voltar a validar sem
tornar a leitura do modal confiável só reintroduz o falso negativo. O caminho medido para
isso, caso se decida retomar, está na #18: sondar a posição do modal por template matching
até `dy == 0` custa 0,9 ms por sondagem numa faixa restrita, e discrimina bem (score 0,951
no frame em animação contra 0,449 numa tela que não é modal).
