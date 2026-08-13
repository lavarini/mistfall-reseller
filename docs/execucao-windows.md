# Rodar a primeira Compra no Windows

## Montagem, uma vez

1. Instale o **Python 3.14** de python.org, marcando "Add python.exe to PATH".
2. Instale o **tesseract** (build do UB Mannheim) e marque a opcao de adicionar ao PATH.
3. Traga o repositorio para a maquina.
4. Numa janela de terminal, na raiz do repositorio:

   ```
   python -m pip install -e .
   python -m pip install mss
   ```

5. Confira que o tesseract responde: `tesseract --version`.

## Antes de cada execucao

- Jogo em **2560x1440**, em primeiro plano.
- Leilao aberto, aba **Comprar**, Categoria **Material de Construcao**.
- Pelo menos um **Item-alvo abaixo do Preco-alvo** visivel na tela.

## Primeira execucao: simulada

Terminal **normal**, sem administrador:

```
mistfall-piloto --simular --pasta execucao-simulada
```

Ela nao clica nem aperta nada. Confira no relatorio se o item e o preco
que ela diz que compraria batem com o que voce ve na tela. **Se isso nao
bater, pare aqui** — a visao nao esta lendo a tela ao vivo, e nao adianta
arriscar ouro.

## Segunda execucao: sem administrador, de proposito

Terminal **normal**, agora pra valer:

```
mistfall-piloto --pasta execucao-sem-admin
```

O esperado e o clique ser ignorado em silencio e o piloto abortar com
"a Janela de Confirmacao nao abriu". Isso **confirma o diagnostico de
UIPI** e responde uma pergunta em aberto do ADR-0001. Anote o que
aconteceu.

## Terceira execucao: valendo

Terminal **como administrador**:

```
mistfall-piloto --pasta execucao-real
```

Tire a mao do mouse durante a contagem de 5 segundos.

## O que trazer de volta

1. As tres pastas de execucao, inteiras.
2. O tempo que a Janela levou para abrir, que a saida imprime.
3. O que aconteceu na execucao sem administrador.
4. Se comprou: o Ouro antes e depois, e se a queda bateu com o Preco Total.
