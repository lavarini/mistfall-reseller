import pytest

from mistfall.cliques import sortear_ponto


class SorteioControlado:
    def __init__(self, devolvidos):
        self.devolvidos = iter(devolvidos)
        self.chamadas = []

    def randint(self, minimo, maximo):
        self.chamadas.append((minimo, maximo))
        return next(self.devolvidos)


@pytest.mark.parametrize(
    "devolvidos, esperado",
    [([10, 20], (10, 20)), ([30, 40], (30, 40))],
)
def test_sorteia_x_e_y_com_os_quatro_limites_inclusivos(devolvidos, esperado):
    sorteio = SorteioControlado(devolvidos)
    assert sortear_ponto((10, 20, 30, 40), sorteio) == esperado
    assert sorteio.chamadas == [(10, 30), (20, 40)]


@pytest.mark.parametrize("area", [(2, 0, 1, 3), (0, 4, 3, 2)])
def test_rejeita_area_invertida(area):
    with pytest.raises(ValueError, match="area de clique invertida"):
        sortear_ponto(area, SorteioControlado([]))
