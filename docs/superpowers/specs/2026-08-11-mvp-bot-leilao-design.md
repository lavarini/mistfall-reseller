# Design do MVP — Bot de Compra no Leilão

Data: 2026-08-11
Épico: [#1](https://github.com/lavarini/mistfall-reseller/issues/1)

## Contexto e premissas

O bot observa a Casa de Leilão do Mistfall e compra Itens-alvo cujo Preço-unitário esteja
no valor desejado, para revenda posterior. O vocabulário deste documento é o do
[CONTEXT.md](../../../CONTEXT.md).

Quatro premissas, levantadas na sessão de brainstorming, moldam todo o resto:

1. **A tese econômica já está validada na mão.** O usuário já faz essa operação
   manualmente e ela funciona. O MVP não precisa provar que dá lucro, nem descobrir quais
   são os Preços-alvo certos — isso já se sabe por experiência. Por isso Tendência de
   Mercado e a revenda automatizada ficam fora da v1 sem prejuízo.
2. **Velocidade não é requisito.** Ritmo equivalente ao de um humano basta. Latência é
   orçamento livre, e pode ser gasta em conferência, espera e nova tentativa.
3. **Rodar sozinho é o produto.** O objetivo é deixar o bot operando sem supervisão. Isso
   promove os guardrails de acessório a essencial.
4. **A pior falha é comprar caro por leitura errada.** Um OCR que lê 250 como 25 faz o bot
   achar que está barato e torrar o Ouro enquanto ninguém olha. O design é conservador:
   na dúvida, não compra.

### Viabilidade: já resolvida

A pergunta "dá para dirigir o jogo?" era o risco que inviabilizaria tudo, e ela já está
respondida por evidência que o usuário possuía antes do projeto começar:

| Metade | Evidência | Veredito |
|--------|-----------|----------|
| Input | Mini Mouse Macro funciona rodando como administrador | Funciona. Usa `SendInput`, o mesmo caminho de `pydirectinput`/`pyautogui`. |
| Captura | Print Screen produziu PNGs 2560×1440 limpos | Funciona. Fosse *fullscreen exclusive* protegido, viria quadro preto. |

O detalhe do **modo administrador** é a explicação, não um acaso: o UIPI do Windows impede
um processo de integridade menor de enviar input a uma janela de integridade maior. O jogo
roda elevado, então um Python não-elevado é ignorado silenciosamente, sem erro. Elevado,
funciona. **Todo o bot precisa rodar como administrador.**

Consequência: a escada de escalonamento prevista no ADR-0001 (pyautogui → pydirectinput →
AHK → Interception) provavelmente é desnecessária. Começamos no primeiro degrau.

### Risco não-técnico

O jogo tem anti-cheat. Anti-cheat costuma detectar *comportamento* — timing metronômico,
precisão sobre-humana — em vez de bloquear a API de input. A mitigação natural é ritmo
humano com variação, que já é requisito por outro motivo (premissa 2). O risco de conta
existe e é do usuário calibrar.

## Escopo do MVP

A mudança estrutural em relação ao plano publicado é **inverter o tracer bullet**: em vez
de começar pela visão sobre imagem estática, atravessar todas as camadas com a visão
substituída por uma constante.

### Fatia 0 — Compra de ponta a ponta com coordenada chumbada

Script rodando como administrador no Windows: captura a tela → confirma que a imagem é
utilizável → clica numa coordenada fixa de Listagem → espera → aperta Espaço → captura de
novo e confere que o Ouro diminuiu.

Sem template matching, sem OCR, sem configuração, sem loop. Prova o esqueleto inteiro —
captura, privilégio, timing da Janela de Confirmação, injeção e verificação — deixando em
aberto apenas "qual Listagem clicar", que é exatamente o buraco que a camada de visão
preenche depois.

O **script** é descartável — coordenada chumbada, sem estrutura, jogado fora depois. O que
sobrevive dele é o **conhecimento**: qual método de captura funcionou, quanto tempo a
Janela de Confirmação leva para abrir, qual biblioteca de injeção passou. Esses achados são
o que a camada de IO definitiva implementa depois, e devem ser registrados na issue.

### Ordem revisada

| Ordem | Fatia | Situação |
|-------|-------|----------|
| 1 | Fatia 0 — ponta a ponta chumbada | nova |
| 2 | [#2](https://github.com/lavarini/mistfall-reseller/issues/2) — slots + Broche + OCR | inalterada |
| 3 | [#3](https://github.com/lavarini/mistfall-reseller/issues/3) — os 7 Itens-alvo | inalterada |
| 4 | [#4](https://github.com/lavarini/mistfall-reseller/issues/4) — estado da tela | inalterada |
| 5 | [#6](https://github.com/lavarini/mistfall-reseller/issues/6) — loop de Compra | perde captura/injeção, provadas na Fatia 0 |
| 6 | [#7](https://github.com/lavarini/mistfall-reseller/issues/7) — Reset | inalterada |
| 7 | [#8](https://github.com/lavarini/mistfall-reseller/issues/8) — guardrails | sobe de prioridade |

A issue [#5](https://github.com/lavarini/mistfall-reseller/issues/5) é **absorvida** pela
Fatia 0 mais um pedaço da #6. Ela existia para responder "dá para dirigir o jogo?", e essa
pergunta morreu.

### Fora do escopo

- **Modo sombra** (rodar sem comprar, só registrando decisões). Foi considerado e
  descartado: a Fatia 0 já dá acesso ao jogo cedo, então ele deixou de ser necessário para
  provar a detecção.
- **Captura manual em massa de prints.** O próprio bot salva as telas que não reconhece,
  então o corpus cresce sozinho.
- **Tendência de Mercado**, **revenda automatizada**, **mais de 1 unidade por Compra**,
  **detecção independente de resolução** — conforme o épico e o ADR-0002.

## Arquitetura

O princípio organizador: **existe exatamente uma fronteira de IO, e todo o resto é função
pura de imagem → dado.** É o ADR-0001 transformado em regra de código.

### A fronteira

Duas interfaces minúsculas, as únicas que sabem que Windows existe:

- `Tela.capturar() -> Imagem`
- `Mao.clicar(x, y)` e `Mao.apertar_espaco()`

Cada uma tem uma implementação falsa: a `Tela` falsa lê um PNG de `images/`, a `Mao` falsa
registra o que lhe pediram. Com isso o cérebro inteiro roda no Mac, sem jogo e sem Windows.

### Unidades puras

| Unidade | Responsabilidade | Depende de |
|---------|------------------|------------|
| `slots` | Recorta os 12 slots por coordenada fixa | nada — geometria pura |
| `itens` | Recorte de ícone → Item-alvo ou nenhum | templates |
| `precos` | Recorte → número, por OCR | tesseract |
| `ouro` | Imagem → Ouro do topo direito | tesseract |
| `estado` | Imagem → lista visível / Janela aberta / outra Categoria | nada |
| `leilao` | Imagem → lista de `Listagem` | as quatro acima |
| `decisao` | `Listagem`s + Preços-alvo → qual comprar, ou nenhuma | nada |

`Listagem` é o tipo central: slot, Item-alvo, Preço-unitário, Estoque.

`decisao` e `slots` não têm dependência alguma. As duas pontas do sistema são triviais, e a
incerteza fica concentrada em `itens` e `precos` — exatamente onde deve estar para ser
atacada.

O orquestrador (`bot`) é a única peça que mistura IO com lógica, e por isso é mantido fino.

### Conferência dupla do preço

Resposta direta à premissa 4. O bot lê o Preço-unitário **duas vezes, em lugares
diferentes**: na Listagem antes de clicar, e dentro da Janela de Confirmação depois de
abrir. Se os números não baterem, aperta Esc em vez de Espaço e salva o print.

Para o bot comprar errado, um erro de OCR precisaria ocorrer duas vezes, em recortes
distintos, produzindo o mesmo número errado. Custa uma captura a mais por Compra — que a
premissa 2 torna gratuita.

Junto vai uma **faixa de sanidade**, derivada da própria configuração: um Preço-unitário
lido abaixo de uma fração do Preço-alvo daquele Item-alvo é tratado como **leitura falha**,
não como pechincha. Um Broche com Preço-alvo 200 aparecendo a 19 é erro de OCR, não
oportunidade. A fração é configurável; um preço absurdamente *alto* não precisa de
tratamento especial, porque a comparação com o Preço-alvo já o rejeita.

### Ferramenta de anotação

Utilitário que recebe um print e devolve a mesma imagem com as caixas desenhadas: cada
slot, o Item identificado, o Preço lido. É como o usuário *vê* se a detecção funciona, em
vez de confiar num número de acurácia agregado. Também é o que torna rápido o trabalho de
rotular o corpus.

## Fluxo e tratamento de erro

1. **Capturar** a tela.
2. **Identificar o estado.** Janela de Confirmação aberta sem termos aberto → Esc e
   recomeça. Categoria errada → volta para Material de Construção. Lista visível → segue.
3. **Ler o Ouro.** Abaixo do piso configurado → para em definitivo.
4. **Varrer** os 12 slots e montar as Listagens.
5. **Decidir.** Nenhuma comprável → **Reset** de Categoria e recomeça.
6. **Clicar** na Listagem escolhida.
7. **Esperar** a Janela de Confirmação ser *detectada* — nunca um `sleep` fixo. Estourou o
   tempo → a lista provavelmente recarregou; recomeça.
8. **Conferir o preço** da Janela contra o da Listagem. Divergiu → Esc, salva o print,
   recomeça.
9. **Espaço.**
10. **Capturar e confirmar que o Ouro diminuiu.** Diminuiu → Compra registrada. Não
    diminuiu → tentativa frustrada registrada. Em ambos os casos a lista já recarregou
    sozinha, então não há Reset.

### Princípios de recuperação

**Nunca travar, sempre voltar a um estado conhecido.** Esc é a primitiva de recuperação: de
qualquer tela inesperada, Esc e captura de novo.

**Parar é mais seguro que insistir.** Se o estado vier irreconhecível em três capturas
seguidas (configurável), o bot para e registra, em vez de continuar clicando. Um bot
perdido clicando às cegas numa tela que não entende é o pior cenário para quem está longe
do teclado.

**Ritmo humano com variação** entre as ações — exigido pela premissa 2 e útil contra
detecção comportamental.

**Tecla de pânico** ativa em qualquer ponto do ciclo, inclusive com a Janela de Confirmação
aberta.

**Escolha entre várias compráveis:** a de maior margem (Preço-alvo − Preço-unitário). Como
se compra 1 unidade e a lista recarrega a cada Compra, a ordem quase não importa na
prática, então vale a regra mais simples.

### Registro

O log grava três coisas, não uma:

- Compras concluídas (Item-alvo, Preço-unitário pago, momento, Ouro restante)
- Tentativas frustradas
- Telas não reconhecidas, com o print anexado

O terceiro caso é o que alimenta a melhoria da detecção: todo print salvo vira caso de
teste.

## Estratégia de testes

**1. Unidades puras, sem imagem.** `decisao` e `slots` se testam com números e coordenadas
escritos à mão: empate, preço exatamente igual ao Preço-alvo, lista vazia.

**2. Visão contra o corpus de prints.** Cada PNG ganha um arquivo de expectativa: qual
Item-alvo em qual slot, a qual Preço-unitário.

A convenção de nomes já existente (`broche-tres-adaga-lanterna-rede-padrao.png` declara
três Broches, uma Adaga, uma Lanterna e uma Rede) serve de verificação cruzada gratuita
contra o arquivo de expectativa.

O trabalho manual inevitável aqui é **rotular os Preços-unitários verdadeiros** de cada
print — é a fonte da verdade do OCR. A ferramenta de anotação torna isso rápido: desenha o
que o bot leu, o usuário corrige apenas o que estiver errado.

**3. Loop contra IO falso.** A `Tela` falsa serve uma sequência roteirizada de prints
(lista → Janela de Confirmação → lista), e a `Mao` falsa grava o que foi pedido.

O teste mais importante da suíte: **quando o preço da Janela diverge do preço da Listagem,
o bot aperta Esc e nunca Espaço.** Se ele ficar vermelho, o bot está torrando Ouro.

Ao lado dele, os testes de recuperação: clique que não abriu a Janela, tela irreconhecível
repetida levando à parada, Ouro abaixo do piso interrompendo, pânico funcionando com a
Janela aberta.

**4. No jogo real, só onde é inevitável.** A Fatia 0 e a validação final da v1.

Níveis 1 a 3 rodam no Mac, sem Windows e sem o jogo — o retorno concreto do ADR-0001.

## Mudanças em documentos existentes

- **CONTEXT.md** (feito neste commit): a justificativa de comprar 1 unidade por Compra
  deixou de ser "para maximizar a velocidade" — premissa que caiu — e passou a ser manter
  simples a interação com a Janela de Confirmação na v1.
- **Épico #1 e issues #2–#8**: precisam refletir a Fatia 0, a absorção da #5 e a ordem
  revisada. Ainda não aplicado.
- **ADR-0001**: a previsão de que a injeção exigiria pydirectinput/AHK/Interception foi
  superada pela evidência do Mini Mouse Macro. Vale uma nota registrando que input e
  captura estão provados e que a exigência real é rodar como administrador.
