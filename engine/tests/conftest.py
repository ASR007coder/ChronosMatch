import pytest

from engine.matching_engine import MatchingEngine as PyEngine

ENGINES = [pytest.param(PyEngine, id="python")]
try:  # Cython build is added in Week 2; every test then runs against both engines.
    from engine.cy_matching_engine import MatchingEngine as CyEngine
    ENGINES.append(pytest.param(CyEngine, id="cython"))
except ImportError:
    pass


@pytest.fixture(params=ENGINES)
def engine_cls(request):
    return request.param


@pytest.fixture
def engine(engine_cls):
    return engine_cls()
