"""Outubro simulado: cópia dos dados em tmp_path com
(a) data_movimento da Orbe deslocada para 10/2026 (data_venda_original preservada),
(b) lojista novo na Orbe com EC fora da planilha,
(c) lançamento Aurora com descrição desconhecida.
Os arquivos originais não são tocados."""
import shutil
from decimal import Decimal as D

import pytest

from src import fechamento
from src.leitores import descobrir_arquivos

EC_NOVO = "1999999999"
EC_VELA = "1086291869"   # lojista existente; venda em 18x (S38: não vendem acima de 12x)


def _orbe_outubro(origem, destino, extras=True):
    linhas = origem.read_text(encoding="utf-8").splitlines()
    out = [linhas[0]]
    for l in linhas[1:]:
        c = l.split(";")
        c[1] = c[1].replace("/09/2026", "/10/2026")      # só data_movimento
        out.append(";".join(c))
    if extras:
        out.append(f"TX99000001;10/10/2026;{EC_NOVO};ESCOLA NOVA IDIOMAS;VENDA;CREDITO A VISTA;1;VISA;"
                   "1000,00;2,69;26,90;973,10;;")
        out.append(f"TX99000002;11/10/2026;{EC_VELA};VELA;VENDA;CREDITO PARCELADO;18;VISA;"
                   "1000,00;3,79;37,90;962,10;;")
    destino.write_text("\r\n".join(out) + "\r\n", encoding="utf-8")


def _aurora_com_desconhecido(origem, destino):
    linhas = origem.read_text(encoding="utf-8").split("\n")
    i = max(n for n, l in enumerate(linhas) if l[:2].isdigit())        # último lançamento
    saldo = linhas[i].split(";")[4]
    linhas.insert(i + 1, f"30/09/2026;COBRANCA MISTERIOSA XYZ;;0,00;{saldo}")   # valor zero: saldo segue fechando
    destino.write_text("\n".join(linhas), encoding="utf-8")


@pytest.fixture(scope="module")
def outubro(raiz, tmp_path_factory):
    ent = tmp_path_factory.mktemp("entrada_out")
    arq = descobrir_arquivos(raiz)
    for k, p in arq.items():
        if k == "orbe":
            for i, q in enumerate(p):
                _orbe_outubro(q, ent / f"orbe_out2026_{i}.csv", extras=(i == 0))
        elif k == "aurora":
            _aurora_com_desconhecido(p, ent / "extrato_aurora_out2026.csv")
        else:
            shutil.copy(p, ent / p.name)
    return fechamento.executar(ent, tmp_path_factory.mktemp("saida_out"))


def test_competencia_outubro(outubro):
    assert outubro["competencia"] == "10/2026"


def test_lojista_novo_vira_pendencia_e_fica_fora(outubro):
    linha = next(l for l in outubro["checkout"] if l["ec"] == EC_NOVO)
    assert linha["status"] == "EXCLUIDA"
    p = [p for p in outubro["pendencias"] if p["ref_origem"] == f"EC {EC_NOVO}"]
    assert len(p) == 1 and p[0]["tipo"] == "TAXA_CONTRATADA_INDEFINIDA" and p[0]["valor"] == D("26.90")
    assert all(l["status"] == "EXCLUIDA" for l in outubro["checkout"] if l["ec"] == EC_NOVO)
    assert sum(len(n["rastro"]) for n in outubro["notas"] if n["linha_negocio"] == "CHECKOUT") == \
        sum(1 for l in outubro["checkout"] if l["status"] == "FATURAVEL" and l["cnpj"] != "00520815000100")


def test_lancamento_desconhecido_humano(outubro):
    l = next(x for x in outubro["lancamentos"] if x["descricao"] == "COBRANCA MISTERIOSA XYZ")
    assert l["metodo"] == "HUMANO" and l["conta"] == "1.1.09.002"
    assert any(p["tipo"] == "LANCAMENTO_NAO_CLASSIFICADO" and p["ref_origem"] == l["ref"] for p in outubro["pendencias"])
    assert not any(p["tipo"] == "EXTRATO_NAO_FECHA" for p in outubro["pendencias"])


def test_casa_continua_taxa_zero(outubro):
    casa = [l for l in outubro["checkout"] if l["ec"] == "1018325654" and l["tipo"] in ("VENDA", "ANTECIPACAO")]
    assert casa and all(l["contratada"] == 0 for l in casa)


def test_remessa_de_setembro_fica_fora_de_outubro(outubro):
    # o relatório da Ponte copiado ainda é de setembro: nada entra na comissão de outubro (R03)
    assert not [n for n in outubro["notas"] if n["linha_negocio"] == "REMESSA"]
    fora = [p for p in outubro["pendencias"] if p["tipo"] == "REMESSA_FORA_COMPETENCIA"]
    assert len(fora) == 1                     # agregada, não 1 por operação


def test_rastro_fecha(outubro):
    for grupo, k in [("comissoes", "comissao"), ("divergencias", "diferenca"), ("notas", "valor"),
                     ("lancamentos", "valor"), ("pendencias", "valor")]:
        for it in outubro[grupo]:
            if it[k] is not None:
                assert sum((r[2] for r in it["rastro"]), D("0")) == it[k], it["id"]


def test_parcelamento_acima_de_12x_vira_pendencia(outubro):
    linha = next(l for l in outubro["checkout"] if l["id"] == "TX99000002")
    assert linha["status"] == "EXCLUIDA" and linha["motivo"] == "ACIMA_12X"
    p = [p for p in outubro["pendencias"] if p["tipo"] == "PARCELAMENTO_ACIMA_12X"]
    assert len(p) == 1 and p[0]["ref_origem"] == f"EC {EC_VELA}" and p[0]["valor"] == D("37.90")
    assert not any(r[1] == "TX99000002" for c in outubro["comissoes"] for r in c["rastro"])
