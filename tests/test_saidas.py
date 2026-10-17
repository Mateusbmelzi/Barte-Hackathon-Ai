"""Formato do edital e regra central do rastro, lendo os CSVs gerados."""
import re
import shutil
from collections import defaultdict
from decimal import Decimal as D

import pandas as pd
import pytest

from src import fechamento
from src.leitores import descobrir_arquivos
from src.saidas import COLUNAS

OBRIGATORIAS = {
    "comissoes_por_lojista.csv": ["id_saida", "cnpj", "lojista", "linha_negocio", "comissao_brl"],
    "divergencias_taxa.csv": ["id_saida", "cnpj", "linha_negocio", "ref_origem", "taxa_contratada_pct",
                              "taxa_aplicada_pct", "diferenca_brl"],
    "notas_a_emitir.csv": ["id_saida", "tomador_cnpj", "tomador", "linha_negocio", "valor_brl", "discriminacao"],
    "lancamentos_classificados.csv": ["id_saida", "banco", "ref_origem", "data", "descricao", "valor",
                                      "conta_codigo", "metodo", "confianca"],
    "pendencias.csv": ["id_saida", "tipo", "ref_origem", "valor_brl", "motivo", "quem_decide"],
    "rastro.csv": ["id_saida", "arquivo_origem", "ref_origem", "valor"],
}
VALOR = {"comissoes_por_lojista.csv": "comissao_brl", "divergencias_taxa.csv": "diferenca_brl",
         "notas_a_emitir.csv": "valor_brl", "pendencias.csv": "valor_brl", "lancamentos_classificados.csv": "valor"}


def _ler(pasta, nome):
    return pd.read_csv(pasta / nome, sep=";", dtype=str, keep_default_na=False)


@pytest.mark.parametrize("nome", list(OBRIGATORIAS))
def test_colunas_obrigatorias_na_ordem(resultado, nome):
    df = _ler(resultado["saida"], nome)
    assert list(df.columns[: len(OBRIGATORIAS[nome])]) == OBRIGATORIAS[nome]
    assert list(df.columns) == COLUNAS[nome]
    if nome != "rastro.csv":
        assert df["id_saida"].is_unique


def test_formatos(resultado):
    s = resultado["saida"]
    num = re.compile(r"^-?\d+\.\d{2}$")
    for nome, col in VALOR.items():
        df = _ler(s, nome)
        vals = [v for v in df[col] if v != ""]
        assert all(num.match(v) for v in vals), nome
    for nome, col in [("comissoes_por_lojista.csv", "cnpj"), ("divergencias_taxa.csv", "cnpj"),
                      ("notas_a_emitir.csv", "tomador_cnpj")]:
        assert all(re.fullmatch(r"\d{14}", v) for v in _ler(s, nome)[col]), nome
    lan = _ler(s, "lancamentos_classificados.csv")
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in lan["data"])
    assert set(lan["banco"]) == {"AURORA", "MERIDIANO"}
    assert set(lan["metodo"]) <= {"REGRA", "IA", "HUMANO"}
    assert all(0 <= float(c) <= 1 for c in lan["confianca"])
    div = _ler(s, "divergencias_taxa.csv")
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in div["data"])
    for nome in ("comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv"):
        assert set(_ler(s, nome)["linha_negocio"]) == {"CHECKOUT", "REMESSA"}
    assert all(";" in l or l == "" for l in (s / "rastro.csv").read_text(encoding="utf-8").splitlines()[:3])


def test_rastro_soma_igual_ao_reportado(resultado):
    s = resultado["saida"]
    rastro = _ler(s, "rastro.csv")
    soma = defaultdict(lambda: D("0"))
    for i, v in zip(rastro["id_saida"], rastro["valor"]):
        soma[i] += D(v)
    obrig = ["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv"]
    for nome, col in VALOR.items():
        df = _ler(s, nome)
        for i, v in zip(df["id_saida"], df[col]):
            if v == "":
                continue
            assert i in soma, f"{i} sem rastro"
            assert soma[i] == D(v), f"{i}: rastro {soma[i]} != {v}"
    ids = set(rastro["id_saida"])
    for nome in obrig:
        assert set(_ler(s, nome)["id_saida"]) <= ids


def test_rastro_ref_existe_na_origem(resultado):
    rastro = _ler(resultado["saida"], "rastro.csv")
    d = resultado["dados"]
    validos = ({l["id"] for l in d["orbe"]} | {o["op"] for o in d["ponte"]}
               | {m["ref"] for m in d["aurora"]} | {m["ref"] for m in d["meridiano"]})
    assert set(rastro["ref_origem"]) <= validos


def test_roda_com_nomes_de_outubro(raiz, tmp_path):
    """Robustez: arquivos com outros nomes (mesmo padrão) em outra pasta."""
    ent = tmp_path / "entrada"
    ent.mkdir()
    novos = {"orbe": "orbe_comissoes_out.csv", "taxas": "taxas_v2.xlsx", "ponte": "ponte.eml",
             "plano": "plano_de_contas.csv", "aurora": "aurora_out.csv", "meridiano": "meridiano.ofx"}
    for k, p in descobrir_arquivos(raiz).items():
        shutil.copy(p, ent / novos[k])
    r = fechamento.executar(ent, tmp_path / "saida")
    assert sum(c["comissao"] for c in r["comissoes"]) == D("207039.73") + D("39543.45")
