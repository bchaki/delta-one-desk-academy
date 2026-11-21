import pytest

from core.data.world import build_world


@pytest.fixture(scope="session")
def world():
    return build_world(7)
