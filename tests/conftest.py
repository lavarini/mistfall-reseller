import random
import pytest

@pytest.fixture(autouse=True)
def reset_random_seed():
    """Reseta a semente global do random para cada teste, garantindo determinismo."""
    random.seed(20260813)
    yield
