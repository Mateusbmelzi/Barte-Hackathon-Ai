"""Classificação dos lançamentos bancários (Aurora e Meridiano) no plano de contas.
Só regras determinísticas (regex da descrição) + conciliações por VALOR e DATA.
O que nenhuma regra resolve vai para 1.1.09.002, metodo=HUMANO, e vira pendência."""
import re
import unicodedata
from collections import defaultdict
from datetime import timedelta

from . import config
from .dinheiro import soma, fmt_br


def _regra(banco, descricao):
    for b, rx, conta, ref, conf, pend in config.REGRAS_EXTRATO:
        if b == banco and re.search(rx, descricao, re.IGNORECASE):
            return conta, ref, conf, pend
    return None


def _lancamento(banco, m):
    r = _regra(banco, m["descricao"])
    base = {"banco": banco, "ref": m["ref"], "data": m["data"], "descricao": m["descricao"], "valor": m["valor"],
            "observacao": "", "pendencia": None}
    if m.get("arquivo"):                      # só com 2+ versões do extrato (rastro.csv aponta o arquivo usado)
        base["arquivo_origem"] = m["arquivo"]
    if r is None:
        base.update(conta=config.CONTA_NAO_IDENTIFICADO, metodo="HUMANO", confianca=config.CONF_SEM_REGRA,
                    regra="sem regra: 1.1.09.002 provisório",
                    pendencia=("LANCAMENTO_NAO_CLASSIFICADO",
                               "Nenhuma regra reconhece a descrição. Lançado provisoriamente em 1.1.09.002; "
                               "definir a conta (contrapartida, R40).", config.QUEM_HELENA))
    else:
        conta, ref, conf, pend = r
        base.update(conta=conta, metodo="REGRA", confianca=conf, regra=ref, pendencia=pend)
    return base


def _ops_unicas(ponte_resultado):
    return [o for o in ponte_resultado if o["status"] not in ("DUPLICATA", "AJUSTE")]   # S40: ajuste não é operação de câmbio


def _conciliar_ted_ponte(lancs, ops):
    """TED para a Ponte no dia D = soma (Valor R$ + IOF) das operações contratadas em D (doc §6.3)."""
    por_dia = defaultdict(list)
    for o in ops:
        por_dia[o["data"]].append(o)
    for l in lancs:
        if l["banco"] == "MERIDIANO" and re.search(r"^TED ENVIADA PONTE CAMBIO", l["descricao"]):
            dia = por_dia.get(l["data"], [])
            esperado = soma(o["valor_brl"] + o["iof"] for o in dia)
            if -l["valor"] == esperado:
                l["observacao"] = f"conciliado: {len(dia)} operações Ponte contratadas em {l['data']:%d/%m} (Valor R$ + IOF)"
            else:
                l["confianca"] = config.CONF_NAO_CONCILIADO
                l["pendencia"] = ("TED_PONTE_NAO_CONCILIADO",
                                  f"TED à Ponte de {fmt_br(-l['valor'])} não bate com Valor R$ + IOF das operações "
                                  f"contratadas no dia ({fmt_br(esperado)}). Conferir com a Ponte.", config.QUEM_HELENA)


def _conciliar_pix_lojista(lancs, ops, nomes_lojistas=()):
    """PIX de lojista no dia d = soma (Valor R$ + IOF) das ops de UM CNPJ contratadas em [d, d+7).
    Casamento só por valor e janela de datas; o nome no extrato não é usado."""
    janela = timedelta(days=config.JANELA_PIX_REMESSA_DIAS)
    usados = set()
    for l in lancs:
        if not (l["banco"] == "MERIDIANO" and re.search(r"^PIX RECEB ", l["descricao"])):
            continue
        achou = None
        por_cnpj = defaultdict(list)
        for o in ops:
            if l["data"] <= o["data"] < l["data"] + janela:
                por_cnpj[o["cnpj"]].append(o)
        for cnpj, os_ in sorted(por_cnpj.items()):
            if (cnpj, l["data"]) not in usados and soma(o["valor_brl"] + o["iof"] for o in os_) == l["valor"]:
                achou = (cnpj, os_)
                break
        if achou:
            usados.add((achou[0], l["data"]))
            l["observacao"] = f"conciliado: CNPJ {achou[0]}, {len(achou[1])} operações Ponte de {l['data']:%d/%m} a +6 dias"
        else:
            # S22 (regra confirmada pelo financeiro): PIX de lojista sem operação Ponte no mês = adiantamento
            # para remessa futura. Conta 2.1.02.001 mantida; acompanhar no relatório do mês seguinte.
            quem = _pagador(l["descricao"], nomes_lojistas)
            l["metodo"] = "HUMANO"
            l["confianca"] = config.CONF_PIX_REMESSA_FUTURA
            l["regra"] += "; S22 PIX de lojista sem operação no mês = recurso para remessa futura"
            l["observacao"] = ("S22: adiantamento de lojista para remessa prevista no mês seguinte (confirmado pelo "
                               "financeiro); acompanhar no relatório da Ponte do mês seguinte")
            l["pendencia"] = ("ACOMPANHAR_REMESSA_FUTURA",
                              f"Adiantamento da {quem} para remessa prevista no mês seguinte (S22): PIX de "
                              f"{fmt_br(l['valor'])} ('{l['descricao']}') sem operação Ponte no mês que o explique. "
                              "Mantido em 2.1.02.001 (recurso de lojista para remessa). Acompanhar: a operação deve "
                              "aparecer no relatório da Ponte do mês seguinte; se não aparecer, confirmar com o lojista "
                              "(devolver ou reclassificar).",
                              config.QUEM_HELENA)


def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower().strip()


def _pagador(descricao, nomes_lojistas):
    """Só para o TEXTO da pendência (o casamento contábil nunca usa nome): o resto da descrição após
    'PIX RECEB' é o começo do nome do pagador; se for prefixo de exatamente um lojista, usa o nome dele."""
    resto = re.sub(r"^PIX RECEB\s+", "", descricao, flags=re.IGNORECASE).strip()
    achados = sorted({n for n in nomes_lojistas if resto and _sem_acento(n).startswith(_sem_acento(resto))})
    return achados[0] if len(achados) == 1 else f"pagador '{resto}'"


def _conciliar_transferencias(lancs):
    """Transferência entre contas próprias: débito num banco = crédito no outro (mesmo valor e data)."""
    transf = [l for l in lancs if l["conta"] == "1.1.09.001"]
    usados = set()
    for l in transf:
        if l["ref"] in usados:
            continue
        par = next((x for x in transf if x["banco"] != l["banco"] and x["ref"] not in usados
                    and x["valor"] == -l["valor"] and x["data"] == l["data"]), None)
        if par:
            usados.update({l["ref"], par["ref"]})
            l["observacao"] = f"par: {par['banco']} {par['ref']}"
            par["observacao"] = f"par: {l['banco']} {l['ref']}"
    for l in transf:
        if l["ref"] not in usados:
            l["observacao"] = "sem par no outro banco dentro do mês: em trânsito"
            l["pendencia"] = ("TRANSFERENCIA_EM_TRANSITO",
                              f"Transferência de {fmt_br(abs(l['valor']))} em {l['data']:%d/%m/%Y} sem contrapartida no outro "
                              "banco dentro do mês (S09: cai no mês seguinte). Mantida em 1.1.09.001 (H13); "
                              "conferir no extrato do mês seguinte.", config.QUEM_HELENA)


def classificar(aurora, meridiano, ponte_resultado, plano, meta_aurora, nomes_lojistas=()):
    lancs = [_lancamento("AURORA", m) for m in aurora] + [_lancamento("MERIDIANO", m) for m in meridiano]
    ops = _ops_unicas(ponte_resultado)
    _conciliar_ted_ponte(lancs, ops)
    _conciliar_pix_lojista(lancs, ops, nomes_lojistas)
    _conciliar_transferencias(lancs)
    for l in lancs:  # toda conta tem que existir e aceitar lançamento
        c = plano.get(l["conta"])
        if c is None or not c["aceita"]:
            raise ValueError(f"conta {l['conta']} ({l['ref']}) não existe ou não aceita lançamento no plano de contas")
        l["conta_descricao"] = c["descricao"]

    pend = []
    for l in lancs:
        if l["pendencia"]:
            tipo, motivo, quem = l["pendencia"]
            pend.append({"tipo": tipo, "ref_origem": l["ref"], "valor": l["valor"], "motivo": motivo, "quem_decide": quem,
                         "rastro": [(l["banco"].lower(), l["ref"], l["valor"], l["descricao"])]})
    # saldo do Aurora tem que fechar (prova de leitura completa)
    si, sf = meta_aurora.get("saldo_anterior"), meta_aurora.get("saldo_final")
    mov_aurora = soma(m["valor"] for m in aurora)
    if si is not None and sf is not None and si + mov_aurora != sf:
        pend.append({"tipo": "EXTRATO_NAO_FECHA", "ref_origem": "AURORA", "valor": None,
                     "motivo": f"Saldo anterior {fmt_br(si)} + movimentos {fmt_br(mov_aurora)} != saldo final {fmt_br(sf)}.",
                     "quem_decide": config.QUEM_HELENA, "rastro": []})
    return lancs, pend
