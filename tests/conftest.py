import hashlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src import fechamento  # noqa: E402
from src.leitores import achatar, descobrir_arquivos  # noqa: E402


def _hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in achatar(descobrir_arquivos(RAIZ))}


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


ARQUIVOS_CASE = [
    "01_orbe_relatorio_comissoes_set2026.csv",
    "02_tabela_taxas_contratadas.xlsx",
    "03_email_ponte_cambio_relatorio_set2026.eml",
    "04_plano_de_contas_fenix_erp.csv",
    "05a_extrato_banco_aurora_cc4471_set2026.csv",
    "05b_extrato_banco_meridiano_cc90233_set2026.ofx",
    "06_orbe_ajustes_tardios_set2026.csv",
]


def pytest_collection_modifyitems(config, items):
    if all((RAIZ / n).exists() for n in ARQUIVOS_CASE):
        return
    marca = pytest.mark.skip(reason="arquivos do case ausentes — coloque-os na raiz")
    for item in items:
        item.add_marker(marca)
