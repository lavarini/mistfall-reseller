import pathlib

CONTEXT = pathlib.Path("CONTEXT.md").read_text(encoding="utf-8")
README = pathlib.Path("README.md").read_text(encoding="utf-8")


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
