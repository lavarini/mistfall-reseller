import pathlib

CONTEXT = pathlib.Path("CONTEXT.md").read_text(encoding="utf-8")
README = pathlib.Path("README.md").read_text(encoding="utf-8")
EXECUCAO_WINDOWS = pathlib.Path("docs/execucao-windows.md").read_text(encoding="utf-8")
ADR_DEV_WINDOWS = pathlib.Path("docs/adr/0001-dev-mac-run-windows.md").read_text(
    encoding="utf-8")
ADR_SEM_CONFIRMACAO = pathlib.Path(
    "docs/adr/0003-nao-conferir-a-janela-de-confirmacao.md").read_text(
        encoding="utf-8")
LEILAO = pathlib.Path("src/mistfall/leilao.py").read_text(encoding="utf-8")
PRECOS = pathlib.Path("src/mistfall/precos.py").read_text(encoding="utf-8")


def test_o_glossario_nao_promete_menor_ou_igual():
    # Preco-alvo virou o preco EXATO. O texto antigo dizia "maximo que
    # aceitamos pagar" e "menor ou igual".
    assert "menor ou igual" not in CONTEXT
    assert "preço unitário máximo" not in CONTEXT


def test_o_readme_nao_promete_a_regra_antiga():
    # Achado do review final: um revisor colou a regra antiga de volta no
    # README, palavra por palavra ("Escolhe a Listagem de maior margem entre
    # as que estão com preço menor ou igual ao Preço-alvo"), e os 7 testes
    # deste arquivo passaram — porque so afirmavam contra o CONTEXT, nunca
    # contra o README. Estas tres asserções são a prova de que a regra antiga
    # não pode voltar sem a suíte reclamar.
    assert "menor ou igual" not in README
    assert "maior margem" not in README
    assert "abaixo do Preço-alvo" not in README


def test_o_glossario_fala_em_preco_exato():
    assert "exat" in CONTEXT.lower()


def test_a_fracao_de_sanidade_sumiu_da_documentacao():
    assert "fracao_sanidade" not in CONTEXT
    assert "fracao_sanidade" not in README


def test_o_readme_descreve_o_sorteio():
    assert "sorte" in README.lower()


def test_o_readme_documenta_os_trabalhadores():
    assert "trabalhadores" in README


def test_o_readme_nao_promete_quatro_conferencias_no_modal():
    # O icone e lido e reportado, mas nao aborta mais.
    assert "quatro coisas" not in README


def test_o_readme_nao_afirma_o_uipi_como_causa_estabelecida():
    # Administrador e necessario, mas o UIPI e hipotese: numa execucao o
    # clique falhou igual com e sem elevacao.
    assert "é o UIPI" not in README
    assert "não é frescura" not in README


def test_o_readme_nao_promete_paralelismo_na_varredura():
    # A varredura passou a fazer uma chamada so. O texto antigo dizia que
    # `trabalhadores` controlava OCRs em paralelo "na varredura dos 12 slots
    # e nos numeros da Janela de Confirmacao" — metade disso deixou de ser
    # verdade. Config que promete uma coisa e faz outra ja custou um review
    # inteiro neste projeto.
    assert "na varredura dos 12 slots" not in README


def test_o_readme_explica_a_leitura_em_folha_unica():
    assert "folha" in README.lower()


def test_as_docstrings_nao_mandam_trabalhadores_para_a_janela():
    # Achado do review final da folha unica: o README foi corrigido, mas
    # leilao.py e precos.py continuaram dizendo que o helper de paralelismo
    # serve as tres leituras da Janela de Confirmacao. Depois do ADR-0003
    # aquelas leituras sairam do caminho, e no caso de precos.py a frase nunca
    # foi verdade — janela.py tem o proprio _numero e nunca importou daqui.
    #
    # O guarda do README so olha o README. Quem le o codigo le a docstring, e
    # ela estava dizendo o contrario da verdade.
    assert "servindo as tres" not in LEILAO
    assert "Serve as tres leituras" not in PRECOS


def test_o_readme_diz_que_trabalhadores_esta_dormente():
    # A chave perdeu os DOIS consumidores que tinha: a varredura virou uma
    # chamada so, e as tres leituras da Janela sairam com a conferencia do
    # modal (ADR-0003). O teste acima guarda uma frase antiga; este guarda a
    # afirmacao atual, que e mais forte — a chave nao controla nada. Config que
    # promete uma coisa e faz outra ja custou um review inteiro neste projeto.
    assert "dormente" in README


def test_o_glossario_define_volta():
    # O titulo sozinho nao define o termo nem guarda os sinonimos rejeitados.
    assert "**Volta**" in CONTEXT
    assert "_Avoid_: Iteração, Ciclo, Rodada." in CONTEXT


def test_o_glossario_define_interruptor():
    # O titulo sozinho nao define o termo nem guarda os sinonimos rejeitados.
    assert "**Interruptor**" in CONTEXT
    assert "_Avoid_: Hotkey, Atalho, Tecla de pânico." in CONTEXT


def test_o_readme_documenta_as_teclas():
    # As teclas precisam estar ligadas ao comando e ao contexto do jogo.
    assert "mistfall-bot" in README
    assert "Aperte **F3** dentro do jogo" in README
    assert "**F4** para pausar" in README
    assert "**F5** para encerrar" in README


def test_a_documentacao_nao_instrui_f2_f3_para_compra():
    textos = README + CONTEXT + EXECUCAO_WINDOWS
    assert "F2" not in textos
    assert "F3 para parar" not in textos


def test_readme_diz_que_ouro_nao_bloqueia_e_documenta_telemetria():
    minusculo = README.lower()
    assert "telemetria-ouro.jsonl" in README
    assert "tempos-do-laco.jsonl" in README
    assert "não confirma" in minusculo or "nao confirma" in minusculo
    assert "benchmark_analise" in README


def test_documentacao_limita_telemetria_de_ouro_a_tela_lista():
    assert "cada Volta cuja tela inicial é LISTA" in " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "cada Volta cuja tela inicial e LISTA" in execucao_windows
    assert "O Ouro e observado uma vez, no frame inicial" not in execucao_windows
    assert (
        "Nas Voltas cuja tela inicial e reconhecida como LISTA, o Ouro e observado uma vez"
        in execucao_windows
    )


def test_documentacao_nao_promete_jsonl_imune_a_erro_de_io():
    assert "nenhuma linha deles bloqueia o laço" not in README
    assert "nunca interrompem o laco" not in EXECUCAO_WINDOWS
    readme = " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "não participam da decisão de Compra" in readme
    assert "não criam uma espera exclusiva" in readme
    assert "nao participam da decisao de Compra" in execucao_windows
    assert "nao criam uma espera exclusiva" in execucao_windows


def test_documentacao_viva_nao_promete_codigo_3_ou_confirmacao_do_ouro():
    textos = README + EXECUCAO_WINDOWS
    assert "OURO NAO CAIU" not in textos
    assert "confirmacao_do_ouro" not in textos
    assert "| `3` |" not in textos


def test_documentacao_arquitetural_descreve_ouro_observacional():
    contexto = " ".join(CONTEXT.split())
    adr_sem_confirmacao = " ".join(ADR_SEM_CONFIRMACAO.split())
    adr_dev_windows = " ".join(ADR_DEV_WINDOWS.split())

    assert "durante a espera pelo Ouro" not in contexto
    assert "Ouro é apenas telemetria observacional" in adr_sem_confirmacao
    assert "COMPRA_ENVIADA" in adr_sem_confirmacao
    assert "nem espera posterior ao Espaço" in adr_sem_confirmacao
    assert "`OURO_NAO_CAIU` era" in adr_dev_windows
    assert "Hoje, `COMPRA_ENVIADA`" in adr_dev_windows


def test_documentacao_qualifica_as_etapas_presentes_em_tempos():
    readme = " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "`tempos` contém somente as etapas alcançadas pela Volta" in readme
    assert "`tempos` contem somente as etapas alcancadas pela Volta" in execucao_windows
    assert "abortos, simulações e caminhos curtos têm um conjunto parcial" in readme
    assert "abortos, simulacoes e caminhos curtos tem um conjunto parcial" in execucao_windows


def test_documentacao_exige_pasta_nova_por_processo_de_sessao():
    readme = " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "Cada processo deve usar uma pasta nova de sessão" in readme
    assert "reutilizar uma pasta existente mistura os JSONL" in readme
    assert "Cada processo deve usar uma pasta nova de sessao" in execucao_windows
    assert "reutilizar uma pasta existente mistura os JSONL" in execucao_windows


def test_o_readme_avisa_que_f4_e_o_unico_freio_do_ouro():
    # Sem este aviso o operador pode supor um piso e deixar o bot gastar Ouro.
    assert "Não há piso de Ouro" in README
    assert "o F4 pausa e o F5 encerra" in README
    assert "limitação do jogo, não uma guarda do bot" in README


def test_o_adr_nao_diz_mais_que_o_clique_nao_foi_confirmado():
    # Guarda o marco historico sem deixa-lo se passar por comportamento vivo.
    adr = ADR_DEV_WINDOWS
    assert "Que o clique com duração resolve" not in adr
    assert "O clique com duração resolve" in adr
    assert ("Naquela execução, o Espaço ainda não tinha sido observado" in adr
            and "nenhuma Compra havia completado" in adr)
    assert "Hoje, `COMPRA_ENVIADA`" in adr
    assert "não há leitura nem espera pós-Espaço" in adr
    assert "Se administrador é necessário para alguma coisa também segue em aberto." in adr


def test_o_glossario_define_o_fluxo_de_venda():
    for termo in ("**Venda**", "**Preço de Venda**", "**Capacidade de Venda**", "**Baú**"):
        assert termo in CONTEXT


def test_o_readme_documenta_a_capacidade_lida_da_tela():
    assert "mistfall-venda" in README
    assert "Capacidade de Venda vem sempre de `X/Y` na tela" in README
    assert "não existe limite fixo" in README


def test_o_readme_diz_que_cada_bau_e_processado_uma_vez():
    assert "Cada Baú é processado uma vez" in README
    assert "avança somente para a direita" in README


def test_o_readme_documenta_os_tres_modos_continuos():
    # Os três comandos contínuos (Compra, Venda, coordenado) precisam estar
    # descritos juntos, não só espalhados em seções separadas.
    assert "mistfall-bot" in README
    assert "mistfall-venda" in README
    assert "mistfall-completo" in README
    assert "alterna Compra e Venda sozinho" in README


def test_o_readme_documenta_inicio_e_premissas_do_fluxo_completo():
    assert "mistfall-completo --pasta sessao-completa" in README
    assert "Item → Material de Construção" in README
    assert "filtro roxo" in README
    assert "estoque_estimado = 0" in README


def test_a_documentacao_de_execucao_windows_repete_inicio_do_fluxo_completo():
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "mistfall-completo --pasta sessao-completa" in execucao_windows
    assert "Item -> Material de Construcao" in execucao_windows
    assert "filtro roxo" in execucao_windows
    assert "estoque_estimado = 0" in execucao_windows


def test_o_readme_documenta_venda_parcial_no_segundo_bau_e_limite_quarenta_e_cinco():
    readme = " ".join(README.split())
    assert "segundo Baú" in readme
    assert "atinge 45 unidades" in readme
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "segundo Bau" in execucao_windows
    assert "atinge 45 unidades" in execucao_windows


def test_documentacao_registra_o_jsonl_do_fluxo_completo_sem_tocar_nos_existentes():
    assert "eventos-do-fluxo.jsonl" in README
    assert "eventos-do-fluxo.jsonl" in EXECUCAO_WINDOWS
    # Os contratos históricos continuam intactos e continuam documentados.
    assert "telemetria-ouro.jsonl" in README
    assert "tempos-do-laco.jsonl" in README


def test_documentacao_avisa_divergencia_do_estoque_estimado_sem_reconciliacao():
    readme = " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    assert "unidade otimista" in readme
    assert "unidade otimista" in execucao_windows
    assert "não há reconciliação persistente implementada" in readme
    assert "nao ha reconciliacao persistente implementada" in execucao_windows


def test_o_context_define_os_termos_do_fluxo_completo():
    for termo in (
        "**Filtro Roxo**", "**Intenção**", "**Regime do Fluxo**",
        "**Estoque estimado**", "**Fluxo Completo**",
    ):
        assert termo in CONTEXT
    contexto = " ".join(CONTEXT.split())
    assert "unidade otimista" in contexto
    assert "não há reconciliação persistente" in contexto


def test_documentacao_repete_o_aviso_de_io_no_jsonl_do_fluxo_completo():
    # O aviso de gravação síncrona existia só para os dois JSONL antigos.
    # `eventos-do-fluxo.jsonl` grava do mesmo jeito, dentro do laço, e pode
    # encerrar a execução do mesmo jeito — o modo completo é justamente o que
    # roda mais tempo sem ninguém olhando.
    readme = " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())
    aviso_readme = "erro de I/O ainda pode encerrar a execução"
    aviso_execucao = "erro de I/O ainda pode encerrar a execucao"

    assert readme.count(aviso_readme) >= 2
    assert execucao_windows.count(aviso_execucao) >= 2
    assert aviso_readme in readme.split("eventos-do-fluxo.jsonl", 1)[1][:500]
    assert aviso_execucao in execucao_windows.split("eventos-do-fluxo.jsonl", 1)[1][:500]


def test_documentacao_registra_o_sessao_json_e_o_codigo_um_do_fluxo_completo():
    # Um operador que encontra o processo terminado precisa saber onde está o
    # diagnóstico e o que o código de saída significa neste modo.
    readme = " ".join(README.split())
    execucao_windows = " ".join(EXECUCAO_WINDOWS.split())

    assert "sessao.json" in readme
    assert "sessao.json" in execucao_windows


def test_o_glossario_nao_promete_quatro_baus():
    # O Armazem expande entre seasons. O texto antigo dizia "Uma das quatro
    # abas do Armazem", e foi essa promessa que travou a leitura em quatro.
    assert "quatro abas" not in CONTEXT
    assert "Baú" in CONTEXT


def test_o_readme_nao_promete_encerrar_no_quarto_bau():
    # A varredura vai ate o ultimo Bau detectado, nao ate o quarto.
    assert "quarto Baú" not in README
    assert "último Baú" in README


def test_o_glossario_nao_promete_somar_em_toda_compra_inconclusiva():
    # Compra inconclusiva com Ouro legivel e SEM queda soma zero: o sinal diz
    # que a Compra provavelmente nao aconteceu. O texto antigo prometia "soma 1
    # a cada Compra confirmada ou inconclusiva", sem a ressalva.
    assert "soma 1 a cada Compra confirmada ou inconclusiva" not in CONTEXT
    assert "sem queda" in CONTEXT


def test_o_glossario_define_resgatar_e_recuperavel():
    # Termos do jogo que o codigo passou a usar: sem verbete, cada um escreve
    # de um jeito e o glossario deixa de ser a fonte unica.
    assert "**Resgatar**" in CONTEXT
    assert "**Recuperável**" in CONTEXT
