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

5. Confira que o tesseract responde: `tesseract --version`.
6. Deixe a **escala de exibicao do Windows em 100%** (Configuracoes → Sistema → Tela →
   Escala). Em tela 1440p o Windows costuma sugerir 125%, e com isso a captura nao sai
   2560x1440 — o piloto recusa e sai com codigo 2 antes de fazer qualquer coisa.

## Antes de cada execucao

- Jogo em **2560x1440**, em primeiro plano.
- Leilao aberto, aba **Comprar**, Categoria **Material de Construcao**.
- Pelo menos um **Item-alvo abaixo do Preco-alvo** visivel na tela.
- O terminal aberto **na raiz do repositorio**. "Executar como administrador" abre o
  terminal em `C:\Windows\System32`, e `--pasta` e `--config` sao relativos ao diretorio
  atual: de la, ou o piloto morre em codigo 2 sem achar o `config.toml`, ou as pastas de
  evidencia vao parar dentro do `System32`.

Em todas as execucoes, anote o **codigo de saida**: `echo %ERRORLEVEL%` logo apos o comando.

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
echo %ERRORLEVEL%
```

Ela nao clica nem aperta nada, e o desfecho esperado e `simulou`. Confira no relatorio se o
item e o preco que ela diz que compraria batem com o que voce ve na tela. **Se isso nao
bater, pare aqui** — a visao nao esta lendo a tela ao vivo, e nao adianta arriscar ouro.

Se o desfecho vier `nada_compravel`, nao e falha do bot: nao ha Item-alvo abaixo do
Preco-alvo na tela. Refaca a pre-condicao e rode de novo.

## Segunda execucao: sem administrador, de proposito

Terminal **normal**, agora pra valer:

```
cd C:\caminho\do\repo
mistfall-piloto --pasta execucao-sem-admin
echo %ERRORLEVEL%
```

Quando aparecer a contagem de 5 segundos, **traga o jogo para a frente com Alt+Tab** — o
`SendInput` vai para a janela ativa, e nao para uma coordenada da tela. **Nao clique no
jogo**: um clique pode abrir um modal sozinho e estragar a pre-condicao.

Ha **tres** desfechos possiveis, e distinguir qual aconteceu e a evidencia que o ADR-0001
quer:

1. **Codigo 2**, com "problema de ambiente: SendInput aceitou 0 de 1 eventos" — o Windows
   recusou o input na cara. UIPI confirmado, e a falha **nao** e silenciosa.
2. **Codigo 1**, com "a Janela de Confirmacao nao abriu" — o input foi engolido em
   silencio. UIPI confirmado, e a falha **e** silenciosa. E o desfecho esperado.
3. **Ela compra de verdade** (codigo 0, ou 3). Entao o UIPI **nao** era a causa, o que e um
   bom resultado — mas significa que uma Compra foi feita: **refaca a pre-condicao antes da
   terceira execucao** (confira que ainda ha Item-alvo abaixo do Preco-alvo na tela).

Anote qual dos tres aconteceu, com o codigo de saida.

## Terceira execucao: valendo

Terminal **como administrador**:

```
cd C:\caminho\do\repo
mistfall-piloto --pasta execucao-real
echo %ERRORLEVEL%
```

Durante a contagem de 5 segundos: **Alt+Tab para o jogo**, sem clicar nele, e tire a mao do
mouse.

### Se o desfecho for "abortou" com "o modal mostra nenhum Item-alvo reconhecido"

E o aborto mais provavel, e **nao e viagem perdida**. Significa que o ícone dentro da Janela
nao casou com nenhum template — quase certamente porque o modal desenha o icone numa escala
que a varredura de 0,85x a 1,15x nao cobre, ou com fundo diferente do da lista.

O bot nao apertou Espaco, entao nao gastou ouro. E o print `01-janela.png` daquela pasta **e
a fixture que faltava** desde o inicio do projeto: o primeiro modal com Item-alvo dentro.
Traga a pasta; o `relatorio.json` traz os sete scores do icone e a escala vencedora, que
dizem exatamente o quanto faltou.

## O que trazer de volta

1. As tres pastas de execucao, inteiras.
2. O codigo de saida de cada uma das tres.
3. O tempo que a Janela levou para abrir, que a saida imprime. E um **teto**, nao uma
   medida: o relogio comeca antes do clique e so para depois de uma captura e de uma
   deteccao de estado, entao inclui o custo de perguntar.
4. Qual dos tres desfechos aconteceu na execucao sem administrador.
5. Se comprou: o Ouro antes e depois, e se a queda bateu com o Preco Total.
