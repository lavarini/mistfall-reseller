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

## O que ainda não foi observado

Que a falha **sem** administrador é silenciosa. `SendInput` pode recusar na cara, devolvendo
menos eventos que o pedido — o código transforma isso em `OSError` e sai com código 2 — ou o
input pode ser engolido sem erro nenhum, e aí o bot aborta com "a Janela de Confirmação não
abriu" e sai com código 1.

**Distinguir os dois é o que fecha esta ADR.** O roteiro em
[`docs/execucao-windows.md`](../execucao-windows.md) manda rodar sem administrador de
propósito, registrando o código de saída, exatamente para isso.
