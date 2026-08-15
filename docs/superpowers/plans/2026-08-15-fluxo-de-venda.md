# Fluxo de Venda — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar `mistfall-venda`, que vende stacks de quantidade exatamente 3 dos Itens-alvo, percorre os Baús apenas à direita e para quando `X/Y` indicar Capacidade de Venda cheia ou quando terminar o quarto Baú.

**Architecture:** A visão de Venda fica isolada em `venda_visao.py`; `venda.py` executa uma Venda e `ciclo_venda.py` controla capacidade, repetição e Baús. O fluxo compartilha `Config`, `Mao`, `Tela`, `Interruptor`, templates de Item-alvo e detecção da Janela de Confirmação, sem transformar a Compra em um modo genérico.

**Tech Stack:** Python 3.14, OpenCV 5, NumPy 2.5, pytesseract 0.3.13/tesseract 5.5, pytest, `ctypes`/SendInput somente no adaptador Windows.

## Global Constraints

- Resolução fixa **2560×1440** (ADR-0002).
- Código, testes, documentação e commits em português, usando o glossário de `CONTEXT.md`.
- Somente stacks de quantidade exatamente **3** são vendidos.
- A tela `X/Y` é a única fonte da Capacidade de Venda; leitura ilegível ou incoerente aborta.
- A Janela de Confirmação só é reconhecida como aberta/fechada; seus campos não são relidos.
- A confirmação usa clique direto em "Listar para Venda"; Espaço é absorvido pelo campo Quantidade focado.
- Depois do clique no slot, a Venda em andamento termina sem consultar F4 no meio.
- O bot nunca navega para um Baú à esquerda do Baú inicial.
- `src/mistfall/perifericos/windows.py` continua sendo o único arquivo dependente de Windows.
- Cada alteração de produção nasce de teste vermelho observado, seguido do mínimo código verde.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/mistfall/config.py` | Carregar Preços-alvo e Preços de Venda; validar os sete Preços de Venda para o comando novo. |
| `src/mistfall/tipos.py` | Tipos puros `Bau`, `CapacidadeVenda` e `SlotArmazem`. |
| `src/mistfall/venda_visao.py` | Geometria, OCR e reconhecimento puro da tela de Venda. |
| `src/mistfall/perifericos/{protocolos,falso,windows}.py` | `Ctrl+A` e digitação numérica atrás de `Mao`. |
| `src/mistfall/venda.py` | Uma Venda: slot → Janela → preencher → clicar em Listar → tela de Venda. |
| `src/mistfall/ciclo_venda.py` | Sessão: capacidade, uma varredura por Baú e avanço à direita. |
| `ferramentas/venda_cli.py` | Comando Windows `mistfall-venda`. |
| `tests/test_{config,venda_visao,perifericos_falso,perifericos_windows,venda,ciclo_venda,venda_cli}.py` | Regressões unitárias e verticais. |
| `CONTEXT.md`, `README.md`, `pyproject.toml` | Vocabulário e operação do novo comando. |

### Task 1: Preços de Venda na configuração

**Files:**
- Modify: `src/mistfall/config.py`
- Modify: `config.toml`
- Modify: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.precos_venda: dict[ItemAlvo, int]`; `validar_precos_venda(config: Config) -> None`
- Preserves: `carregar_config()` aceita arquivo sem `[precos_venda]` para não quebrar o comando de Compra.

- [ ] **Step 1: Escrever testes vermelhos para carregar e validar Preços de Venda**

Adicionar testes que carreguem os sete valores aprovados, preservem um TOML antigo sem a seção e rejeitem mapa incompleto, item desconhecido, booleano, zero e negativo ao chamar `validar_precos_venda`:

```python
def test_carrega_precos_de_venda(tmp_path):
    caminho = escrever_config(tmp_path, """
[precos_alvo]
broche = 188
[precos_venda]
broche = 226
adaga = 240
lanterna = 281
dragao = 295
orbe = 304
rede = 312
codice = 338
""")
    config = carregar_config(caminho)
    validar_precos_venda(config)
    assert config.precos_venda[ItemAlvo.CODICE] == 338

def test_compra_aceita_config_sem_precos_de_venda(tmp_path):
    config = carregar_config(escrever_config(tmp_path, "[precos_alvo]\nbroche = 188\n"))
    assert config.precos_venda == {}

def test_venda_exige_os_sete_precos(tmp_path):
    config = carregar_config(escrever_config(tmp_path, """
[precos_alvo]
broche = 188
[precos_venda]
broche = 226
"""))
    with pytest.raises(ValueError, match="faltam Precos de Venda"):
        validar_precos_venda(config)
```

- [ ] **Step 2: Rodar os testes e confirmar falha pela interface ausente**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`

Expected: FAIL porque `Config.precos_venda` e `validar_precos_venda` ainda não existem.

- [ ] **Step 3: Implementar o parser compartilhado e a validação completa**

Usar um helper que converta uma seção TOML em `dict[ItemAlvo, int]`, mantendo mensagens específicas por seção. `Config` fica compatível com seus construtores atuais:

```python
@dataclass(frozen=True)
class Config:
    precos_alvo: dict[ItemAlvo, int]
    trabalhadores: int = TRABALHADORES_PADRAO
    precos_venda: dict[ItemAlvo, int] = field(default_factory=dict)

def validar_precos_venda(config: Config) -> None:
    faltantes = set(ItemAlvo) - set(config.precos_venda)
    if faltantes:
        nomes = ", ".join(sorted(item.value for item in faltantes))
        raise ValueError(f"faltam Precos de Venda para: {nomes}")
```

Preencher `config.toml` com os sete valores da especificação.

- [ ] **Step 4: Rodar testes focados e a regressão de decisão/CLI de Compra**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_decisao.py tests/test_bot_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.toml src/mistfall/config.py tests/test_config.py
git commit -m "Adiciona Precos de Venda a configuracao"
```

### Task 2: Tipos e geometria da tela de Venda

**Files:**
- Modify: `src/mistfall/tipos.py`
- Create: `src/mistfall/venda_visao.py`
- Create: `tests/test_venda_visao.py`

**Interfaces:**
- Produces: `Bau(IntEnum)` com valores `PRIMEIRO=0` até `QUARTO=3`; `CapacidadeVenda(ocupadas: int, limite: int)`; `SlotArmazem(linha, coluna, item, quantidade)`
- Produces: `ler_capacidade(img) -> CapacidadeVenda | None`; `ler_bau_selecionado(img) -> Bau | None`; `centro_bau(bau) -> tuple[int, int]`; `caixa_slot_armazem(linha, coluna) -> tuple[int, int, int, int]`

- [ ] **Step 1: Escrever testes vermelhos contra as imagens reais**

Carregar `images/venda-stash-2.png`, `images/venda-stash-3.png` e `images/modal-venda-broche.png` e afirmar:

```python
def test_le_capacidade_nas_duas_telas_de_armazem():
    esperado = CapacidadeVenda(ocupadas=0, limite=12)
    assert ler_capacidade(stash_2) == esperado
    assert ler_capacidade(stash_3) == esperado

def test_detecta_bau_dourado_selecionado():
    assert ler_bau_selecionado(stash_2) is Bau.SEGUNDO
    assert ler_bau_selecionado(stash_3) is Bau.TERCEIRO

def test_geometria_tem_8_colunas_e_7_linhas_sem_sobrepor():
    caixas = [caixa_slot_armazem(l, c) for l in range(7) for c in range(8)]
    assert len(set(caixas)) == 56
```

- [ ] **Step 2: Confirmar o vermelho**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py -q`

Expected: FAIL por módulo ausente.

- [ ] **Step 3: Implementar capacidade e geometria fixa**

Usar as regiões medidas nas imagens 2560×1440: capacidade ao redor de `(340, 200, 425, 250)`, centros dos Baús na faixa `x=1720..1915, y≈286`, e grade 8×7 iniciando em `x≈1688, y≈333`, passos aproximados `92×128`. Ajustar os limites exatos contra os testes reais, mantendo todos os números nomeados como constantes. Para capacidade, recortar apenas `X/Y`, ampliar 4×, Otsu e OCR com whitelist `0123456789/`; aceitar apenas regex `^(\d+)/(\d+)$` e validar `0 <= X <= Y` e `Y > 0`.

Para o Baú, comparar brilho/cor dourada em recortes idênticos dos quatro ícones. Só devolver o maior quando ele ultrapassar limiar absoluto medido nas duas imagens e tiver margem sobre o segundo colocado; caso contrário, `None`.

```python
def ler_capacidade(img: np.ndarray) -> CapacidadeVenda | None:
    texto = _ocr_capacidade(_recortar(img, REGIAO_CAPACIDADE))
    casamento = re.fullmatch(r"(\d+)/(\d+)", texto)
    if casamento is None:
        return None
    ocupadas, limite = map(int, casamento.groups())
    if limite <= 0 or not 0 <= ocupadas <= limite:
        return None
    return CapacidadeVenda(ocupadas, limite)
```

- [ ] **Step 4: Adicionar negativos sintéticos para capacidade e Baú ambíguo**

Testar `X > Y`, limite zero, texto apagado e dois Baús com o mesmo destaque. A mudança de produção que faz esses testes passarem deve ser somente os guardas e a margem, sem fallback em `12`.

- [ ] **Step 5: Rodar testes focados**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/tipos.py src/mistfall/venda_visao.py tests/test_venda_visao.py
git commit -m "Le capacidade e Bau da tela de Venda"
```

### Task 3: Identificação dos slots e stacks de quantidade 3

**Files:**
- Modify: `src/mistfall/venda_visao.py`
- Modify: `tests/test_venda_visao.py`

**Interfaces:**
- Produces: `varrer_armazem(img) -> list[SlotArmazem]`; `escolher_slot_de_venda(slots) -> SlotArmazem | None`; `centro_slot_armazem(slot) -> tuple[int, int]`
- Consumes: `identificar_item`, `pontuar`, templates existentes, grade 8×7 da Task 2.

- [ ] **Step 1: Escrever teste vermelho de leitura real dos stacks**

Mapear explicitamente os slots de Item-alvo visíveis nas duas imagens e suas quantidades revisadas na imagem. O teste deve afirmar ao menos os três Broches `3, 3, 2` do segundo Baú e os stacks `3` dos Itens-alvo do quarto Baú; não usar a própria função sob teste para construir o esperado.

```python
def test_bau_dois_encontra_somente_broches_de_stack_tres_como_candidatos(stash_2):
    slots = varrer_armazem(stash_2)
    candidatos = [s for s in slots if s.item is ItemAlvo.BROCHE and s.quantidade == 3]
    assert [(s.linha, s.coluna) for s in candidatos] == [(5, 1), (5, 2)]
    assert escolher_slot_de_venda(slots) == candidatos[0]
```

Antes de fixar o mapa do quarto Baú, gerar uma imagem anotada de bancada e revisar visualmente cada positivo; esse artefato é diagnóstico temporário e não entra no commit.

- [ ] **Step 2: Confirmar o vermelho**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py -q`

Expected: FAIL porque `varrer_armazem` não existe.

- [ ] **Step 3: Implementar leitura de Item-alvo e quantidade**

Recortar a área do ícone dentro de cada slot e adaptar a escala antes de reutilizar `identificar_item`; escolher a escala por melhor score, sem reduzir `LIMIAR` nem `MARGEM_MINIMA` globais da Compra. Ler quantidades dos 56 slots em uma folha única, como `precos.ler_precos`, com whitelist `0123456789` e separadores pretos. Slot sem número visível recebe `None`, nunca `1` implícito.

```python
def escolher_slot_de_venda(slots: list[SlotArmazem]) -> SlotArmazem | None:
    return next((slot for slot in slots
                 if slot.item is not None and slot.quantidade == 3), None)
```

- [ ] **Step 4: Adicionar testes vermelhos para não candidatos**

Cobrir stack `2`, `5`, sem número, quantidade apagada, não alvo e match ambíguo. Nomear em cada teste qual mudança de produção o faria falhar: aceitar quantidade diferente, assumir quantidade ausente ou afrouxar o template.

- [ ] **Step 5: Rodar visão completa e regressão dos templates de Compra**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py tests/test_itens.py tests/test_regressao.py -q`

Expected: PASS, incluindo a acurácia anterior dos templates.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/venda_visao.py tests/test_venda_visao.py
git commit -m "Detecta stacks vendaveis no Armazem"
```

### Task 4: Digitação numérica na fronteira de IO

**Files:**
- Modify: `src/mistfall/perifericos/protocolos.py`
- Modify: `src/mistfall/perifericos/falso.py`
- Modify: `src/mistfall/perifericos/windows.py`
- Modify: `tests/test_perifericos_falso.py`
- Modify: `tests/test_perifericos_windows.py`

**Interfaces:**
- Produces: `Mao.selecionar_tudo() -> None`; `Mao.digitar_numero(numero: int) -> None`

- [ ] **Step 1: Escrever testes vermelhos dos dublês e do contrato Windows**

```python
def test_mao_falsa_registra_selecao_e_numero():
    mao = MaoFalsa()
    mao.selecionar_tudo()
    mao.digitar_numero(338)
    assert mao.acoes == [("selecionar_tudo",), ("digitar_numero", 338)]
```

Estender o teste AST para exigir ambos os métodos em `MaoWindows`.

- [ ] **Step 2: Confirmar o vermelho**

Run: `.venv/bin/python -m pytest tests/test_perifericos_falso.py tests/test_perifericos_windows.py -q`

Expected: FAIL pelos métodos ausentes.

- [ ] **Step 3: Implementar Ctrl+A e dígitos com scancodes**

Adicionar `SCANCODE_CTRL_ESQUERDO = 0x1D`, `SCANCODE_A = 0x1E` e tabela dos dez dígitos da fileira superior (`0=0x0B`, `1..9=0x02..0x0A`). `selecionar_tudo` mantém Ctrl pressionado enquanto aperta A e solta Ctrl; `digitar_numero` rejeita negativos e aperta cada caractere por `_apertar`.

```python
SCANCODE_DIGITO = {"0": 0x0B, **{str(n): n + 1 for n in range(1, 10)}}

def digitar_numero(self, numero: int) -> None:
    if not isinstance(numero, int) or isinstance(numero, bool) or numero < 0:
        raise ValueError("numero precisa ser inteiro nao negativo")
    for digito in str(numero):
        self._apertar(SCANCODE_DIGITO[digito])
```

- [ ] **Step 4: Testar ordem exata do Ctrl+A e dos scancodes de `338`**

Interceptar `_enviar` e afirmar eventos down/up: Ctrl down, A down, A up, Ctrl up; depois `3,3,8`, cada um com down/up e duração positiva.

- [ ] **Step 5: Rodar testes de periféricos**

Run: `.venv/bin/python -m pytest tests/test_perifericos_falso.py tests/test_perifericos_windows.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/perifericos tests/test_perifericos_falso.py tests/test_perifericos_windows.py
git commit -m "Permite preencher campos da Venda"
```

### Task 5: Executar uma Venda

**Files:**
- Create: `src/mistfall/venda.py`
- Create: `tests/test_venda.py`

**Interfaces:**
- Produces: `RitmoVenda`; `DesfechoVenda`; `ResultadoVenda`; `executar_venda(tela, mao, slot, preco_venda, pasta, ritmo) -> ResultadoVenda`
- Consumes: `identificar_estado(...)=JANELA_CONFIRMACAO`; `eh_tela_venda`; centros dos campos e do slot; `Tela`; `Mao`.

- [ ] **Step 1: Escrever o teste vertical vermelho do caminho feliz**

Roteirizar `TelaFalsa` com tela de Venda, modal e tela de Venda posterior. Afirmar a sequência inteira:

```python
assert mao.acoes == [
    ("clicar", *centro_slot_armazem(slot)),
    ("clicar", *CENTRO_PRECO_VENDA),
    ("selecionar_tudo",),
    ("digitar_numero", 226),
    ("clicar", *CENTRO_QUANTIDADE_VENDA),
    ("selecionar_tudo",),
    ("digitar_numero", 3),
    ("apertar_espaco",),
]
assert resultado.desfecho is DesfechoVenda.VENDEU
```

- [ ] **Step 2: Confirmar o vermelho**

Run: `.venv/bin/python -m pytest tests/test_venda.py -q`

Expected: FAIL por módulo ausente.

- [ ] **Step 3: Implementar a máquina de estados mínima**

`RitmoVenda` concentra pausa antes do clique, intervalo e tetos; `instantaneo()` zera esperas nos testes. O diário grava `00-antes.png`, `01-janela.png`, `02-depois.png` e sempre fecha `relatorio.json` em `finally`. Só inicia digitação após `JANELA_CONFIRMACAO`; só devolve `VENDEU` após `eh_tela_venda` reaparecer.

- [ ] **Step 4: Adicionar testes vermelhos de segurança**

Cobrir: modal nunca abre (somente clique no slot); modal não fecha (um único clique no botão); preço inválido antes de IO; exceção no meio ainda fecha relatório. Testar que nenhuma função de leitura interna de `janela.py` é chamada.

- [ ] **Step 5: Rodar o módulo e testes de estado existentes**

Run: `.venv/bin/python -m pytest tests/test_venda.py tests/test_estado.py tests/test_janela.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/venda.py tests/test_venda.py
git commit -m "Executa uma Venda com valores fixos"
```

### Task 6: Ciclo de Venda, capacidade e Baús à direita

**Files:**
- Create: `src/mistfall/ciclo_venda.py`
- Create: `tests/test_ciclo_venda.py`

**Interfaces:**
- Produces: `SessaoVenda`; `DesfechoSessaoVenda`; `executar_ciclo_venda(tela, mao, config, pasta, interruptor, ritmo) -> SessaoVenda`
- Consumes: `ler_capacidade`, `ler_bau_selecionado`, `varrer_armazem`, `escolher_slot_de_venda`, `centro_bau`, `executar_venda`.

- [ ] **Step 1: Escrever teste vermelho de consumo dos candidatos do mesmo Baú**

Usar dublês de visão e de `executar_venda` para provar a lógica sem OCR: a primeira imagem entrega capacidade `0/12` e dois candidatos; as capturas seguintes atualizam a capacidade para `1/12` e `2/12`. Afirmar duas Vendas antes do primeiro clique de Baú e uma única chamada a `varrer_armazem` naquele Baú.

- [ ] **Step 2: Confirmar o vermelho**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py -q`

Expected: FAIL por módulo ausente.

- [ ] **Step 3: Implementar o laço e a releitura autoritativa**

Ao entrar em um Baú, capturar, validar tela/Baú/capacidade e chamar `varrer_armazem` uma única vez. Guardar em ordem visual todos os candidatos com Item-alvo e quantidade `3`. Para cada candidato, reler a capacidade da captura atual, parar se cheia e delegar uma Venda. Depois de `VENDEU`, atualizar a captura e `X/Y`, mas consumir o próximo candidato armazenado sem novo OCR nem template matching. Ao esgotar a lista, consultar F4 e clicar em `Bau(valor + 1)`; se `QUARTO`, encerrar `ARMAZEM_ESGOTADO`.

Não incrementar capacidade localmente. A única contagem de sucesso da sessão é diagnóstica; a decisão sempre usa o novo `X/Y`.

- [ ] **Step 4: Adicionar testes vermelhos dos términos e guardas**

Cobrir: começa no segundo Baú e nunca clica no primeiro; percorre segundo→terceiro→quarto; termina no quarto; `X == Y`; `X/Y` ilegível; Baú ambíguo; Venda abortada encerra sessão; F4 antes do slot e antes do próximo Baú; mudança de limite `1/12 → 2/20` é aceita porque a nova leitura substitui a anterior.

- [ ] **Step 5: Rodar ciclo e regressão do ciclo de Compra**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py tests/test_ciclo.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/ciclo_venda.py tests/test_ciclo_venda.py
git commit -m "Percorre Baús respeitando a capacidade"
```

### Task 7: Comando, documentação e vocabulário

**Files:**
- Create: `ferramentas/venda_cli.py`
- Create: `tests/test_venda_cli.py`
- Modify: `pyproject.toml`
- Modify: `CONTEXT.md`
- Modify: `README.md`
- Modify: `tests/test_documentacao.py`

**Interfaces:**
- Produces: `mistfall-venda = "ferramentas.venda_cli:main"`

- [ ] **Step 1: Escrever testes vermelhos da CLI**

Testar parser com `--pasta`, `--config`, tempos calibráveis; carregamento e validação dos Preços de Venda antes de importar Windows; código `2` para ambiente/config; montagem de `TelaWindows`, `MaoWindows`, `InterruptorWindows`; e chamada de `executar_ciclo_venda`.

- [ ] **Step 2: Confirmar o vermelho**

Run: `.venv/bin/python -m pytest tests/test_venda_cli.py tests/test_documentacao.py -q`

Expected: FAIL por CLI e documentação ausentes.

- [ ] **Step 3: Implementar CLI e entry point**

Seguir `ferramentas.bot_cli`: mensagem ASCII `aperte F3 no jogo para comecar, F4 para parar`, import local de Windows e pasta padrão `sessao-venda`. Não adicionar `--limite-listagens`.

```toml
[project.scripts]
mistfall-piloto = "ferramentas.piloto_cli:main"
mistfall-bot = "ferramentas.bot_cli:main"
mistfall-venda = "ferramentas.venda_cli:main"
```

- [ ] **Step 4: Documentar o fluxo operacional e o glossário**

Adicionar a `CONTEXT.md` as definições exatas de Venda, Preço de Venda, Capacidade de Venda e Baú da especificação. No README, documentar pré-condição (Vender + Armazém), F3/F4, preços fixos, stack 3, leitura `X/Y`, movimento somente à direita e exemplos:

```bash
mistfall-venda --pasta sessao-venda
# equivalente:
python -m ferramentas.venda_cli --pasta sessao-venda
```

- [ ] **Step 5: Rodar CLI, documentação, instalação e suíte completa**

Run: `.venv/bin/python -m pytest tests/test_venda_cli.py tests/test_documentacao.py tests/test_instalacao.py -q`

Expected: PASS.

Run: `.venv/bin/python -m pytest -q`

Expected: PASS sem avisos ou falhas.

- [ ] **Step 6: Commit**

```bash
git add ferramentas/venda_cli.py tests/test_venda_cli.py pyproject.toml CONTEXT.md README.md tests/test_documentacao.py
git commit -m "Disponibiliza o comando de Venda"
```

### Task 8: Verificação vertical e evidência final

**Files:**
- Modify only if a verified defect is found: files owned by Tasks 1–7 and their tests.

**Interfaces:**
- Verifies all interfaces and constraints above; introduces no new behavior.

- [ ] **Step 1: Confirmar que as três imagens de referência estão rastreadas**

Run: `git status --short images/modal-venda-broche.png images/venda-stash-2.png images/venda-stash-3.png`

Expected before adding: three `??` entries. Review dimensions with OpenCV and add exactly these files to the feature branch.

- [ ] **Step 2: Executar testes focados de Venda com saída detalhada**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_venda_visao.py tests/test_perifericos_falso.py tests/test_perifericos_windows.py tests/test_venda.py tests/test_ciclo_venda.py tests/test_venda_cli.py -v`

Expected: todos PASS.

- [ ] **Step 3: Executar a suíte completa fresca**

Run: `.venv/bin/python -m pytest -q`

Expected: exit `0`, zero falhas.

- [ ] **Step 4: Verificar integridade do diff**

Run: `git diff --check`

Expected: nenhuma saída, exit `0`.

Run: `git status --short`

Expected: apenas os três PNGs prontos para o commit final, ou worktree limpo se já incluídos.

- [ ] **Step 5: Commitar as imagens de evidência, se ainda não incluídas**

```bash
git add images/modal-venda-broche.png images/venda-stash-2.png images/venda-stash-3.png
git commit -m "Adiciona imagens do fluxo de Venda"
```

- [ ] **Step 6: Repetir a verificação após o último commit**

Run: `.venv/bin/python -m pytest -q && git diff --check && git status --short`

Expected: testes verdes, diff íntegro e worktree limpo.
