# Design: vazão do laço e telemetria de Ouro

## Objetivo

Aumentar Compras por minuto no laço do bot. Nesta fase, Ouro é telemetria: sua leitura não
confirma Compra, não aborta a Volta e não retarda a próxima tentativa. Guardas e sinalizadores
de pânico baseados em Ouro ficam para uma etapa posterior, depois que sua regra existir.

O trabalho preserva a leitura dos 12 Preços-unitários em folha única. Não volta às 12 chamadas
individuais ao tesseract.

## Evidência da primeira sessão

A pasta `sessao/` contém 48 Voltas: 36 terminaram como `comprou` e 12 como
`ouro_nao_caiu`. As distribuições medidas nos relatórios foram:

| Etapa | Mediana | Média | Máximo |
|---|---:|---:|---:|
| `pre_voo` | 380,1 ms | 383,2 ms | 502,8 ms |
| `varredura` | 381,9 ms | 406,3 ms | 1.416,9 ms |
| `modal` | 103,2 ms | 102,4 ms | 120,1 ms |
| `confirmacao_do_ouro` | 2.432,9 ms | 3.570,9 ms | 7.303,3 ms |

A primeira varredura pagou aquecimento: 1.416,9 ms. Depois dela, a varredura ficou perto de
380 ms, salvo poucos desvios pequenos.

Nas 36 Compras em que o Ouro caiu dentro da espera, a confirmação custou em média 2.430,3 ms.
Nas 12 em que não caiu, custou em média 6.992,7 ms. O Ouro continuou igual também no começo da
Volta seguinte em todas as 11 falhas que têm sucessora; portanto, os relatórios não mostram
mero débito tardio dentro da janela observada. A espera entre clique e Espaço também não separa
sucesso de falha: ambos aparecem por toda a faixa de aproximadamente 80–120 ms.

Além dos tempos registrados, o caminho saudável paga hoje:

- pausa aleatória de 200–600 ms antes do clique;
- 50 ms depois de mover o mouse e 50 ms segurando o botão;
- 50 ms segurando Espaço;
- 1.000 ms entre Voltas.

Uma Volta com Compra confirmada custa aproximadamente 4,8 s incluindo esses tempos. O desenho
novo mira inicialmente cerca de 0,9–1,3 s por tentativa, mas esse número é hipótese: o valor que
decide vem do Windows, com o jogo aberto e disputando CPU.

## Decisões

### Ouro deixa o caminho crítico

Depois de apertar Espaço, a Volta termina sem `espera_apos_espaco`, sem enquete do Ouro e sem
`teto_espera_ouro`. Não existe mais `ouro_nao_caiu` no caminho vivo.

O desfecho que hoje se chama `COMPROU` passa a se chamar `COMPRA_ENVIADA`. O nome descreve o que
o bot sabe: clique e Espaço foram enviados. Não afirma que o jogo aceitou a Compra. A
contabilidade da sessão também fala em Compras enviadas, não confirmadas, e deixa de calcular
Ouro gasto a partir de uma validação que não existe.

O Ouro ilegível não aborta. A observação é registrada com valor nulo e a análise das Listagens
continua. Exceções de ambiente ou programação continuam sendo erros; somente `None`, que já é o
resultado normal de OCR inconclusivo, vira ausência de telemetria.

### Linha do tempo da sessão

A raiz da sessão recebe `telemetria-ouro.jsonl`, em formato append-only. Cada linha é um objeto
JSON independente com:

- `volta`: número da Volta;
- `instante_monotonico_ms`: tempo monotônico relativo ao início da sessão;
- `horario`: data e hora civil local em ISO 8601;
- `ouro`: inteiro lido ou `null`;
- `origem`: `pre_voo`.

A linha do tempo registra observações, não causalidade. Ela não associa uma queda a uma Compra,
não reabre relatório anterior e não decide sucesso. O `relatorio.json` da Volta mantém a mesma
observação inicial para o diagnóstico daquela Volta, usando o campo `ouro_observado`; os campos
`ouro_antes`, `ouro_depois` e `preco_total_esperado` saem para não preservar uma semântica
enganosa.

A escrita da linha do tempo acontece no laço, que conhece o número da Volta e a raiz da sessão.
O piloto de uma Volta continua sem conhecer sessões.

### Análise concorrente do frame inicial

O frame continua sendo capturado uma vez e salvo antes de qualquer ação. A resolução e o estado
da tela são conferidos primeiro. Se não for a lista do Leilão em Material de Construção, a Volta
mantém o aborto de segurança e nenhum trabalho caro é disparado.

Quando o estado é `LISTA`, duas tarefas independentes usam o mesmo frame imutável:

1. leitura do Ouro;
2. varredura bruta das 12 Listagens, incluindo ícones e a folha de Preços-unitários.

Elas rodam em duas threads. Cada ramo pode chamar um processo do tesseract, mas a varredura
continua usando uma só chamada para a folha inteira. Isso não ressuscita `trabalhadores=4`: a
configuração antiga continua dormente e será tratada separadamente. O executor tem exatamente
dois trabalhos de alto nível e não paraleliza os 12 slots.

Depois que os dois ramos terminam, o piloto confere ordenação, escolhe a Listagem e segue. Uma
falha na análise das Listagens preserva o comportamento seguro atual. Uma leitura inconclusiva
do Ouro produz telemetria nula e não interfere na decisão.

O benchmark precisa comparar o pipeline sequencial e o concorrente. Concorrência só fica ativa
por padrão se reduzir o tempo de parede no Windows com o jogo aberto sem mudar nenhum resultado
do corpus. Se a disputa entre duas instâncias do tesseract eliminar o ganho, mantém-se a remoção
da confirmação bloqueante e deixa-se a análise inicial sequencial.

### Esperas deliberadas

Os novos valores iniciais são:

| Espera | Atual | Nova |
|---|---:|---:|
| pausa antes do clique | 200–600 ms | 50–150 ms |
| entre clique e Espaço | 80–120 ms | 80–120 ms |
| entre Voltas | 1.000 ms | 150 ms |
| depois de Espaço | 2.000 ms + enquete | nenhuma |

A pausa entre clique e Espaço permanece intacta porque a sessão não mostra correlação entre seu
valor e as tentativas perdidas. Mudar essa espera junto com a remoção da validação destruiria a
capacidade de comparar a próxima sessão com esta.

Os 150 ms entre Voltas continuam sendo uma proteção simples contra rotação máxima em tela
inválida. O valor fica no `Ritmo`, injetável nos testes e explícito nas métricas. Espera
adaptativa fica fora deste recorte.

### Métricas

O relatório deixa de agrupar custos diferentes em `pre_voo` e `varredura`. Ele registra:

- `captura_pre_voo`;
- `gravacao_pre_voo`;
- `estado`;
- `ouro`;
- `varredura_total`;
- `itens`;
- `preparo_folha`;
- `tesseract_precos`;
- `conferencia_e_decisao`;
- `pausa_antes_do_clique`;
- `clique`;
- `espera_modal`;
- `espaco`.

Como Ouro e varredura se sobrepõem, a soma das etapas internas não representa o tempo de parede.
O relatório inclui também `analise_inicial_parede`, medido do início dos dois trabalhos até
ambos terminarem. `varredura_total` cobre apenas seu próprio ramo.

A espera entre Voltas pertence ao laço, não ao piloto. A raiz da sessão recebe também
`tempos-do-laco.jsonl`. Depois de cada espera, o laço acrescenta uma linha com a Volta encerrada,
o início monotônico da Volta seguinte, a espera efetiva e o intervalo total entre os dois
inícios. Se o operador parar antes da próxima Volta, não existe linha inventada para ela.

Medições usam relógio monotônico. Horário civil existe apenas para correlacionar a sessão com o
que o operador viu.

## Fluxo

1. O laço inicia a Volta e captura o frame.
2. O piloto salva o frame e identifica o estado.
3. Em `LISTA`, dispara leitura do Ouro e varredura em paralelo.
4. Reúne resultados, registra métricas e escolhe uma Listagem.
5. O laço acrescenta a observação de Ouro à linha do tempo da sessão.
6. Se houver Listagem, espera 50–150 ms, clica, espera 80–120 ms e aperta Espaço.
7. A Volta termina como `COMPRA_ENVIADA`, sem captura ou espera exclusiva posterior.
8. O laço espera 150 ms e começa a próxima Volta.

O fluxo de `NADA_COMPRAVEL` continua acionando Reset. As esperas próprias do Reset não mudam
neste trabalho, porque a sessão traz apenas Voltas com tentativa de Compra e não mede esse
caminho.

## Testes e validação

### Correção

- O corpus inteiro mantém os mesmos Itens-alvo e Preços-unitários no modo sequencial e no
  concorrente.
- Uma leitura de Ouro igual a `None` não aborta nem impede Compra.
- Depois de Espaço, nenhuma captura, leitura de Ouro ou espera de confirmação acontece.
- O desfecho é `COMPRA_ENVIADA`, nunca `COMPROU` ou `OURO_NAO_CAIU`.
- A linha do tempo recebe uma linha JSON válida por observação, inclusive `ouro: null`, e uma
  interrupção não corrompe as linhas anteriores.
- O piloto não escreve diretamente na raiz da sessão.
- Os tempos concorrentes registram tanto cada ramo quanto o tempo de parede.

### Desempenho

Um benchmark reproduzível roda sobre os frames de `sessao/` e compara:

- aquecimento separado da amostra estável;
- pipeline sequencial;
- pipeline concorrente de dois ramos;
- mediana, p95 e máximo;
- igualdade exata dos resultados.

O benchmark local orienta, mas não aprova o padrão. A aceitação final usa uma nova sessão no
Windows com o jogo aberto. A entrega registra:

- tentativas por minuto;
- mediana e p95 de `analise_inicial_parede`;
- mediana e p95 de cada ramo;
- tempo total entre inícios de Voltas;
- comparação sequencial versus concorrente na mesma máquina.

Não há meta rígida inventada antes da medição. O critério é remover completamente a espera
posterior ao Espaço e demonstrar que a concorrência reduz tempo de parede sem regressão do
corpus. Se não reduzir, ela é desligada e os demais ganhos permanecem.

## Ideias deliberadamente adiadas

- sinalizadores de pânico baseados em Ouro;
- regra que associa queda de Ouro a uma ou mais Compras;
- investigação da causa das 12 tentativas perdidas;
- espera adaptativa entre Voltas;
- alteração da faixa de 80–120 ms entre clique e Espaço;
- OCR persistente com `tesserocr` ou outra integração nativa;
- paralelização interna do reconhecimento dos 12 ícones;
- remoção definitiva de `paralelo.py` e `config.trabalhadores`;
- otimização das esperas e capturas do Reset.

Essas ideias ficam documentadas para não serem confundidas com esquecimento. Nenhuma delas deve
entrar escondida no plano desta mudança.
