import hashlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src import fechamento  # noqa: E402
from src.leitores import descobrir_arquivos  # noqa: E402


def _hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in descobrir_arquivos(RAIZ).values()}


@pytest.fixture(scope="session")
def resultado(tmp_path_factory):
    antes = _hashes()
    saida = tmp_path_factory.mktemp("saida")
    r = fechamento.executar(RAIZ, saida)
    r["hash_antes"], r["hash_depois"] = antes, _hashes()
    return r


@pytest.fixture(scope="session")
def raiz():
    return RAIZ
