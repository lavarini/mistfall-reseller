# Task 3 — Randomizar os dois cliques do Reset

## Ciclo TDD

- Vermelho: após adaptar e ampliar `tests/test_reset.py`,
  `/Users/lavarini/lavarini/projects/mistfall-reseller/.venv/bin/python -m pytest tests/test_reset.py -q`
  falhou com 6 falhas e 2 sucessos, pois `resetar_categoria` ainda não aceitava
  `sorteio`.
- Verde: após implementar a injeção do gerador e o sorteio dos dois pontos,
  o mesmo comando passou com `8 passed`.
- Regressão: `/Users/lavarini/lavarini/projects/mistfall-reseller/.venv/bin/python -m pytest -q`
  passou com `425 passed in 125.24s (0:02:05)`.

## Arquivos

- `src/mistfall/reset.py`: adiciona `sorteio` opcional, inicializa um gerador
  local quando necessário e usa `area_clique_categoria`/`sortear_ponto` nos
  cliques de ida e volta.
- `tests/test_reset.py`: verifica áreas seguras, alternância Forja/Chave,
  mesma instância injetada, reprodutibilidade, independência do random global
  e tentativa do segundo clique após falha da primeira transição.

## Auto-revisão

- A assinatura mantém os argumentos posicionais existentes; `sorteio` foi
  acrescentado ao final.
- A ordem dos cliques, capturas e pausas não foi alterada.
- O segundo clique continua sendo executado sem depender do resultado da
  primeira captura.
- `git diff --check` não reportou problemas.
- Nenhum arquivo fora do escopo da tarefa foi alterado.

## Commit

Implementação: `d7eca29 Randomiza cliques de Categoria no Reset`.
Este relatório foi finalizado no commit seguinte.
