# Fluxo Completo de Compra e Venda Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar um modo coordenado de Compra/Venda adaptativo, preservando os comandos isolados e padronizando F3/F4.

**Architecture:** Um coordenador explícito mantém uma máquina de estados pequena e consome eventos produzidos pelos executores atuais. A política de ritmo/estoque será pura e testável; uma camada separada fará a navegação entre Comprar, Vender, Inventário, Armazém, Baús e filtro roxo. O ciclo isolado de Venda ganhará uma operação parcial para o coordenador, sem mudar seus defaults atuais.

**Tech Stack:** Python 3.14, dataclasses/enums, OpenCV, NumPy, pytesseract, pytest, protocolos `Tela`/`Mao`/`Interruptor` e dublês existentes.

**Spec:** `docs/superpowers/specs/2026-08-18-fluxo-completo-compra-venda-design.md`

## Global Constraints

- Todos os modos contínuos usam F3 para iniciar e F4 para parar; F2 deixa de ser usado.
- `mistfall-bot` e `mistfall-venda` continuam disponíveis e preservam sua estratégia e seus defaults.
- O modo completo começa em Comprar, Item → Material de Construção, assume `estoque_estimado = 0` e valida o filtro roxo.
- Uma intenção é uma Listagem de Item-alvo no Preço-alvo; ela não depende de Compra confirmada.
- 0–2 Resets entre intenções é rápido; 3 Resets é intervalo lento; três intervalos lentos consecutivos ou cinco Resets consecutivos entram em lento.
- O limite operacional do modo lento é `estoque_estimado >= 45` unidades.
- A Venda lista stacks exatos de 3 e relê `X/Y` após cada Listagem; capacidade cheia e estável por aproximadamente 3 segundos encerra a sessão parcial.
- Sinais estratégicos ambíguos não encerram o processo por um único frame; falhas persistentes de navegação/visão encerram o modo completo com diagnóstico.
- O código Windows continua confinado a `src/mistfall/perifericos/windows.py`; todos os testes novos rodam no macOS.

---

### Task 1: Padronizar o Interruptor F3/F4 sem alterar os ciclos

**Files:**
- Modify: `src/mistfall/perifericos/protocolos.py:35-53`
- Modify: `src/mistfall/perifericos/windows.py:47-123`
- Modify: `ferramentas/bot_cli.py:1-60`
- Modify: `tests/test_perifericos_windows.py` e `tests/test_bot_cli.py`
- Modify: `README.md`, `CONTEXT.md`, `docs/execucao-windows.md`, `tests/test_documentacao.py`

**Interfaces:**
- Consumes: `InterruptorWindows(vk_inicio, vk_parada)` e `Interruptor` existentes.
- Produces: `InterruptorWindows()` com defaults `VK_F3`/`VK_F4`; `mistfall-bot` exibindo F3/F4.

- [ ] **Step 1: Write the failing tests**

Adicionar testes que afirmem `InterruptorWindows()._vk_inicio == VK_F3`, `._vk_parada == VK_F4`, que o bot construa o interruptor padrão com essas teclas e que a documentação não instrua F2 para iniciar nem F3 para parar.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_perifericos_windows.py tests/test_bot_cli.py tests/test_documentacao.py -q`

Expected: falha nos defaults Windows, na mensagem do bot e nas asserções documentais que ainda citam F2/F3.

- [ ] **Step 3: Implement the minimal change**

Trocar apenas os defaults e textos de F2/F3 para F3/F4. Manter os parâmetros explícitos usados pelo CLI de Venda para não quebrar sua injeção existente. Atualizar docstrings que descrevem o par F2/F3.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_perifericos_windows.py tests/test_bot_cli.py tests/test_venda_cli.py tests/test_documentacao.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/perifericos/protocolos.py src/mistfall/perifericos/windows.py ferramentas/bot_cli.py tests/test_perifericos_windows.py tests/test_bot_cli.py tests/test_documentacao.py README.md CONTEXT.md docs/execucao-windows.md
git commit -m "Padroniza interruptores em F3 e F4"
```

### Task 2: Detectar toasts de Compra e validar o filtro roxo

**Files:**
- Create: `src/mistfall/compra_visao.py`
- Create: `tests/test_compra_visao.py`
- Read: `images/cheio-2.png` como fixture já versionada; usar também `sessao/volta-0001/01-apos-espaco.png` como fixture existente

**Interfaces:**
- Produces enum `MensagemCompra` com `SUCESSO`, `INVENTARIO_CHEIO` e `NENHUMA`.
- Produces `detectar_mensagem_compra(img: np.ndarray) -> MensagemCompra`.
- Produces `filtro_roxo_ativo(img: np.ndarray) -> bool`.

- [ ] **Step 1: Write the failing tests**

Testar que `cheio-2.png` retorna `INVENTARIO_CHEIO`, que o frame antigo de sucesso retorna `SUCESSO`, que uma lista sem toast retorna `NENHUMA` e que fixtures de Compra com filtro roxo detectam o filtro enquanto uma variante sintética sem o ícone roxo não detecta.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_compra_visao.py -q`

Expected: falha por módulo/funções inexistentes.

- [ ] **Step 3: Implement the minimal detector**

Recortar a região fixa central do toast, normalizar brilho/cor e classificar as duas mensagens sem varrer a tela inteira. Usar OCR limitado ou comparação visual calibrada contra os dois frames reais, escolhendo o método que não introduza uma captura adicional. Detectar o filtro pela região dos ícones de raridade e pelo sinal de seleção do roxo; encapsular todos os limites como constantes do módulo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_compra_visao.py tests/test_estado.py tests/test_ouro.py -q`

Expected: PASS e nenhuma alteração no comportamento dos detectores existentes.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/compra_visao.py tests/test_compra_visao.py
git commit -m "Detecta resultado visual da Compra"
```

### Task 3: Criar a política pura de ritmo, estoque e transições

**Files:**
- Create: `src/mistfall/fluxo.py`
- Create: `tests/test_fluxo.py`

**Interfaces:**
- Produces `ModoFluxo`, `EventoFluxo`, `AcaoFluxo` e `EstadoFluxo` dataclasses/enums.
- Produces `estado_inicial() -> EstadoFluxo`.
- Produces `aplicar_evento(estado: EstadoFluxo, evento: EventoFluxo) -> tuple[EstadoFluxo, AcaoFluxo]`.
- `EstadoFluxo` expõe `estoque_estimado`, contadores de Resets/intenção, modo e uma flag de Compra pendente.

- [ ] **Step 1: Write the failing tests**

Cobrir sequências explícitas:

```python
assert modo_de(["intencao", "reset", "intencao"]) == ModoFluxo.RAPIDO
assert modo_de(["intencao", "reset", "reset", "reset", "intencao"] * 3) == ModoFluxo.LENTO
assert modo_de(["reset"] * 5) == ModoFluxo.LENTO
```

Também testar `100 - 45 == 55`, Compra confirmada somando 1, Compra inconclusiva somando unidade provisória, inventário cheio sem somar e decisão de Venda quando o estoque lento atinge 45.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fluxo.py -q`

Expected: falha por módulo e interfaces inexistentes.

- [ ] **Step 3: Implement the minimal pure policy**

Modelar cada intenção e Reset como evento; contar Resets entre intenções, acumular três intervalos de três Resets e disparar lento em cinco Resets consecutivos. Separar a decisão `VENDER_POR_INVENTARIO_CHEIO` da decisão `VENDER_POR_FLUXO_LENTO`. Aplicar unidades listadas ao saldo sem zerá-lo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fluxo.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/fluxo.py tests/test_fluxo.py
git commit -m "Modela politica adaptativa de Compra e Venda"
```

### Task 4: Isolar a navegação Comprar/Vender e restauração do filtro

**Files:**
- Create: `src/mistfall/navegacao.py`
- Create: `tests/test_navegacao.py`
- Modify: `src/mistfall/venda_visao.py` somente para reutilizar predicados/constantes de painel e Baú quando necessário

**Interfaces:**
- Produces `ir_para_venda(tela, mao, ritmo) -> FrameVenda`.
- Produces `ir_para_compra(tela, mao, ritmo) -> FrameCompra`.
- Produces `garantir_filtro_roxo(tela, mao, ritmo) -> FrameCompra`.
- Cada função confirma o estado alvo antes de retornar e devolve `None`/resultado de falha com motivo serializável quando o estado não estabiliza.

- [ ] **Step 1: Write the failing tests**

Com `TelaFalsa`/`MaoFalsa`, verificar a sequência Comprar → Vender → Inventário → Armazém → Baú 2, que o primeiro Baú não recebe clique, e o retorno Armazém → Comprar → Material de Construção → filtro roxo. Testar que uma tela não confirmada não é aceita como retorno.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_navegacao.py -q`

Expected: falha por módulo/funções inexistentes.

- [ ] **Step 3: Implement the navigation boundary**

Adicionar coordenadas centrais seguras para abas Comprar/Vender, usar `ler_painel_itens`, `eh_tela_venda`, `ler_bau_selecionado` e `filtro_roxo_ativo`, e encapsular as esperas/retentativas. A navegação para Venda sempre seleciona explicitamente o segundo Baú; o retorno sempre chama `garantir_filtro_roxo`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_navegacao.py tests/test_venda_visao.py tests/test_ciclo_venda.py -q`

Expected: PASS, incluindo a regressão do ciclo de Venda isolado.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/navegacao.py src/mistfall/venda_visao.py tests/test_navegacao.py
git commit -m "Isola navegacao entre Compra e Venda"
```

### Task 5: Adicionar Venda parcial sem alterar o modo isolado

**Files:**
- Modify: `src/mistfall/ciclo_venda.py`
- Modify: `src/mistfall/venda.py` se o resultado precisar expor unidades listadas
- Modify: `tests/test_ciclo_venda.py` e `tests/test_venda.py`

**Interfaces:**
- Preserve: `executar_ciclo_venda(...)` com seu comportamento atual e espera de capacidade cheia.
- Produce: `executar_venda_parcial(tela, mao, config, pasta, interruptor, ritmo, sorteio) -> SessaoVenda`.
- `SessaoVenda` passa a expor `unidades_listadas = vendas * 3` e o último `CapacidadeVenda` observado.

- [ ] **Step 1: Write the failing tests**

Testar que a operação parcial começa no Baú 2, lista até a capacidade atual, relê `X/Y` após cada Venda, aproveita uma vaga liberada e retorna após aproximadamente 3 segundos sem mudança quando `X == Y`. Testar que o ciclo isolado continua esperando como antes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ciclo_venda.py tests/test_venda.py -q`

Expected: falha apenas nos novos testes de parcial.

- [ ] **Step 3: Implement the partial executor**

Extrair a parte comum do ciclo sem duplicar a lógica de `executar_venda`. Na variante parcial, não chamar `esperar_inicio`, iniciar no Baú 2, não esperar indefinidamente quando a capacidade encher e usar uma janela de estabilidade de aproximadamente 3 segundos. Após cada Listagem, capturar a tela, atualizar a capacidade e decidir continuar/encerrar.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ciclo_venda.py tests/test_venda.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/ciclo_venda.py src/mistfall/venda.py tests/test_ciclo_venda.py tests/test_venda.py
git commit -m "Adiciona Venda parcial para o fluxo coordenado"
```

### Task 6: Expor o frame seguinte da Compra para confirmação sem captura extra

**Files:**
- Modify: `src/mistfall/piloto.py`
- Modify: `src/mistfall/ciclo.py`
- Modify: `tests/test_piloto.py` e `tests/test_ciclo.py`

**Interfaces:**
- Add optional callback `observador_frame_inicial: Callable[[np.ndarray], None] | None` to `executar`.
- The callback runs once after the pre-voo capture and before state/analysis, allowing the coordinator to classify the toast from the next normal Volta.
- Existing `observador_ouro` and `executar_ciclo` behavior remain unchanged when the callback is omitted.

- [ ] **Step 1: Write the failing tests**

Testar que o callback recebe exatamente o frame inicial, antes de qualquer clique, e que o fluxo atual continua fazendo a mesma quantidade de capturas quando nenhum callback é fornecido. Testar que o ciclo pode encaminhar o callback sem alterar seus relatórios existentes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_piloto.py tests/test_ciclo.py -q`

Expected: falha nos testes que usam o novo parâmetro.

- [ ] **Step 3: Implement the callback seam**

Adicionar o parâmetro opcional, invocá-lo imediatamente após `tela.capturar()` e manter o callback fora da decisão da Compra. O callback do coordenador atualizará mensagem/Ouro pendentes; o piloto continuará retornando `COMPRA_ENVIADA` como hoje.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_piloto.py tests/test_ciclo.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/piloto.py src/mistfall/ciclo.py tests/test_piloto.py tests/test_ciclo.py
git commit -m "Expõe frame normal para confirmar Compra"
```

### Task 7: Implementar o coordenador e o CLI do fluxo completo

**Files:**
- Create: `src/mistfall/ciclo_completo.py`
- Create: `ferramentas/completo_cli.py`
- Create: `tests/test_ciclo_completo.py`
- Create: `tests/test_completo_cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produce: `executar_ciclo_completo(tela, mao, config, pasta, interruptor, ritmo_compra, ritmo_venda, sorteio=None) -> SessaoCompleta`.
- Produce entry point `mistfall-completo = ferramentas.completo_cli:main`.
- The coordinator calls `executar` for one Compra, `resetar_categoria` only when no intention exists, `executar_venda_parcial` for a partial sale, and the navigation functions for tab changes.

- [ ] **Step 1: Write the failing tests**

Com dublês, testar: início em Comprar; Compra rápida sem Venda voluntária; inventário cheio entrando em Venda; três intervalos lentos entrando em Venda; cinco Resets entrando em Venda; retorno restaurando filtro roxo; saldo 100→55 após vender 45; e parada F4 em Compra ou Venda.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ciclo_completo.py tests/test_completo_cli.py -q`

Expected: falha por módulos/entry point inexistentes.

- [ ] **Step 3: Implement the coordinator**

Criar o laço que espera F3 uma única vez, captura eventos de cada Volta, entrega-os a `aplicar_evento`, executa a ação resultante e mantém um relatório de sessão. Ao entrar em Venda, navegar, chamar a variante parcial, subtrair `unidades_listadas`, navegar de volta e garantir o roxo. Nenhuma falha de um sinal estratégico isolado encerra o laço; falha persistente de navegação encerra com desfecho e motivo.

- [ ] **Step 4: Implement the CLI and entry point**

Seguir o padrão de `bot_cli.py`/`venda_cli.py`: `--pasta`, `--config`, opções de ritmo, validação de `precos_venda`, `InterruptorWindows(vk_inicio=VK_F3, vk_parada=VK_F4)`, e mensagem operacional F3/F4. Adicionar `mistfall-completo` ao `pyproject.toml`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_ciclo_completo.py tests/test_completo_cli.py tests/test_instalacao.py -q`

Expected: PASS, incluindo a existência do novo entry point.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/ciclo_completo.py ferramentas/completo_cli.py tests/test_ciclo_completo.py tests/test_completo_cli.py pyproject.toml
git commit -m "Adiciona coordenador do fluxo completo"
```

### Task 8: Telemetria, documentação e regressão completa

**Files:**
- Modify: `src/mistfall/telemetria.py`
- Create or modify: `tests/test_telemetria.py`
- Modify: `README.md`, `CONTEXT.md`, `docs/execucao-windows.md`, `tests/test_documentacao.py`

**Interfaces:**
- Produce a session JSONL stream for coordinator events without changing the existing Ouro/loop JSONL contracts.
- Document the three modes, F3/F4, startup assumptions, 45-unit policy, partial Venda and the new command.

- [ ] **Step 1: Write the failing tests**

Testar a gravação de eventos com modo, intenção, Resets, saldo, unidades listadas, capacidade e motivo da transição. Adicionar asserções documentais para `mistfall-completo`, F3/F4, início em Material de Construção, segundo Baú e limite 45.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_telemetria.py tests/test_documentacao.py -q`

Expected: falha nas novas chaves e textos.

- [ ] **Step 3: Implement telemetry and documentation**

Adicionar um escritor incremental dedicado ao modo completo; preservar `telemetria-ouro.jsonl` e `tempos-do-laco.jsonl` dos modos atuais. Atualizar exemplos de uso e remover instruções antigas F2/F3.

- [ ] **Step 4: Run the full verification suite**

Run: `pytest -q`

Expected: PASS em toda a suíte existente e nova.

- [ ] **Step 5: Review the diff and commit**

```bash
git diff --check HEAD~1
git status --short
git add src/mistfall/telemetria.py tests/test_telemetria.py README.md CONTEXT.md docs/execucao-windows.md tests/test_documentacao.py
git commit -m "Documenta e instrumenta o fluxo completo"
```

## Plan Self-Review

- Spec coverage: modos isolados e F3/F4 (Task 1), toasts/filtro (Task 2), ritmo/saldo (Task 3), navegação (Task 4), Venda parcial/capacidade (Task 5), confirmação sem captura extra (Task 6), coordenador/CLI (Task 7), telemetria/documentação/regressão (Task 8).
- Placeholder scan: no step depends on an unspecified future work item; every task names files, interfaces, tests and commands.
- Type consistency: `MensagemCompra`, `EstadoFluxo`, `aplicar_evento`, `executar_venda_parcial` and `executar_ciclo_completo` are introduced before consumers.
