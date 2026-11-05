import pytest

from engine.matching_engine import MatchingEngine as PyEngine

ENGINES = [pytest.param(PyEngine, id="python")]

try:
    from engine.cython.matching_core import CythonMatchingEngine as CyEngine

    ENGINES.append(pytest.param(CyEngine, id="cython"))
except ImportError as exc:
    print(f"Cython engine unavailable: {exc}")


@pytest.fixture(params=ENGINES)
def engine_cls(request):
    return request.param


@pytest.fixture
def engine(engine_cls):
    return engine_cls()