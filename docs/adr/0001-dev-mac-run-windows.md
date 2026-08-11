# Desenvolver no macOS, executar no Windows

O jogo roda num PC Windows separado, então o bot é executado lá. Porém o desenvolvimento
acontece num Mac. Decidimos separar a lógica de **visão** (captura, template matching de
ícones, OCR de preço), que é testável offline contra os prints já capturados, da camada de
**IO** (captura de tela ao vivo e injeção de clique/Espaço), que é específica de Windows.

Consequência: toda a detecção pode ser desenvolvida e testada no Mac contra imagens
estáticas; só a camada de IO precisa de uma máquina Windows para rodar de verdade. Jogos
costumam ignorar input sintético comum, então a injeção no Windows provavelmente exigirá
pydirectinput/AHK/Interception em vez de pyautogui puro.
