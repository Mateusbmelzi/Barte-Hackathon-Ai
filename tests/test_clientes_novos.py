"""Clientes novos: detecção, registro, armazenamento do contrato, 6 CSVs idênticos e taxa do contrato como base."""
import filecmp
import shutil
from pathlib import Path

import pytest

from src import cadastro as cad, clientes_novos as cn, fechamento

RAIZ = Path(__file__).resolve().parent.parent
CSVS = ["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv",
        "lancamentos_classificados.csv", "pendencias.csv", "rastro.csv"]
ATLAS = "39566044000119"


@pytest.fixture()
def pasta(tmp_path):
    p = tmp_path / "cadastro"
    shutil.copytree(RAIZ / "cadastro", p, ignore=shutil.ignore_patterns("contratos"))
    return p


def test_atlas_aparece_como_contrato_pendente(resultado):
    novos = {c["cnpj"]: c for c in resultado["clientes_novos"]}
    assert set(novos) == {ATLAS}
    a = novos[ATLAS]
    assert a["status"] == "CONTRATO_PENDENTE" and a["origem"] == "ORBE" and a["ec_orbe"] == "1076801732"
    assert a["qtd_transacoes"] > 0 and "." in a["valor_bruto"] and len(a["valor_bruto"].split(".")[1]) == 2


def test_fluente_e_lojistas_da_planilha_nao_sao_novos(resultado):
    cnpjs = {c["cnpj"] for c in cn.detectar(resultado["dados"], RAIZ / "cadastro")}
    assert "03229837000103" not in cnpjs          # Fluente
    assert "00520815000100" not in cnpjs          # Casa do Estudante
    assert "66564512000199" not in cnpjs          # Novo Horizonte (de-para)


def test_cliente_inventado_na_orbe_aparece(resultado):
    d = dict(resultado["dados"])
    inventado = dict(d["orbe"][0], ec="9999999999", nome="LOJA NOVA FICTICIA", id="TXNOVA")
    d["orbe"] = list(d["orbe"]) + [inventado]
    novos = {c["ec_orbe"]: c for c in cn.detectar(d, RAIZ / "cadastro")}
    assert novos["9999999999"]["status"] == "CONTRATO_PENDENTE"
    assert novos["9999999999"]["nome"] == "LOJA NOVA FICTICIA" and novos["9999999999"]["qtd_transacoes"] == 1
    assert novos["9999999999"]["cnpj"] == ""


def test_cliente_novo_na_ponte_por_cnpj(resultado):
    d = dict(resultado["dados"])
    d["ponte"] = list(d["ponte"]) + [dict(d["ponte"][0], cnpj="11222333000181", cliente="AURORA INTERCAMBIO")]
    novos = {c["cnpj"]: c for c in cn.detectar(d, RAIZ / "cadastro")}
    assert novos["11222333000181"]["origem"] == "PONTE"


def test_sem_registro_nao_detecta(resultado, tmp_path):
    assert cn.detectar(resultado["dados"], tmp_path) == []


def test_ciclo_de_status_e_crescimento(resultado, pasta):
    d = dict(resultado["dados"])
    d["orbe"] = list(d["orbe"]) + [dict(d["orbe"][0], ec="9999999999", nome="LOJA NOVA", id="TXNOVA")]
    novo = [c for c in cn.detectar(d, pasta) if c["ec_orbe"] == "9999999999"][0]
    cn.adicionar_novo(pasta, novo, "helena")
    assert cn.adicionar_novo(pasta, novo, "helena")["ec_orbe"] == "9999999999"      # idempotente
    assert len([l for l in cn.ler(pasta) if l["ec_orbe"] == "9999999999"]) == 1
    cn.registrar_contrato(pasta, ATLAS, "contrato_atlas.pdf", "helena")
    a = [l for l in cn.ler(pasta) if l["cnpj"] == ATLAS][0]
    assert a["status"] == "CONTRATO_ANALISADO" and a["contrato_arquivo"] == "contrato_atlas.pdf"
    assert [c["status"] for c in cn.detectar(d, pasta) if c["cnpj"] == ATLAS] == ["CONTRATO_ANALISADO"]
    cn.marcar(pasta, ATLAS, "CONFIRMADO", "helena")
    assert ATLAS not in {c["cnpj"] for c in cn.detectar(d, pasta)}
    with pytest.raises(cn.ClienteInvalido):
        cn.marcar(pasta, ATLAS, "QUALQUER", "helena")
    with pytest.raises(cn.ClienteInvalido):
        cn.marcar(pasta, "00000000000000", "CONFIRMADO", "helena")


def test_guardar_contrato_nao_sobrescreve(tmp_path):
    n1 = cn.guardar_contrato(tmp_path, "39.566.044/0001-19", "contrato.txt", b"v1")
    n2 = cn.guardar_contrato(tmp_path, ATLAS, "contrato.txt", b"v2")
    assert (n1, n2) == ("contrato.txt", "contrato_v2.txt")
    assert (tmp_path / "contratos" / ATLAS / "contrato.txt").read_bytes() == b"v1"
    assert (tmp_path / "contratos" / ATLAS / "contrato_v2.txt").read_bytes() == b"v2"
    n3 = cn.guardar_contrato(tmp_path, ATLAS, "../../fuga.txt", b"x")
    assert n3 == "fuga.txt"


def test_seis_csvs_identicos_a_saida(resultado, tmp_path):
    """Com a detecção ligada (padrão), os 6 CSVs e o dossiê seguem idênticos byte a byte à saida/ versionada."""
    for nome in CSVS:
        assert (resultado["saida"] / nome).read_bytes() == (RAIZ / "saida" / nome).read_bytes(), nome
    dossie = RAIZ / "saida" / "investigacao"
    if dossie.exists():
        cmp = filecmp.dircmp(dossie, resultado["saida"] / "investigacao")
        assert not cmp.diff_files and not cmp.left_only and not cmp.right_only


def test_taxa_do_contrato_vira_base_para_lojista_sem_planilha(pasta, tmp_path):
    """Atlas sem linha na planilha: com o bloqueio encerrado e TAXA_ESPECIAL no cadastro, a taxa do cadastro é a base."""
    antes = fechamento.executar(RAIZ, tmp_path / "a", investigar=False, cadastro=pasta)
    assert all(c["cnpj"] != ATLAS for c in antes["comissoes"])           # bloqueada pelo C005 (como em setembro)
    arq = pasta / "condicoes_comerciais.csv"      # simula o Comercial encerrar o bloqueio C005 (cópia de teste)
    arq.write_text(arq.read_text(encoding="utf-8").replace("BLOQUEIO_FATURAMENTO;39566044000119;1076801732;Atlas Idiomas;CHECKOUT;;;2026-09-10;",
                                                           "BLOQUEIO_FATURAMENTO;39566044000119;1076801732;Atlas Idiomas;CHECKOUT;;;2026-10-01;"), encoding="utf-8")
    cad.adicionar_varias(pasta, [
        {"tipo": "TAXA_ESPECIAL", "cnpj": ATLAS, "ec_orbe": "1076801732", "lojista": "Atlas Idiomas",
         "linha_negocio": "CHECKOUT", "campo": f, "valor": v, "vigencia_inicio": "2026-09-01", "aprovado_por": "Comercial",
         "fonte": "contrato teste"}
        for f, v in [("DEBITO", "1.50"), ("CREDITO A VISTA", "2.50"), ("PARC_2_6", "3.00"), ("PARC_7_12", "3.50"),
                     ("PIX", "0.90"), ("ANTECIPACAO", "2.00")]], "teste")
    r = fechamento.executar(RAIZ, tmp_path / "b", investigar=False, cadastro=pasta)
    com = [c for c in r["comissoes"] if c["cnpj"] == ATLAS]
    assert com and com[0]["lojista"] == "Atlas Idiomas" and com[0]["comissao"] > 0
    assert all(l["status"] == "FATURAVEL" for l in r["checkout"] if l["ec"] == "1076801732")
    # quem tem linha na planilha não muda: mesmas comissões dos demais
    base = {c["cnpj"]: c["comissao"] for c in antes["comissoes"]}
    assert {c["cnpj"]: c["comissao"] for c in r["comissoes"] if c["cnpj"] != ATLAS} == base


def test_valores_do_cliente_novo_separam_vendas_e_antecipacoes(resultado):
    a = next(c for c in resultado["clientes_novos"] if c["cnpj"] == ATLAS)
    assert a["valor_bruto"] == a["valor_bruto_vendas"] == "135428.90"
    assert a["qtd_vendas"] <= a["qtd_transacoes"] and a["qtd_vendas"] > 0
    assert "." in a["valor_bruto_antecipacoes"]
