import pathlib

CONTEXT = pathlib.Path("CONTEXT.md").read_text(encoding="utf-8")
README = pathlib.Path("README.md").read_text(encoding="utf-8")
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
    assert "Aperte **F2** dentro do jogo" in README
    assert "**F3** para parar" in README


def test_o_readme_avisa_que_f3_e_o_unico_freio_do_ouro():
    # Sem este aviso o operador pode supor um piso e deixar o bot gastar Ouro.
    assert "Não há piso de Ouro" in README
    assert "o único freio é o F3" in README


def test_o_adr_nao_diz_mais_que_o_clique_nao_foi_confirmado():
    # Guarda o que foi confirmado e as duas perguntas que continuam abertas.
    adr = pathlib.Path("docs/adr/0001-dev-mac-run-windows.md").read_text(
        encoding="utf-8")
    assert "Que o clique com duração resolve" not in adr
    assert "O clique com duração resolve" in adr
    assert ("continua sem observação é o **Espaço**" in adr
            and "nenhuma Compra jamais completou" in adr)
    assert "Se administrador é necessário para alguma coisa também segue em aberto." in adr
