# Desenvolver no macOS, executar no Windows

O jogo roda num PC Windows separado, então o bot é executado lá. Porém o desenvolvimento
acontece num Mac. Decidimos separar a lógica de **visão** (captura, template matching de
ícones, OCR de preço), que é testável offline contra os prints já capturados, da camada de
**IO** (captura de tela ao vivo e injeção de clique/Espaço), que é específica de Windows.

Consequência: toda a detecção pode ser desenvolvida e testada no Mac contra imagens
estáticas; só a camada de IO precisa de uma máquina Windows para rodar de verdade. Jogos
costumam ignorar input sintético comum, então a injeção no Windows provavelmente exigirá
pydirectinput/AHK/Interception em vez de pyautogui puro.

## Como isso se materializou

A fronteira virou dois protocolos, `Tela` e `Mao`, com uma implementação real e um par de
dublês. O ganho foi maior do que o previsto: **o orquestrador inteiro é exercitado no macOS**,
com a `TelaFalsa` servindo um roteiro de PNGs e a `MaoFalsa` gravando o que lhe pediram. Só
`src/mistfall/perifericos/windows.py` não roda aqui — e ele não tem lógica nenhuma, só traduz
chamada em syscall.

**A escada de escalonamento prevista acima não foi necessária.** Não entrou pydirectinput, nem
AHK, nem Interception: `ctypes` da biblioteca padrão chamando `SendInput` bastou. O que
importa não era a biblioteca, e sim dois detalhes:

- **`KEYEVENTF_SCANCODE`, não virtual-key.** Jogos leem scancode de hardware e ignoram evento
  de tecla virtual. É essa a razão real de scripts "funcionarem no Bloco de Notas e não no
  jogo" — não a escolha de biblioteca. Espaço é `0x39`, Esc é `0x01`.
- **Rodar como administrador.** O UIPI do Windows impede um processo de integridade menor de
  enviar input a uma janela de integridade maior. O jogo roda elevado.

A evidência que sustentou essa aposta é anterior ao projeto: o Mini Mouse Macro dirige o jogo
quando roda elevado, e ele usa `SendInput` como qualquer um dos candidatos da escada.

## O que a execução na máquina do jogo mostrou

A pergunta era distinguir se a falha **sem** administrador é silenciosa. A execução respondeu
outra coisa, mais útil: **administrador não é a variável.**

Observado, com o jogo aberto e o Leilão na tela:

- Com e **sem** administrador, o comportamento é **idêntico**.
- O `SendInput` **aceita** os eventos nas duas. Se recusasse, `_enviar` levantaria `OSError` e
  a saída seria código 2 — não foi o que aconteceu.
- O cursor **se move** e para na Listagem certa. A conversão de pixel para coordenada absoluta
  está correta, e o movimento sintético chega ao jogo.
- O clique **não acontece**. A Janela de Confirmação não abre, e o bot aborta.

O Windows está aceitando o input, e o jogo enxerga o movimento. Então o UIPI não é o que
bloqueia, e a linha "rodar como administrador" acima **não se sustenta como explicação deste
sintoma**. Ela não foi refutada como requisito geral — só deixou de ser a causa aqui.

Sobrou uma única diferença entre o movimento, que funciona, e o clique, que não: a **forma**.
`LEFTDOWN` e `LEFTUP` viajavam no mesmo lote de `SendInput`, então o botão ficava apertado por
tempo zero. Um app comum recebe as duas mensagens pela fila e enxerga o clique inteiro; um jogo
costuma **amostrar** o estado do mouse uma vez por quadro, e entre dois quadros o botão desceu
e subiu. Na hora de amostrar, está solto.

Isso acrescenta um terceiro detalhe à lista acima, da mesma família dos outros dois — a
distância entre mandar o evento e o alvo perceber o evento:

- **O clique precisa de duração.** Pressionar e soltar vão em lotes separados, com espera entre
  eles. O padrão é 50 ms, ~3 quadros a 60 fps.

## O que a execução seguinte confirmou

**O clique com duração resolve.** A execução guardada em `execucao-real/` clicou numa
Listagem e a Janela de Confirmação abriu — o `01-janela.png` é a evidência. A correção
derivada por eliminação acima está certa.

Naquela execução, o Espaço ainda não tinha sido observado: ela abortou lendo o modal, e
nenhuma Compra havia completado. A
[#9](https://github.com/lavarini/mistfall-reseller/issues/9) existia para responder a essa
pergunta, e `OURO_NAO_CAIU` era um código de saída próprio. Isso é histórico: o Espaço foi
posteriormente incorporado ao caminho vivo e a confirmação pelo Ouro foi removida.

Hoje, `COMPRA_ENVIADA` é o desfecho depois de enviar clique e Espaço. O Ouro observado no
frame inicial é telemetria, não confirmação; não há leitura nem espera pós-Espaço, e
`OURO_NAO_CAIU` não é mais um desfecho do código atual.

Se administrador é necessário para alguma coisa também segue em aberto.
