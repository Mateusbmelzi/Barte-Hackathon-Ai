"""Totais contra o gabarito do entendimento (docs/01_entendimento_dados.md §0, §3.5, §9)."""
from decimal import Decimal as D

from src.dinheiro import arred, soma


def _tot(xs, k):
    return soma(x[k] for x in xs)


def test_checkout(resultado):
    chk = [c for c in resultado["comissoes"] if c["linha_negocio"] == "CHECKOUT"]
    assert len(chk) == 21
    assert sum(c["qtd"] for c in chk) == 1886
    assert _tot(chk, "comissao") == D("207039.73")


def test_notas(resultado):
    n_chk = [n for n in resultado["notas"] if n["linha_negocio"] == "CHECKOUT"]
    n_rem = [n for n in resultado["notas"] if n["linha_negocio"] == "REMESSA"]
    assert len(n_chk) == 20 and _tot(n_chk, "valor") == D("207045.23")
    assert len(n_rem) == 1 and n_rem[0]["tomador_cnpj"] == "75374179000146"
    assert n_rem[0]["valor"] == D("39543.45")


def test_divergencias_checkout(resultado):
    d = [x for x in resultado["divergencias"] if x["linha_negocio"] == "CHECKOUT"]
    assert len(d) == 210 and _tot(d, "diferenca") == D("16973.65")


def test_remessa(resultado):
    rem = [c for c in resultado["comissoes"] if c["linha_negocio"] == "REMESSA"]
    assert len(rem) == 14
    assert sum(c["qtd"] for c in rem) == 228
    assert _tot(rem, "comissao") == D("39543.45")


def test_divergencia_remessa(resultado):
    d = [x for x in resultado["divergencias"] if x["linha_negocio"] == "REMESSA"]
    ma = [x for x in d if x["cnpj"] == "17217888000111"]
    assert len(ma) == 23 and _tot(ma, "diferenca") == D("1418.85")
    assert len(d) == 23                                  # sem alarme de centavo (H06) e sem negativos (H08 revisada)
    negativos = {"PC-0926-0210", "PC-0926-0326", "PC-0926-0491", "PC-0926-0545"}
    assert not negativos & {x["ref_origem"] for x in d}
    pend = {p["ref_origem"] for p in resultado["pendencias"] if p["tipo"] == "SPREAD_NEGATIVO"}
    assert pend == negativos


def test_extratos(resultado):
    l = resultado["lancamentos"]
    assert sum(1 for x in l if x["banco"] == "AURORA") == 84
    assert sum(1 for x in l if x["banco"] == "MERIDIANO") == 100
    plano = resultado["dados"]["plano"]
    assert all(plano[x["conta"]]["aceita"] for x in l)


def test_casos_pontuais(resultado):
    chk = {l["id"]: l for l in resultado["checkout"]}
    # estorno de agosto da Oxford: taxa contratada da venda original (7-12x 3,79%)
    tx = chk["TX88444848"]
    assert tx["status"] == "FATURAVEL" and tx["contratada"] == D("3.79")
    assert tx["comissao"] == arred(D("-2193.16") * D("3.79") / 100) == D("-83.12")
    assert not tx["divergente"]
    # Casa: estorno de agosto abate à taxa de agosto (H01) e a Casa fecha em -5,50 sem nota
    assert chk["TX88445133"]["comissao"] == D("-5.50")
    casa = next(c for c in resultado["comissoes"] if c["cnpj"] == "00520815000100" and c["linha_negocio"] == "CHECKOUT")
    assert casa["comissao"] == D("-5.50")
    assert not any(n["tomador_cnpj"] == "00520815000100" for n in resultado["notas"])
    assert any(p["tipo"] == "SALDO_CHECKOUT_NAO_POSITIVO" and p["valor"] == D("-5.50") for p in resultado["pendencias"])
    # Atlas fora de comissões e notas
    assert all(l["status"] == "EXCLUIDA" for l in resultado["checkout"] if l["ec"] == "1076801732")
    assert not any(n["tomador_cnpj"] == "39566044000119" for n in resultado["notas"])


def test_remessa_pontual(resultado):
    rem = resultado["remessa"]
    dup = [o for o in rem if o["op"] == "PC-0926-0162"]
    assert [o["status"] for o in dup] == ["VALIDA", "DUPLICATA"]          # contada 1x
    neg = next(o for o in rem if o["op"] == "PC-0926-0210")
    assert neg["status"] == "NEGATIVA"
    rastro_nota = next(n for n in resultado["notas"] if n["linha_negocio"] == "REMESSA")["rastro"]
    refs = [r[1] for r in rastro_nota]
    assert "PC-0926-0210" not in refs and refs.count("PC-0926-0162") == 1


def test_lancamento_aurora_ref(resultado):
    l = {x["ref"]: x for x in resultado["lancamentos"] if x["banco"] == "AURORA"}
    assert l["L9"]["valor"] == D("66026.00") and l["L9"]["conta"] == "1.1.03.001"
    assert l["L50"]["valor"] == D("7350.00") and l["L50"]["conta"] == "1.1.09.002"
    assert l["L92"]["valor"] == D("-300000.00") and l["L92"]["conta"] == "1.1.09.001"


def test_pendencias_esperadas(resultado):
    tipos = {(p["tipo"], p["ref_origem"]): p["valor"] for p in resultado["pendencias"]}
    assert tipos[("CREDITO_NAO_IDENTIFICADO", "L50")] == D("7350.00")
    assert tipos[("DEVOLUCAO_REPASSE", "L65")] == D("12400.00")
    assert tipos[("TRANSFERENCIA_EM_TRANSITO", "L92")] == D("-300000.00")
    assert tipos[("PIX_LOJISTA_SEM_OPERACAO", "MRD2026090425")] == D("18240.00")
    assert tipos[("OPERACAO_DUPLICADA", "PC-0926-0162")] == D("821.88")
    assert soma(p["valor"] for p in resultado["pendencias"] if p["tipo"] == "SPREAD_NEGATIVO") == D("-1834.05")
    assert tipos[("CONFERIR_REPASSE_PONTE", "Nota REMESSA")] == D("39543.45")
    assert tipos[("RISCO_ANTECIPACAO", "EC 1076801732")] == D("179592.82")


def test_arquivos_de_origem_intocados(resultado):
    assert resultado["hash_antes"] == resultado["hash_depois"]
