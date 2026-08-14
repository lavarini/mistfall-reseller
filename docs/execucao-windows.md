# Rodar a primeira Compra no Windows

## Montagem, uma vez

1. Instale o **Python 3.14** de python.org, marcando "Add python.exe to PATH".
2. Instale o **tesseract** (build do UB Mannheim) e marque a opcao de adicionar ao PATH.
3. Traga o repositorio para a maquina.
4. Numa janela de terminal, na raiz do repositorio:

   ```
   python -m pip install -e .
   ```

   O **`-e` nao e opcional**: sem ele os `templates/` ficam fora do pacote instalado e a
   deteccao de item quebra na primeira execucao. O `mss` entra junto, por ser dependencia
   declarada so no Windows.

5. O `pip` termina com um aviso parecido com este, e ele **importa**:

   ```
   WARNING: The script mistfall-piloto.exe is installed in
   'C:\Users\<voce>\AppData\Local\Python\pythoncore-3.14-64\Scripts' which is not on PATH.
   ```

   O Python 3.14 do python.org instala pelo *Python Install Manager*, e o "Add python.exe to
   PATH" do passo 1 poe no PATH um atalho para o `python.exe` — **nao** a pasta `Scripts`
   daquela instalacao. Por isso `python -m pip` funciona e o `mistfall-piloto` responde "nao
   e reconhecido" mesmo com o pacote instalado. Copie o caminho que o aviso imprimiu e
   acrescente-o ao PATH do usuario, no PowerShell:

   ```powershell
   [Environment]::SetEnvironmentVariable(
     'Path',
     [Environment]::GetEnvironmentVariable('Path','User') + ';<o caminho do aviso>',
     'User')
   ```

   Repare que ele le o PATH **do usuario**, e nao o do processo: lendo o do processo voce
   grava uma copia do PATH da maquina dentro do seu, e isso e chato de desfazer. Depois
   **feche e abra um terminal novo** — a sessao atual nao recebe a mudanca. Confirme com
   `Get-Command mistfall-piloto`. Vale tambem para o terminal elevado da terceira execucao: a
   elevacao mantem o mesmo perfil de usuario.

   Se preferir nao mexer no PATH, todo `mistfall-piloto ...` deste roteiro pode virar
   `python -m ferramentas.piloto_cli ...`, que e o mesmo programa pelo caminho do modulo.

6. Confira que o tesseract responde: `tesseract --version`.
7. Deixe a **escala de exibicao do Windows em 100%** (Configuracoes → Sistema → Tela →
   Escala). Em tela 1440p o Windows costuma sugerir 125%, e com isso a captura nao sai
   2560x1440 — o piloto recusa e sai com codigo 2 antes de fazer qualquer coisa.

## Antes de cada execucao

- Jogo em **2560x1440**, em primeiro plano.
- Leilao aberto, aba **Comprar**, Categoria **Material de Construcao**.
- Pelo menos um **Item-alvo exatamente no Preco-alvo** visivel na tela. Preco abaixo do
  Preco-alvo e leitura suspeita, nao pechincha: nao gera Compra, entao a pre-condicao com a
  regra nova e "no valor", nao "abaixo dele".
- O terminal aberto **na raiz do repositorio**. "Executar como administrador" abre o
  terminal em `C:\Windows\System32`, e `--pasta` e `--config` sao relativos ao diretorio
  atual: de la, ou o piloto morre em codigo 2 sem achar o `config.toml`, ou as pastas de
  evidencia vao parar dentro do `System32`.

Em todas as execucoes, anote o **codigo de saida**: `$LASTEXITCODE` logo apos o comando. Os
blocos abaixo estao em **PowerShell**; no `cmd.exe` o equivalente e `echo %ERRORLEVEL%`.

| Codigo | Significado |
|--------|-------------|
| 0 | correu como esperado (comprou, simulou, ou nada havia comprável) |
| 1 | abortou por seguranca — nao apertou Espaco, ou apertou e o Ouro ficou ilegivel |
| 2 | problema de ambiente (resolucao, tesseract, config, `SendInput` recusado) |
| 3 | apertou Espaco e o **Ouro nao se moveu** |

## Primeira execucao: simulada

Terminal **normal**, sem administrador:

```
cd C:\caminho\do\repo
mistfall-piloto --simular --pasta execucao-simulada
$LASTEXITCODE
```

Ela nao clica nem aperta nada, e o desfecho esperado e `simulou`. Confira no relatorio se o
item e o preco que ela diz que compraria batem com o que voce ve na tela. **Se isso nao
bater, pare aqui** — a visao nao esta lendo a tela ao vivo, e nao adianta arriscar ouro.

Se o desfecho vier `nada_compravel`, nao e falha do bot: nao ha Item-alvo exatamente no
Preco-alvo na tela. Refaca a pre-condicao e rode de novo.

## Segunda execucao: sem administrador, de proposito

Terminal **normal**, agora pra valer:

```
cd C:\caminho\do\repo
mistfall-piloto --pasta execucao-sem-admin
$LASTEXITCODE
```

Quando aparecer a contagem de 5 segundos, **traga o jogo para a frente com Alt+Tab** — o
`SendInput` vai para a janela ativa, e nao para uma coordenada da tela. **Nao clique no
jogo**: um clique pode abrir um modal sozinho e estragar a pre-condicao.

Ha **tres** desfechos possiveis:

1. **Codigo 2**, com "problema de ambiente: SendInput aceitou 0 de 1 eventos" — o Windows
   recusou o input na cara. Ai sim o UIPI esta bloqueando, e a falha **nao** e silenciosa.
2. **Codigo 1 ou 3**, sem a Compra acontecer — o clique nao produziu efeito, e o Espaco
   foi apertado no vazio. Como a Janela nao e mais conferida, o piloto nao sabe dizer
   que ela nao abriu: quem denuncia e o Ouro nao ter caido.
3. **Ela compra de verdade** (codigo 0, ou 3) — mas significa que uma Compra foi feita:
   **refaca a pre-condicao antes da terceira execucao** (confira que ainda ha Item-alvo
   exatamente no Preco-alvo na tela).

**O desfecho 2 nao prova UIPI.** Uma versao anterior deste roteiro dizia que sim, e a
execucao de 2026-08-13 mostrou que nao: com e sem administrador o comportamento foi
identico, o `SendInput` aceitou os eventos nas duas, o cursor foi ate a Listagem certa e o
clique nao aconteceu. A causa era o clique ter duracao zero — `LEFTDOWN` e `LEFTUP` no mesmo
lote —, e nao privilegio. Veja o ADR-0001.

Entao, se der o desfecho 2, a pergunta a responder e **onde** o clique se perde, e a
comparacao com e sem administrador e o que separa privilegio de forma do input. Anote qual
dos tres aconteceu, com o codigo de saida, **nas duas execucoes**.

## Terceira execucao: valendo

Terminal **como administrador**:

```
cd C:\caminho\do\repo
mistfall-piloto --pasta execucao-real
$LASTEXITCODE
```

Durante a contagem de 5 segundos: **Alt+Tab para o jogo**, sem clicar nele, e tire a mao do
mouse.

### A Janela nao e mais conferida

Depois do clique o piloto **espera um tempo fixo e aperta Espaco**. A Janela nao e detectada,
nao e capturada e nao e lida. Nenhum aborto vem mais do modal, e nenhuma string do tipo "o
modal cobra X" ou "Preco Unitario ilegivel" existe hoje. Ver o ADR-0003.

Consequencia pratica para quem opera: **o bot aperta Espaco de olhos fechados.** Se o clique
nao abrir a Janela, o Espaco vai para o jogo. Se a Janela abrir com Quantidade diferente de
1, ele compra a Quantidade que estiver la.

A espera e ajustavel sem editar codigo, e e o numero que esta sendo calibrado:

```
mistfall-piloto --pasta execucao-700 --espera-modal 700
```

Cada `relatorio.json` grava o valor usado em `espera_do_modal_ms`, entao as pastas de
tentativas diferentes nao se confundem.

### Se o desfecho for "abortou"

Sobrou pouca coisa que aborta, e nenhuma delas olha o modal: pre-voo em outra Categoria, tela
que nao e a lista, Ouro inicial ilegivel, ou Ouro final ilegivel depois do Espaco. O `motivo`
no `relatorio.json` diz qual.

**Atencao ao aborto depois do Espaco**: nesse caso o bot ja apertou, entao pode ter gastado
ouro. Confira o Ouro no jogo antes de repetir.

## O que trazer de volta

1. As tres pastas de execucao, inteiras.
2. O codigo de saida de cada uma das tres.
3. O `espera_do_modal_ms` de cada pasta, e se aquele valor bastou. E o numero em calibracao:
   pequeno demais e o Espaco chega antes de a Janela abrir.
4. Qual dos tres desfechos aconteceu na execucao sem administrador.
5. Se comprou: o Ouro antes e depois, e se a queda bateu com o Preco-unitario da
   Listagem escolhida. Com o modal fora do caminho, essa e a unica conferencia que
   sobrou — e ela acontece depois do Espaco.
