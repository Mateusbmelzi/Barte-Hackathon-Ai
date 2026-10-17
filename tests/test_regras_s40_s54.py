"""Respostas S40-S54 do financeiro (17/10/2026) no checkout, remessa e dossiê. Setembro (arquivos da raiz) e
cenários simulados em tmp_path; os arquivos originais não são tocados."""
import csv
import io
import shutil
from datetime import date, datetime
from decimal import Decimal as D
from email.message import EmailMessage

import openpyxl
import pytest

from src import checkout, config, fechamento, leitores
from src.dinheiro import soma

CASA_EC, CASA = "1018325654", "00520815000100"
ATLAS_EC, ATLAS_CNPJ = "1076801732", "39566044000119"
OXFORD_EC = "1000960410"


def _pend(r, tipo):
    return [p for p in r["pendencias"] if p["tipo"] == tipo]


# ================================================================ S43 — spread negativo: dois valores
def test_s43_spread_negativo_mostra_os_dois_valores(resultado):
    pend = {p["ref_origem"]: p for p in _pend(resultado, "SPREAD_NEGATIVO")}
    ponte_aerea = pend["CNPJ 95739378000118"]
    assert ponte_aerea["valor"] == D("-1351.87")                      # diferença até o contratado = o que se pede à Ponte
    assert "Spread realizado no relatório: R$ -687,52" in ponte_aerea["motivo"]
    assert "Diferença até o spread contratado" in ponte_aerea["motivo"] and "R$ -1.351,87" in ponte_aerea["motivo"]
    assert "estimado D-1" not in ponte_aerea["motivo"]
    assert ponte_aerea["rastro"] == [("ponte", "PC-0926-0210", D("-1351.87"), "Diferença até o spread contratado")]
    realizado = soma(o["spread_brl"] for o in resultado["remessa"] if o["status"] == "NEGATIVA")
    assert realizado == D("-1834.05")
    assert soma(p["valor"] for p in pend.values()) == D("-3565.98")
    for p in pend.values():                                           # soma do rastro = valor reportado
        assert soma(r[2] for r in p["rastro"]) == p["valor"]


def test_s43_a_formula_e_realizado_menos_contratado_x_ptax_x_me(resultado):
    for o in resultado["remessa"]:
        if o["status"] == "NEGATIVA":
            assert o["dif_contrato"] == (o["spread_brl"] - o["contratado"] * o["ptax"] * o["valor_me"]).quantize(D("0.01"))
            assert o["dif_contrato"] < o["spread_brl"] < 0


# ================================================================ S51 — devolução = o que saiu do bolso
def test_s51_checkout_devolver_e_valor_taxa_menos_comissao(resultado):
    p = {(x["tipo"], x["ref_origem"]): x for x in resultado["pendencias"]}
    casa = p[("DEVOLUCAO_LOJISTA_ISENCAO", f"EC {CASA_EC}")]
    assert casa["valor"] == D("15396.77")
    assert "R$ 15.397,42" in casa["motivo"] and "truncamento da Orbe" in casa["motivo"]
    rota = p[("DIVERGENCIA_TAXA_CHECKOUT", "EC 1074504011")]
    bridge = p[("DIVERGENCIA_TAXA_CHECKOUT", "EC 1075624862")]
    assert (rota["valor"], bridge["valor"]) == (D("1545.86"), D("29.94"))
    for x in (casa, rota, bridge):
        assert soma(r[2] for r in x["rastro"]) == x["valor"]
    # recomputado direto das linhas
    for ec, esperado in ((CASA_EC, casa["valor"]), ("1074504011", rota["valor"]), ("1075624862", bridge["valor"])):
        ls = [l for l in resultado["checkout"] if l["status"] == "FATURAVEL" and l["ec"] == ec and l["divergente"]]
        assert soma(l["valor_taxa"] - l["comissao"] for l in ls) == esperado
    # a lista de divergências continua pela fórmula (S11)
    d = [x for x in resultado["divergencias"] if x["linha_negocio"] == "CHECKOUT"]
    assert soma(x["diferenca"] for x in d) == D("16973.65")
    assert soma(x["diferenca"] for x in d if x["cnpj"] == CASA) == D("15397.42")


def test_s51_dossie_devolver_e_recuperar(resultado):
    g = {x["cnpj"]: x for x in resultado["investigacao"]["grupos"]}
    assert g[CASA]["valor_divergencia_brl"] == "15397.42"
    assert g[CASA]["valor_devolver_lojista_brl"] == "15396.77" and g[CASA]["valor_recuperar_parceiro_brl"] == "0.00"
    rota = g["95927868000148"]
    assert rota["valor_devolver_lojista_brl"] == rota["valor_recuperar_parceiro_brl"] == "1545.86"
    assert rota["valor_divergencia_brl"] == "1546.28"


def test_s51_remessa_mundo_aberto_pelo_spread_cobrado_a_mais(resultado):
    ma = [o for o in resultado["remessa"] if o["divergente"] and o["cnpj"] == "17217888000111"]
    assert len(ma) == 23
    a_mais = soma((o["spread_brl"] - o["contratado"] * o["ptax"] * o["valor_me"]).quantize(D("0.01")) for o in ma)
    p = next(x for x in _pend(resultado, "DIVERGENCIA_SPREAD_REMESSA") if x["ref_origem"] == "CNPJ 17217888000111")
    assert p["valor"] == a_mais == D("1418.88")
    assert "Devolver ao lojista R$ 1.418,88; recuperar do parceiro (Ponte) R$ 1.418,88" in p["motivo"]
    assert soma(r[2] for r in p["rastro"]) == p["valor"]
    g = next(x for x in resultado["investigacao"]["grupos"] if x["cnpj"] == "17217888000111")
    assert g["valor_divergencia_brl"] == "1418.85" and g["valor_devolver_lojista_brl"] == "1418.88"
    d = [x for x in resultado["divergencias"] if x["cnpj"] == "17217888000111"]
    assert soma(x["diferenca"] for x in d) == D("1418.85")             # CSV segue a fórmula (S11)


def test_s51_comissoes_e_notas_de_setembro_nao_mudam(resultado):
    chk = [c for c in resultado["comissoes"] if c["linha_negocio"] == "CHECKOUT"]
    rem = [c for c in resultado["comissoes"] if c["linha_negocio"] == "REMESSA"]
    assert soma(c["comissao"] for c in chk) == D("203735.34") and soma(c["comissao"] for c in rem) == D("39543.45")
    assert soma(n["valor"] for n in resultado["notas"] if n["linha_negocio"] == "CHECKOUT") == D("203740.84")


# ================================================================ S41 — textos
def test_s41_textos_de_natureza(resultado):
    casa = _pend(resultado, "DEVOLUCAO_LOJISTA_ISENCAO")[0]
    assert "concessão comercial fora do contrato" in casa["motivo"].lower()
    assert "devolução sai do bolso da Tarvo" in casa["motivo"]
    for p in _pend(resultado, "DIVERGENCIA_TAXA_CHECKOUT") + _pend(resultado, "DIVERGENCIA_SPREAD_REMESSA"):
        assert "condição contratada" in p["motivo"] and "não o aviso" in p["motivo"]
    # o valor do campo natureza nos CSVs não muda
    assert {d["natureza"] for d in resultado["divergencias"]} == {"CONTRATO", "ISENCAO_NAO_INFORMADA"}
    g = next(x for x in resultado["investigacao"]["grupos"] if x["cnpj"] == CASA)
    assert g["natureza"] == "ISENCAO_NAO_INFORMADA"
    assert "S41" in [s["id"] for s in g["respostas_financeiro"]]


# ================================================================ S42/S50 — alerta de antecipação
def test_s42_so_a_atlas_acende_em_setembro(resultado):
    alertas = _pend(resultado, "ALERTA_ANTECIPACAO")
    assert [a["ref_origem"] for a in alertas] == [f"EC {ATLAS_EC}"]
    a = alertas[0]
    assert a["valor"] == D("183581.24") and soma(r[2] for r in a["rastro"]) == a["valor"]
    for trecho in ("Pico de antecipação acumulada de R$ 183.581,24 em 24/09/2026", "Reversões posteriores ao pico: 1",
                   "saldo líquido de antecipação no fim do mês R$ 127.230,96", ATLAS_CNPJ):
        assert trecho in a["motivo"]


def test_s42_regra_antiga_acenderia_seis_lojistas(resultado, monkeypatch):
    monkeypatch.setattr(config, "ALERTA_ANTECIPACAO_SO_LOJISTA_NOVO", False)
    ecs = {a["ref_origem"][3:] for a in checkout.alertas_antecipacao(resultado["checkout"])}
    # Oxford, Kiwi, Dublin, Canguru, Mundo Aberto e Atlas: lojista demais (S42)
    assert len(ecs) == 6 and ATLAS_EC in ecs and OXFORD_EC in ecs


def _l(id_, ec, tipo, data, bruto, **kw):
    base = dict(id=id_, ec=ec, nome=f"LOJA {ec}", tipo=tipo, data=data, bruto=D(bruto), id_ref=None, data_orig=None,
                modalidade="CREDITO A VISTA", parcelas=1, status="FATURAVEL")
    base.update(kw)
    return base


def test_s42_lojista_novo_com_contrato_tambem_acende_e_antigo_nao():
    d = date
    linhas = [
        # NOVO (EC 1): primeira transação em 10/10, antecipa 1000 com 200 vendidos, reversão depois do pico
        _l("V1", "1", "VENDA", d(2026, 10, 10), "200"), _l("A1", "1", "ANTECIPACAO", d(2026, 10, 11), "1000"),
        _l("R1", "1", "REVERSAO ANTECIPACAO", d(2026, 10, 20), "-600", id_ref="A1", data_orig=d(2026, 10, 11)),
        # ANTIGO (EC 2): venda de setembro (estorno de venda anterior ao mês) -> tem histórico
        _l("E2", "2", "ESTORNO", d(2026, 10, 3), "-50", id_ref="X", data_orig=d(2026, 9, 28)),
        _l("A2", "2", "ANTECIPACAO", d(2026, 10, 12), "5000"),
        # começa no 1º dia (EC 3): não é "depois do 1º dia"
        _l("V3", "3", "VENDA", d(2026, 10, 1), "100"), _l("A3", "3", "ANTECIPACAO", d(2026, 10, 2), "9000"),
        # novo mas dentro das vendas (EC 4): não acende
        _l("V4", "4", "VENDA", d(2026, 10, 5), "9000"), _l("A4", "4", "ANTECIPACAO", d(2026, 10, 6), "1000"),
        # ruído para a competência (mês mais frequente = outubro)
        _l("V5", "5", "VENDA", d(2026, 10, 15), "10"), _l("V6", "5", "VENDA", d(2026, 10, 16), "10"),
    ]
    out = checkout.alertas_antecipacao(linhas)
    assert [a["ref_origem"] for a in out] == ["EC 1"]
    a = out[0]
    assert a["valor"] == D("1000.00") and soma(r[2] for r in a["rastro"]) == a["valor"]   # pico antes da reversão
    assert "11/10/2026" in a["motivo"] and "Reversões posteriores ao pico: 1" in a["motivo"]
    assert "saldo líquido de antecipação no fim do mês R$ 400,00" in a["motivo"]
    assert "agravado por não haver contrato" not in a["motivo"]


# ================================================================ S45 — Atlas pelo CNPJ da aba antiga
def test_s45_atlas_identificada_pelo_cnpj_e_fora_das_comissoes(resultado):
    p = _pend(resultado, "LOJISTA_SEM_CONTRATO")[0]
    assert p["ref_origem"] == f"EC {ATLAS_EC}" and ATLAS_CNPJ in p["motivo"] and "S45" in p["motivo"]
    assert len(p["rastro"]) == 57 and soma(r[2] for r in p["rastro"]) == p["valor"] == D("7876.05")
    assert config.CNPJ_EC_BLOQUEADO[ATLAS_EC] == ATLAS_CNPJ
    assert ATLAS_CNPJ not in {c["cnpj"] for c in resultado["comissoes"]}
    assert ATLAS_EC not in {ec for c in resultado["comissoes"] for ec in c["ec_orbe"].split("|")}
    assert not any(n["tomador_cnpj"] == ATLAS_CNPJ for n in resultado["notas"])


# ================================================================ S44 — estorno: taxa da venda, faixa do estorno
def test_s44_estorno_data_da_venda_e_faixa_da_propria_linha(resultado):
    contratos = resultado["dados"]["contratos"]
    venda = _l("V", OXFORD_EC, "VENDA", date(2026, 9, 3), "1000", modalidade="CREDITO A VISTA", parcelas=1)
    est = _l("E", OXFORD_EC, "ESTORNO", date(2026, 9, 30), "-1000", modalidade="CREDITO PARCELADO", parcelas=3,
             id_ref="V", data_orig=date(2026, 9, 3))
    por_id = {"V": venda, "E": est}
    data, fx, erro = checkout.referencia_taxa(est, por_id)
    assert (data, fx, erro) == (date(2026, 9, 3), "PARC_2_6", None)      # faixa vem do estorno, não da venda (à vista)
    taxa, contrato, _, erro = checkout.taxa_contratada(est, contratos, por_id)
    assert erro is None and taxa == contrato["taxas"]["PARC_2_6"]
    # sem modalidade na linha do estorno, o fallback é a venda original (dado ausente)
    est2 = dict(est, modalidade="", parcelas=None)
    assert checkout.referencia_taxa(est2, {"V": venda, "E": est2})[1] == "CREDITO A VISTA"


def test_s44_em_setembro_nenhum_estorno_muda_de_faixa(resultado):
    por_id = {l["id"]: l for l in resultado["dados"]["orbe"]}
    for l in resultado["dados"]["orbe"]:
        o = por_id.get(l["id_ref"]) if l["tipo"] == "ESTORNO" else None
        if o is not None:
            assert checkout.faixa(l["modalidade"], l["parcelas"], "ESTORNO") == checkout.faixa(
                o["modalidade"], o["parcelas"], "VENDA"), l["id"]


# ================================================================ S47 — isenção da Casa pela data da antecipação
def test_s47_isencao_casa_antecipacao_pela_data_da_antecipacao(resultado):
    contratos = resultado["dados"]["contratos"]

    def taxa(linha, por_id=None):
        t, _, regra, erro = checkout.taxa_contratada(linha, contratos, por_id or {linha["id"]: linha})
        assert erro is None
        return t, regra

    ant_ago = _l("A1", CASA_EC, "ANTECIPACAO", date(2026, 8, 31), "1000", modalidade="", parcelas=None)
    ant_set = _l("A2", CASA_EC, "ANTECIPACAO", date(2026, 9, 1), "1000", modalidade="", parcelas=None)
    assert taxa(ant_ago)[0] == D("2.10") and taxa(ant_set)[0] == 0 and taxa(ant_set)[1].startswith("R52")
    # a reversão (em setembro) de uma antecipação de agosto segue a taxa da antecipação, não a data da reversão
    rev = _l("R1", CASA_EC, "REVERSAO ANTECIPACAO", date(2026, 9, 5), "-1000", id_ref="A1", modalidade="", parcelas=None)
    assert taxa(rev, {"A1": ant_ago, "R1": rev})[0] == D("2.10")
    # estorno de venda de agosto segue a taxa da venda (S47)
    est = _l("E1", CASA_EC, "ESTORNO", date(2026, 9, 5), "-100", id_ref="V0", data_orig=date(2026, 8, 20))
    assert taxa(est)[0] == D("2.69")


# ================================================================ entradas simuladas (S52, S40)
CAB = ("id_transacao;data_movimento;cod_estabelecimento;nome_estabelecimento;tipo_lancamento;modalidade;"
       "qtd_parcelas;bandeira;valor_bruto;taxa_aplicada_pct;valor_taxa;valor_liquido;id_referencia;data_venda_original")


def _entrada(raiz, destino, orbes, ponte=None):
    destino.mkdir(exist_ok=True)
    for k, p in leitores.descobrir_arquivos(raiz).items():
        if k == "orbe" or (k == "ponte" and ponte is not None):
            continue
        shutil.copy(p, destino / p.name)
    for nome, linhas in orbes.items():
        (destino / nome).write_text("\r\n".join([CAB, *linhas]) + "\r\n", encoding="utf-8")
    if ponte is not None:
        (destino / "ponte_out2026.eml").write_bytes(ponte)
    return destino


# ---------------------------------------------------------------- S52
VENDA = f"TXA0001;10/09/2026;{OXFORD_EC};OXFORD;VENDA;CREDITO A VISTA;1;VISA;1000,00;2,59;25,90;974,10;;"
AJUSTE = f"TXA0001;10/09/2026;{OXFORD_EC};OXFORD;VENDA;CREDITO A VISTA;1;VISA;1000,00;2,69;26,90;973,10;;"


def test_s52_mesmo_id_com_valores_diferentes_vale_o_arquivo_de_ajuste(raiz, tmp_path):
    ent = _entrada(raiz, tmp_path / "e", {"orbe_a.csv": [VENDA], "orbe_b_ajuste.csv": [AJUSTE]})
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    linhas = [l for l in r["checkout"] if l["id"] == "TXA0001"]
    assert len(linhas) == 1 and linhas[0]["arquivo"] == "orbe_b_ajuste.csv" and linhas[0]["taxa_aplicada"] == D("2.69")
    p = _pend(r, "ORBE_LINHA_DUPLICADA")
    assert len(p) == 1 and p[0]["ref_origem"] == "TXA0001"
    m = p[0]["motivo"]
    assert "VALORES DIFERENTES" in m and "orbe_b_ajuste.csv" in m and "orbe_a.csv" in m
    assert "R$ 25,90" in m and "R$ 26,90" in m                     # os dois valores à vista
    assert p[0]["valor"] == D("25.90") and p[0]["rastro"][0][0] == "orbe@orbe_a.csv"
    # a comissão é calculada uma vez só (2,59% contratado de Oxford em 10/09 sobre 1000)
    assert sum(1 for c in r["comissoes"] for x in c["rastro"] if x[1] == "TXA0001") == 1


def test_s52_identica_conta_uma_vez(raiz, tmp_path):
    ent = _entrada(raiz, tmp_path / "e", {"orbe_a.csv": [VENDA], "orbe_b_ajuste.csv": [VENDA]})
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    p = _pend(r, "ORBE_LINHA_DUPLICADA")
    assert [l["arquivo"] for l in r["checkout"] if l["id"] == "TXA0001"] == ["orbe_a.csv"]
    assert len(p) == 1 and "idêntica" in p[0]["motivo"]


# ---------------------------------------------------------------- S40
OP_CAB = ["Nº Operação", "Data Contratação", "Data Liquidação", "CNPJ Cliente", "Cliente", "Moeda", "Valor ME",
          "Taxa Cliente", "PTAX Ref.", "Valor R$", "Spread R$", "Spread %", "Spread Estimado R$ (D-1)", "IOF R$",
          "Status Compliance", "Observação"]
MAPLE, PAEREA = "34671260000100", "95739378000118"


def _ponte(ops):
    """.eml com um relatório da Ponte de outubro. ops = [(nº, dia, cnpj, spread_brl, obs)]; ME 1000 x PTAX 5."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Operações"
    ws.append(["PONTE CÂMBIO S.A. - Relatório Mensal"]); ws.append([]); ws.append([]); ws.append([])
    ws.append(OP_CAB)
    for op, dia, cnpj, spread, obs in ops:
        ws.append([op, datetime(2026, 10, dia), datetime(2026, 10, dia + 1), cnpj, "CLIENTE", "USD", 1000, 5.3, 5.0,
                   5300, float(spread), float(spread) / 5000, 75, 20, "APROVADO", obs])
    buf = io.BytesIO()
    wb.save(buf)
    m = EmailMessage()
    m["Subject"] = "Relatório mensal de operações - TARVO - 10/2026"
    m.set_content("Segue o relatório. O repasse da participação de 50% será creditado em 06/11/2026.")
    m.add_attachment(buf.getvalue(), maintype="application",
                     subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="PonteCambio_102026.xlsx")
    return m.as_bytes()


OUT_ORBE = [f"TX99000001;10/10/2026;{OXFORD_EC};OXFORD;VENDA;CREDITO A VISTA;1;VISA;1000,00;2,59;25,90;974,10;;"]


def test_s40_ajuste_da_ponte_abate_a_nota_e_nao_e_spread_negativo(raiz, tmp_path):
    ops = [("PC-1026-0001", 5, MAPLE, 75, None), ("PC-1026-0002", 6, PAEREA, 75, None),
           ("PC-1026-0003", 7, MAPLE, -40, "Taxa travada no pedido (D-1)"),                      # negativo comum
           ("PC-1026-0004", 8, PAEREA, -30, "AJUSTE REF PC-0926-0210 - contestação aceita")]      # ajuste da Ponte
    ent = _entrada(raiz, tmp_path / "e", {"orbe_out.csv": OUT_ORBE}, _ponte(ops))
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    rem = {o["op"]: o for o in r["remessa"]}
    assert rem["PC-1026-0004"]["status"] == "AJUSTE" and rem["PC-1026-0004"]["ref_ajuste"] == "PC-0926-0210"
    assert rem["PC-1026-0004"]["comissao"] == D("-15.00")                  # 50% do Spread R$
    assert rem["PC-1026-0003"]["status"] == "NEGATIVA"
    # o ajuste NÃO vira spread negativo a contestar; o negativo comum continua
    neg = _pend(r, "SPREAD_NEGATIVO")
    assert [x[1] for p in neg for x in p["rastro"]] == ["PC-1026-0003"]
    # nota única: 37,50 + 37,50 - 15,00; rastro com a operação original
    nf = [n for n in r["notas"] if n["linha_negocio"] == "REMESSA"]
    assert len(nf) == 1 and nf[0]["valor"] == D("60.00")
    assert soma(x[2] for x in nf[0]["rastro"]) == D("60.00")
    det = {x[1]: x[3] for x in nf[0]["rastro"]}
    assert "ajuste de PC-0926-0210" in det["PC-1026-0004"]
    assert "ajustes de contestacao" in nf[0]["discriminacao"] and "PC-0926-0210" in nf[0]["discriminacao"]
    # comissão por lojista: Ponte Aérea 37,50 - 15,00; rastro com a referência
    com = {c["cnpj"]: c for c in r["comissoes"] if c["linha_negocio"] == "REMESSA"}
    assert com[PAEREA]["comissao"] == D("22.50") and com[MAPLE]["comissao"] == D("37.50")
    assert any("ajuste de PC-0926-0210" in x[3] for x in com[PAEREA]["rastro"])
    # pendência de conferência do ajuste (premissa em aberto) e rastro fecha
    aj = _pend(r, "AJUSTE_PONTE_APLICADO")
    assert len(aj) == 1 and aj[0]["valor"] == D("-15.00") and "PREMISSA NOSSA" in aj[0]["motivo"]
    for grupo, k in (("comissoes", "comissao"), ("notas", "valor"), ("pendencias", "valor")):
        for it in r[grupo]:
            if it[k] is not None:
                assert soma(x[2] for x in it["rastro"]) == it[k], it["id"]


def test_s40_nota_da_ponte_zerada_ou_negativa_nao_emite_e_vira_pendencia(raiz, tmp_path):
    ops = [("PC-1026-0001", 5, MAPLE, 20, None), ("PC-1026-0004", 8, PAEREA, -60, "AJUSTE REF PC-0926-0210")]
    ent = _entrada(raiz, tmp_path / "e", {"orbe_out.csv": OUT_ORBE}, _ponte(ops))
    r = fechamento.executar(ent, tmp_path / "s", investigar=False)
    assert not [n for n in r["notas"] if n["linha_negocio"] == "REMESSA"]
    p = _pend(r, "SALDO_REMESSA_NAO_POSITIVO")
    assert len(p) == 1 and p[0]["valor"] == D("-20.00") and "não é emitida" in p[0]["motivo"]
    assert soma(x[2] for x in p[0]["rastro"]) == p[0]["valor"]
    assert not _pend(r, "CONFERIR_REPASSE_PONTE")                  # sem nota, nada a conferir
    with open(tmp_path / "s" / "notas_a_emitir.csv", encoding="utf-8", newline="") as f:
        assert not [x for x in csv.DictReader(f, delimiter=";") if x["tomador_cnpj"] == config.CNPJ_PONTE]
