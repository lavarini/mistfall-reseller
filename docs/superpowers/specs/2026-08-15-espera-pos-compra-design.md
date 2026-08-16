# Design: espera de estabilização após Compra enviada

## Objetivo

Evitar que a próxima Volta leia e clique uma lista ainda em atualização depois de uma Compra
enviada. O ajuste deve proteger somente esse caminho, sem reduzir a vazão das Voltas que não
compraram.

## Comportamento

O `Ritmo` passa a expor duas esperas diferentes entre Voltas:

- `espera_entre_voltas`, já existente, continua fixa em `0.15` segundo;
- `espera_apos_compra`, nova faixa, usa `(0.35, 0.45)` segundo.

Depois de `COMPRA_ENVIADA`, o ciclo sorteia uma espera uniformemente distribuída entre 350 e
450 ms. A média estatística da faixa é 400 ms. Depois de qualquer outro desfecho, o ciclo mantém
a espera fixa atual de 150 ms.

O ajuste não espera nem reconhece uma mudança visual. É uma primeira proteção temporal,
deliberadamente simples e não bloqueante além da própria pausa aprovada.

## Fluxo e aleatoriedade

O ciclo decide a espera depois de imprimir o resultado da Volta e antes de iniciar a próxima.
Ele usa a mesma instância de `random.Random` da sessão que já controla os demais sorteios da
Compra.

Em pseudocódigo:

```python
if resultado.desfecho is Desfecho.COMPRA_ENVIADA:
    espera = sorteio.uniform(*ritmo.espera_apos_compra)
else:
    espera = ritmo.espera_entre_voltas
time.sleep(espera)
```

`PAROU` continua saindo do ciclo antes de qualquer espera. A alternância de Reset, decisões,
capturas, cliques e teclas não muda.

`Ritmo.instantaneo()` define `espera_apos_compra=(0.0, 0.0)` e mantém
`espera_entre_voltas=0.0`, para que a suíte não passe a dormir.

## Telemetria

A telemetria de intervalo já mede a duração real da espera entre Voltas. Ela continua recebendo
`espera_anterior`, agora com o valor efetivamente escolhido:

- aproximadamente 350–450 ms depois de uma Compra enviada;
- aproximadamente 150 ms nos demais casos com ritmo padrão.

Não se adiciona campo, arquivo ou evento. A medição existente basta para validar o efeito em uma
sessão real.

## Testes

Os testes do ciclo devem provar:

- Compra enviada chama `sleep` com valor dentro de `0.35..0.45`;
- sementes variadas produzem mais de um valor pós-Compra;
- a mesma semente reproduz o valor;
- mudar o estado global de `random` não altera uma sessão com gerador injetado;
- `NADA_COMPRAVEL`, incluindo Volta com Reset, mantém exatamente `0.15` segundo;
- `ABORTOU` mantém exatamente `0.15` segundo;
- `PAROU` não dorme;
- a mesma instância da sessão continua sendo repassada a piloto e Reset;
- `Ritmo.instantaneo()` zera ambas as esperas;
- a telemetria recebe a espera realmente aplicada.

Testes da CLI que verificam o ritmo padrão passam a conferir também a nova faixa. Não se adiciona
argumento de linha de comando nesta etapa.

## Documentação operacional

O README deve explicar que, após uma Compra enviada, o loop aguarda um valor sorteado entre 350
e 450 ms para a lista atualizar. Deve distinguir essa espera dos 150 ms mantidos após Voltas sem
Compra.

## Fora de escopo

- esperar ou reconhecer estabilização visual da lista;
- alterar a espera após Voltas sem Compra;
- alterar a espera entre clique e Espaço;
- mudar análise, decisão, Reset, Ouro, cliques ou fluxo de Venda;
- tornar a faixa configurável por TOML ou CLI;
- adicionar nova telemetria ou persistir o valor sorteado fora da medição existente.
