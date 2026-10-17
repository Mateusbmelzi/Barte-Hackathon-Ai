"""Orbe em 1 ou N arquivos no mesmo mês (relatório + ajustes tardios). Tudo em tmp_path: independe dos
arquivos da raiz e não muda com o conteúdo de setembro."""
import csv
import shutil
from decimal import Decimal as D

import pytest

from src import config, fechamento, leitores

CAB = ("id_transacao;data_movimento;cod_estabelecimento;nome_estabelecimento;tipo_lancamento;modalidade;"
       "qtd_parcelas;bandeira;valor_bruto;taxa_aplicada_pct;valor_taxa;valor_liquido;id_referencia;data_venda_original")
EC = "1000960410"   # Oxford, contrato vigente na planilha da raiz

VENDA = f"TXA0001;10/09/2026;{EC};OXFORD;VENDA;CREDITO A VISTA;1;VISA;1000,00;2,59;25,90;974,10;;"
ANTEC = f"ANA0001;11/09/2026;{EC};OXFORD;ANTECIPACAO;;;;2000,00;2,10;42,00;1958,00;;"
EST1 = f"TXB0001;30/09/2026;{EC};OXFORD;ESTORNO;CREDITO A VISTA;1;VISA;-1000,00;2,59;-25,90;-974,10;TXA0001;10/09/2026"
EST2 = f"TXB0002;30/09/2026;{EC};OXFORD;ESTORNO;CREDITO A VISTA;1;VISA;-1000,00;2,59;-25,90;-974,10;TXA0001;10/09/2026"
REV1 = f"ANB0001;30/09/2026;{EC};OXFORD;REVERSAO ANTECIPACAO;;;;-2000,00;2,10;-42,00;-1958,00;ANA0001;11/09/2026"


def _csv(pasta, nome, *linhas):
    (pasta / nome).write_text("\r\n".join([CAB, *linhas]) + "\r\n", encoding="utf-8")
    return pasta / nome


def _entrada(raiz, destino, orbes):
    """Os 5 arquivos não-Orbe da raiz + os arquivos Orbe dados {nome: [linhas]}."""
    destino.mkdir(exist_ok=True)
    for k, p in leitores.descobrir_arquivos(raiz).items():
        if k != "orbe":
            shutil.copy(p, destino / p.name)
    for nome, linhas in orbes.items():
        _csv(destino, nome, *linhas)
    return destino


# ---------------------------------------------------------------- leitura
def test_descobre_todos_os_orbe_em_ordem_de_nome(raiz, tmp_path):
    ent = _entrada(raiz, tmp_path / "e", {"orbe_b.csv": [EST1], "orbe_a.csv": [VENDA]})
    arq = leitores.descobrir_arquivos(ent)
    assert [p.name for p in arq["orbe"]] == ["orbe_a.csv", "orbe_b.csv"]
    assert not isinstance(arq["taxas"], list)


def test_sem_nenhum_orbe_continua_erro(raiz, tmp_path):
    ent = _entrada(raiz, tmp_path / "e", {})
    with pytest.raises(FileNotFoundError, match="orbe"):
        leitores.descobrir_arquivos(ent)


def test_concatena_e_guarda_arquivo_origem(tmp_path):
    b = _csv(tmp_path, "orbe_b_ajustes.csv", EST1)
    a = _csv(tmp_path, "orbe_a.csv", VENDA, ANTEC)
    linhas, dup = leitores.ler_orbe_varios([b, a])       # ordem dada não importa: vale a ordem de nome
    assert [l["id"] for l in linhas] == ["TXA0001", "ANA0001", "TXB0001"] and dup == []
    assert [l["arquivo"] for l in linhas] == ["orbe_a.csv", "orbe_a.csv", "orbe_b_ajustes.csv"]
    assert [l["linha"] for l in linhas] == [2, 3, 2]     # linha física dentro do próprio arquivo


def test_id_repetido_entre_arquivos_conta_uma_vez(tmp_path):
    a = _csv(tmp_path, "orbe_a.csv", VENDA)
    b = _csv(tmp_path, "orbe_b.csv", VENDA, VENDA.replace("1000,00", "999,00"))   # repete igual e repete diferente
    linhas, dup = leitores.ler_orbe_varios([a, b])
    # S52: a idêntica sai (conta uma vez); a de valor diferente do arquivo posterior (ajuste) SUBSTITUI a anterior
    assert len(linhas) == 1 and linhas[0]["arquivo"] == "orbe_b.csv" and linhas[0]["bruto"] == D("999.00")
    assert [(d["arquivo"], d["identica"]) for d in dup] == [("orbe_b.csv", True), ("orbe_a.csv", False)]
    assert dup[1]["original"] is linhas[0] and dup[0]["original"]["arquivo"] == "orbe_a.csv"


def test_id_repetido_no_mesmo_arquivo(tmp_path):
    a = _csv(tmp_path, "orbe_a.csv", VENDA, VENDA)
    linhas, dup = leitores.ler_orbe_varios(a)
    assert len(linhas) == 1 and len(dup) == 1 and dup[0]["linha"] == 3


# ---------------------------------------------------------------- fechamento
@pytest.fixture(scope="module")
def dois_arquivos(raiz, tmp_path_factory):
    base = tmp_path_factory.mktemp("dois")
    ent = _entrada(raiz, base / "ent", {"orbe_a.csv": [VENDA, ANTEC], "orbe_b.csv": [EST1, REV1, VENDA]})
    r = fechamento.executar(ent, base / "saida", investigar=False)
    return r, base / "saida"


def _pend(r, tipo):
    return [p for p in r["pendencias"] if p["tipo"] == tipo]


def _comissao(r, id_):
    return next(l for l in r["checkout"] if l["id"] == id_)


def test_estorno_em_outro_arquivo_anula_a_venda(dois_arquivos):
    r, _ = dois_arquivos
    v, e = _comissao(r, "TXA0001"), _comissao(r, "TXB0001")
    assert v["status"] == e["status"] == "FATURAVEL" and e["comissao"] == -v["comissao"] != 0
    a, rv = _comissao(r, "ANA0001"), _comissao(r, "ANB0001")
    assert rv["comissao"] == -a["comissao"] != 0


def test_linha_repetida_vira_pendencia_e_nao_conta_em_dobro(dois_arquivos):
    r, _ = dois_arquivos
    assert sum(1 for l in r["checkout"] if l["id"] == "TXA0001") == 1
    p = _pend(r, "ORBE_LINHA_DUPLICADA")
    assert len(p) == 1 and p[0]["ref_origem"] == "TXA0001" and "orbe_a.csv" in p[0]["motivo"]
    assert p[0]["rastro"][0][0] == "orbe@orbe_b.csv"


def test_rastro_aponta_arquivo_certo(dois_arquivos):
    _, saida = dois_arquivos
    with open(saida / "rastro.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    por_ref = {}
    for x in rows:
        por_ref.setdefault(x["ref_origem"], set()).add(x["arquivo_origem"])
    assert por_ref["TXA0001"] == {"orbe_a.csv", "orbe_b.csv"}   # a original (a) e a repetição ignorada (b)
    assert por_ref["TXB0001"] == {"orbe_b.csv"} and por_ref["ANB0001"] == {"orbe_b.csv"}
    assert por_ref["ANA0001"] == {"orbe_a.csv"}


def test_dupla_reversao_nao_aplica_e_abre_pendencia(raiz, tmp_path):
    ent = _entrada(raiz, tmp_path / "e", {"orbe_a.csv": [VENDA, ANTEC], "orbe_b.csv": [EST1, EST2]})
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    e1, e2 = _comissao(r, "TXB0001"), _comissao(r, "TXB0002")
    assert e1["status"] == "FATURAVEL" and e2["status"] == "EXCLUIDA" and e2["motivo"] == "ESTORNO_DUPLICADO"
    p = _pend(r, "ORBE_ESTORNO_DUPLICADO")
    assert len(p) == 1 and p[0]["ref_origem"] == "TXB0002" and p[0]["valor"] == D("-25.90")
    assert "NÃO aplicada" in p[0]["motivo"]
    assert not _pend(r, "TAXA_CONTRATADA_INDEFINIDA")        # não vira "sem taxa"
    chk = [c for c in r["comissoes"] if c["ec_orbe"] == EC][0]
    assert chk["comissao"] == _comissao(r, "ANA0001")["comissao"]        # venda + estorno = 0; sobra a antecipação


def test_dupla_reversao_aplicada_se_o_parametro_mandar(raiz, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APLICAR_ESTORNO_DUPLICADO", True)
    ent = _entrada(raiz, tmp_path / "e", {"orbe_a.csv": [VENDA], "orbe_b.csv": [EST1, EST2]})
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    assert _comissao(r, "TXB0002")["status"] == "FATURAVEL"
    p = _pend(r, "ORBE_ESTORNO_DUPLICADO")
    assert len(p) == 1 and "Aplicada mesmo assim" in p[0]["motivo"]


def test_um_arquivo_orbe_continua_funcionando(raiz, tmp_path):
    ent = _entrada(raiz, tmp_path / "e", {"so_orbe.csv": [VENDA]})
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    assert [l["id"] for l in r["checkout"]] == ["TXA0001"] and not _pend(r, "ORBE_LINHA_DUPLICADA")
