"""Dossiê determinístico de investigação (PLANO_IA_01 Fase 1): schema, fatos conhecidos de setembro,
determinismo e independência dos 6 CSVs oficiais."""
import json
import re
from decimal import Decimal as D

import pytest

from src import config, fechamento, investigacao
from src.dinheiro import soma
from src.saidas import COLUNAS

CHAVES = ["id_grupo", "contraparte", "linha_negocio", "lojista", "cnpj", "ec_orbe", "natureza", "qtd",
          "valor_divergencia_brl", "valor_devolver_lojista_brl", "valor_recuperar_parceiro_brl",
          "condicao_contratual", "fatos", "respostas_financeiro", "exemplos"]
CASA, ROTA, BRIDGE, MUNDO = "00520815000100", "95927868000148", "22224579000109", "17217888000111"
DINHEIRO = re.compile(r"^-?\d+\.\d{2}$")


@pytest.fixture(scope="module")
def dossie(resultado):
    assert resultado["investigacao_erro"] is None
    return resultado["investigacao"]


@pytest.fixture(scope="module")
def grupos(dossie):
    return {g["cnpj"]: g for g in dossie["grupos"]}


def _textos(g):
    return " ".join(f["texto"] for f in g["fatos"])


def test_schema(dossie, resultado):
    assert list(dossie) == ["competencia", "grupos"] and dossie["competencia"] == "09/2026"
    origem = ({l["id"] for l in resultado["dados"]["orbe"]} | {o["op"] for o in resultado["dados"]["ponte"]})
    for i, g in enumerate(dossie["grupos"], start=1):
        assert list(g) == CHAVES
        assert g["id_grupo"] == f"G{i:02d}"
        assert g["contraparte"] in ("ORBE", "PONTE") and g["linha_negocio"] in ("CHECKOUT", "REMESSA")
        assert g["contraparte"] == {"CHECKOUT": "ORBE", "REMESSA": "PONTE"}[g["linha_negocio"]]
        assert re.fullmatch(r"\d{14}", g["cnpj"])
        assert (g["ec_orbe"] is None) == (g["contraparte"] == "PONTE")
        assert g["natureza"] in ("CONTRATO", "ISENCAO_NAO_INFORMADA")
        assert isinstance(g["qtd"], int) and g["qtd"] > 0
        for k in ("valor_divergencia_brl", "valor_devolver_lojista_brl", "valor_recuperar_parceiro_brl"):
            assert isinstance(g[k], str) and DINHEIRO.match(g[k]), k
        # S51: devolver = o que saiu do bolso (difere da fórmula só pelo truncamento da Orbe / arredondamento)
        assert abs(D(g["valor_devolver_lojista_brl"]) - D(g["valor_divergencia_brl"])) < D("1.00")
        esperado = g["valor_devolver_lojista_brl"] if g["natureza"] == "CONTRATO" else "0.00"
        assert g["valor_recuperar_parceiro_brl"] == esperado
        assert g["condicao_contratual"]
        assert [f["id"] for f in g["fatos"]] == [f"F{n}" for n in range(1, len(g["fatos"]) + 1)]
        for f in g["fatos"]:
            assert list(f) == ["id", "texto", "refs"] and f["texto"] and len(f["refs"]) <= 3
            assert set(f["refs"]) <= origem
        for s in g["respostas_financeiro"]:
            assert list(s) == ["id", "texto"] and s["texto"] == config.TEXTOS_FINANCEIRO[s["id"]]
        assert 1 <= len(g["exemplos"]) <= 3 and set(g["exemplos"]) <= origem


def test_grupos_e_ordem(dossie, resultado):
    chaves = [(g["contraparte"], g["cnpj"], g["natureza"]) for g in dossie["grupos"]]
    assert chaves == [("ORBE", CASA, "ISENCAO_NAO_INFORMADA"), ("ORBE", ROTA, "CONTRATO"),
                      ("PONTE", MUNDO, "CONTRATO"), ("ORBE", BRIDGE, "CONTRATO")]
    valores = [D(g["valor_divergencia_brl"]) for g in dossie["grupos"]]
    assert valores == sorted(valores, reverse=True)
    for g in dossie["grupos"]:                                    # bate com divergencias_taxa.csv
        div = [d for d in resultado["divergencias"]
               if d["cnpj"] == g["cnpj"] and d["linha_negocio"] == g["linha_negocio"] and d["natureza"] == g["natureza"]]
        assert len(div) == g["qtd"] and soma(d["diferenca"] for d in div) == D(g["valor_divergencia_brl"])
    assert [g["valor_divergencia_brl"] for g in dossie["grupos"]] == ["15397.42", "1546.28", "1418.85", "29.95"]


def test_respostas_financeiro(grupos):
    ids = {c: [s["id"] for s in g["respostas_financeiro"]] for c, g in grupos.items()}
    assert ids == {CASA: ["S07", "S18", "S37", "S30", "S41", "S51"], ROTA: ["S06", "S51"],
                   BRIDGE: ["S30", "S41", "S51"], MUNDO: ["S05", "S10", "S13", "S30", "S41"]}


def test_fatos_rota(grupos):
    t = _textos(grupos[ROTA])
    assert "Primeira transação divergente em 12/09/2026" in t
    assert "Diferença constante de +0,50 p.p." in t
    assert "Faixas afetadas: crédito à vista (38), 2–6x (31), 7–12x (18)." in t
    assert "sem divergência: débito (7), Pix (10), antecipação (2)" in t     # débito NÃO é afetado
    assert "87 de 87 transações das faixas afetadas divergem (100%)" in t
    assert "linha única do lojista" in t and "53 com data de referência antes de 12/09/2026" in t
    assert ("Em todas as faixas afetadas, a taxa aplicada = contratada +0,50 p.p.: crédito à vista 2,49% → 2,99%; "
            "2–6x 2,99% → 3,49%; 7–12x 3,59% → 4,09%.") in t
    assert ("A aba 'ANTIGO 2025 - nao usar' da planilha (mesmo CNPJ) coincide com a taxa aplicada em 2 de 5 faixas com "
            "transações no período (crédito à vista 2,99%, 2–6x 3,49%); não explica 7–12x (aplicada 4,09%; aba 3,49%), "
            "nem débito (aplicada 1,49%; aba 1,69%) e Pix (aplicada 0,89%; aba 0,99%), que seguiram a taxa contratada "
            "vigente (linha 10, desde 01/01/2026).") in t


def test_fatos_bridge(grupos):
    t = _textos(grupos[BRIDGE])
    assert "Em todas as faixas afetadas" not in t                        # 1 faixa só
    assert "Em todas as faixas afetadas" not in _textos(grupos[CASA])    # diferença varia por faixa
    assert "Primeira transação divergente em 15/09/2026 e última em 18/09/2026 (4 dia(s)" in t
    assert ("Taxa aplicada = vigência anterior do mesmo lojista na planilha (linha 6, até 14/09/2026) em: "
            "crédito à vista 2,59%; a vigente no período (linha 7) é crédito à vista 2,19%.") in t
    assert "Mudança de vigência em 15/09/2026; a divergência começa no mesmo dia (15/09/2026)" in t
    assert "Faixas afetadas: crédito à vista (5)." in t


def test_fatos_casa(grupos):
    g = grupos[CASA]
    t = _textos(g)
    assert g["ec_orbe"] == "1018325654" and g["natureza"] == "ISENCAO_NAO_INFORMADA"
    assert "118 de 118 transações das faixas afetadas divergem (100%)" in t
    assert "a cobrada antes da isenção, em 118 de 118 transações" in t
    assert ("A planilha de taxas não registra a isenção; ela vem do acordo comercial informado pelo financeiro "
            "(S07), válido de 01/09/2026 a 31/12/2026; a divergência começa no mesmo dia.") in t
    assert "config" not in t
    assert "não houve transação do lojista em faixa sem divergência" in t
    # a única transação do mês fora do período é o estorno da venda de agosto (H01), não divergente
    assert "1 com data de referência antes de 01/09/2026), nenhuma divergente" in t


def test_fatos_mundo_aberto(grupos):
    g = grupos[MUNDO]
    t = _textos(g)
    assert g["contraparte"] == "PONTE" and g["ec_orbe"] is None
    assert "coincide com o spread padrão de 1,50% (CC03)" in t and "23 de 23 operações; contratado 1,20%" in t
    assert "Diferença variável de +0,2991 p.p. a +0,3009 p.p." in t
    assert "spread remessa 1,20%" in g["condicao_contratual"]


def test_arquivos_gravados_e_deterministicos(resultado, raiz, tmp_path):
    pasta = resultado["saida"] / "investigacao"
    assert json.loads((pasta / "dossie.json").read_text(encoding="utf-8")) == resultado["investigacao"]
    md = (pasta / "dossie.md").read_text(encoding="utf-8")
    assert md.startswith("# Dossiê de investigação") and "## G01 — Casa do Estudante" in md
    r2 = fechamento.executar(raiz, tmp_path)
    for nome in ("dossie.json", "dossie.md"):
        b = (pasta / nome).read_bytes()
        assert b == (tmp_path / "investigacao" / nome).read_bytes()
        assert b == (raiz / "saida" / "investigacao" / nome).read_bytes(), f"saida/ desatualizada: rode o CLI ({nome})"
        assert b"\r\n" not in b
    assert investigacao.gerar(r2, []) == investigacao.gerar(r2, [])


def test_csvs_nao_dependem_do_dossie(resultado, raiz, tmp_path, monkeypatch):
    sem = tmp_path / "sem"
    fechamento.executar(raiz, sem, investigar=False)
    assert not (sem / "investigacao").exists()

    def explode(*a, **k):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr(investigacao, "gerar", explode)
    quebrado = tmp_path / "quebrado"
    r = fechamento.executar(raiz, quebrado)
    assert r["investigacao"] is None and "falha simulada" in r["investigacao_erro"]
    for nome in COLUNAS:
        b = (resultado["saida"] / nome).read_bytes()
        assert b == (sem / nome).read_bytes() == (quebrado / nome).read_bytes(), nome
