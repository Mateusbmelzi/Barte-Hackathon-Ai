"""Totais contra o gabarito do entendimento (docs/01_entendimento_dados.md §0, §3.5, §9)."""
from decimal import Decimal as D

from src.dinheiro import arred, soma


def _tot(xs, k):
    return soma(x[k] for x in xs)


def test_checkout(resultado):
    chk = [c for c in resultado["comissoes"] if c["linha_negocio"] == "CHECKOUT"]
    assert len(chk) == 21
    assert sum(c["qtd"] for c in chk) == 1900  # inclui 06_orbe_ajustes_tardios
    assert _tot(chk, "comissao") == D("203735.34")  # inclui 06_orbe_ajustes_tardios


def test_notas(resultado):
    n_chk = [n for n in resultado["notas"] if n["linha_negocio"] == "CHECKOUT"]
    n_rem = [n for n in resultado["notas"] if n["linha_negocio"] == "REMESSA"]
    assert len(n_chk) == 20 and _tot(n_chk, "valor") == D("203740.84")  # inclui 06_orbe_ajustes_tardios
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
    pend = [p for p in resultado["pendencias"] if p["tipo"] == "SPREAD_NEGATIVO"]
    assert {r[1] for p in pend for r in p["rastro"]} == negativos      # rastro por operação
    assert all(p["ref_origem"].startswith("CNPJ ") for p in pend)      # 1 pendência por lojista (S38)
    assert len(pend) == len({p["ref_origem"] for p in pend}) == 4      # setembro: 4 lojistas, 1 op cada


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
    assert tipos[("ACOMPANHAR_REMESSA_FUTURA", "MRD2026090425")] == D("18240.00")
    assert tipos[("OPERACAO_DUPLICADA", "PC-0926-0162")] == D("821.88")
    # S43: valor_brl = diferença até o spread contratado (realizado em -1.834,05; ver test_regras_s40_s54)
    assert soma(p["valor"] for p in resultado["pendencias"] if p["tipo"] == "SPREAD_NEGATIVO") == D("-3565.98")
    assert tipos[("CONFERIR_REPASSE_PONTE", "Nota REMESSA")] == D("39543.45")
    assert tipos[("ALERTA_ANTECIPACAO", "EC 1076801732")] == D("183581.24")    # S42/S50: pico líquido de reversões


def test_arquivos_de_origem_intocados(resultado):
    assert resultado["hash_antes"] == resultado["hash_depois"]


def test_fase0_pendencias_s18_s22_s34_s38(resultado):
    """S18/S37 Casa fora da cobrança da Orbe; S34 devolver/recuperar; S22 PIX = remessa futura; S38 Comercial."""
    p = {(x["tipo"], x["ref_origem"]): x for x in resultado["pendencias"]}
    casa = p[("DEVOLUCAO_LOJISTA_ISENCAO", "EC 1018325654")]
    assert casa["valor"] == D("15396.77") and casa["quem_decide"] == "Helena (Financeiro) / Comercial"
    assert "NÃO entra na cobrança da Orbe" in casa["motivo"] and "devolução ao lojista" in casa["motivo"]
    assert not any(x["tipo"] == "DIVERGENCIA_TAXA_CHECKOUT" and x["ref_origem"] == "EC 1018325654"
                   for x in resultado["pendencias"])
    rota = p[("DIVERGENCIA_TAXA_CHECKOUT", "EC 1074504011")]
    assert "Devolver ao lojista R$ 1.545,86; recuperar do parceiro (Orbe) R$ 1.545,86" in rota["motivo"]
    ma = p[("DIVERGENCIA_SPREAD_REMESSA", "CNPJ 17217888000111")]
    assert "Devolver ao lojista R$ 1.418,88; recuperar do parceiro (Ponte) R$ 1.418,88" in ma["motivo"]
    assert "(S30)" in ma["motivo"] and "(S05)" in ma["motivo"]          # B5: caso de fronteira
    assert p[("LOJISTA_SEM_CONTRATO", "EC 1076801732")]["quem_decide"] == "Comercial"
    assert p[("ALERTA_ANTECIPACAO", "EC 1076801732")]["quem_decide"] == "Helena (Financeiro) / Comercial"
    pix = p[("ACOMPANHAR_REMESSA_FUTURA", "MRD2026090425")]
    assert "Adiantamento da Ponte Aérea Estudantil Ltda para remessa prevista no mês seguinte (S22)" in pix["motivo"]
    lan = next(x for x in resultado["lancamentos"] if x["ref"] == "MRD2026090425")
    assert lan["conta"] == "2.1.02.001" and lan["metodo"] == "HUMANO" and lan["confianca"] == D("1.00")
    assert "S22" in lan["observacao"]
    natureza = {(d["lojista"], d["natureza"]) for d in resultado["divergencias"]}
    assert natureza == {("Casa do Estudante Viagens Ltda", "ISENCAO_NAO_INFORMADA"),
                        ("Rota Global Intercâmbio Ltda", "CONTRATO"), ("Escola Bridge de Idiomas Ltda", "CONTRATO"),
                        ("Mundo Aberto", "CONTRATO")}
