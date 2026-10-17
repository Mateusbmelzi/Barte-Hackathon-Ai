"""Linha REMESSA (Ponte Câmbio): participação no spread, divergências e pendências."""
from collections import OrderedDict

from . import config
from .checkout import contrato_vigente, contratos_ativos, nome_por_cnpj
from .dinheiro import arred, soma, fmt_br, fmt_pct


def calcular(ops, contratos, competencia_mes):
    """Classifica cada operação: VALIDA, DUPLICATA, NEGATIVA ou FORA_COMPETENCIA."""
    ativos = contratos_ativos(contratos)
    vistos = set()
    out = []
    for o in ops:
        r = dict(o)
        r["status"] = "VALIDA"
        if o["op"] in vistos:
            r["status"] = "DUPLICATA"            # R24: nº de operação único; repetida conta 1 vez
        elif (o["data"].year, o["data"].month) != competencia_mes:
            r["status"] = "FORA_COMPETENCIA"     # R03: competência = data de contratação
        elif o["spread_brl"] < 0:
            r["status"] = "NEGATIVA"             # R23: spread negativo fora da comissão e da nota
        vistos.add(o["op"])
        contrato, erro = contrato_vigente([c for c in ativos if c["cnpj"] == o["cnpj"]], o["data"])
        r["contrato_erro"] = erro
        if contrato is not None:
            padrao = contrato["spread"] is None
            r["contratado"] = config.SPREAD_PADRAO if padrao else contrato["spread"]   # CC03 (padrão); negociado = linha da planilha (ex.: CC02)
            r["regra_spread"] = ("CC03 spread padrão 1,5% (célula em branco/'padrão')" if padrao
                                 else f"spread contratado linha {contrato['linha']}")
        else:
            r["contratado"], r["regra_spread"] = None, None
        if r["status"] == "VALIDA":
            r["comissao"] = arred(o["spread_brl"] * config.PARTICIPACAO_REMESSA)        # R20/R01 por operação
        # divergência (R22, H06, H07): só operações válidas. H08 (revisada): spread negativo
        # NÃO é divergência (o lojista pagou a menos); fica só na pendência SPREAD_NEGATIVO.
        r["divergente"] = False
        if r["status"] == "VALIDA" and r["contratado"] is not None:
            delta = o["spread_pct"] - r["contratado"]
            if abs(delta) >= config.TOLERANCIA_SPREAD:
                r["divergente"] = True
                r["diferenca"] = arred(delta * o["ptax"] * o["valor_me"])
        out.append(r)
    return out


def _agrupar(linhas):
    g = OrderedDict()
    for l in linhas:
        g.setdefault(l["cnpj"], []).append(l)
    return g


def comissoes(resultado, contratos):
    """H17: comissão REMESSA por lojista = soma dos 50% por operação daquele CNPJ."""
    nomes = nome_por_cnpj(contratos)
    validas = [o for o in resultado if o["status"] == "VALIDA"]
    out = []
    for cnpj, ls in sorted(_agrupar(validas).items()):
        out.append({
            "cnpj": cnpj, "lojista": nomes.get(cnpj, ls[0]["cliente"]), "linha_negocio": "REMESSA",
            "comissao": soma(o["comissao"] for o in ls), "qtd": len(ls), "ec_orbe": "",
            "regra": "R20 50% do Spread R$ por operação, half-up (R01); H17 quebra por lojista",
            "rastro": [("ponte", o["op"], o["comissao"], f"50% de Spread R$ {o['spread_brl']}") for o in ls],
        })
    return out


def nota(resultado, competencia):
    """R32: 1 nota só, tomadora Ponte Câmbio, pelo total da participação."""
    validas = [o for o in resultado if o["status"] == "VALIDA"]
    if not validas:
        return []
    total = soma(o["comissao"] for o in validas)
    txt = (f"Servicos de intermediacao de cambio - participacao de 50% do spread realizado - "
           f"competencia {competencia} - {len(validas)} operacoes")
    return [{"tomador_cnpj": config.CNPJ_PONTE, "tomador": config.NOME_PONTE, "linha_negocio": "REMESSA",
             "valor": total, "discriminacao": txt,
             "rastro": [("ponte", o["op"], o["comissao"], "50% Spread R$") for o in validas]}]


def divergencias(resultado, contratos):
    nomes = nome_por_cnpj(contratos)
    out = []
    for o in resultado:
        if o["divergente"]:
            out.append({
                "cnpj": o["cnpj"], "linha_negocio": "REMESSA", "ref_origem": o["op"],
                "contratada_pct": o["contratado"] * 100, "aplicada_pct": o["spread_pct"] * 100,
                "diferenca": o["diferenca"], "lojista": nomes.get(o["cnpj"], o["cliente"]), "ec_orbe": "",
                "tipo_lancamento": "REMESSA",
                "data": o["data"], "valor_base": o["valor_me"],
                "regra": ("R22/H07 (spread% - contratado) x PTAX x Valor ME; tolerância 0,01 p.p. (H06); "
                          + (o["regra_spread"] or "")),
                "natureza": config.NATUREZA_CONTRATO,
                "rastro": [("ponte", o["op"], o["diferenca"], f"{o['moeda']} {o['valor_me']} x PTAX {o['ptax']}")],
            })
    return out


def pendencias(resultado, contratos, meta_ponte, total_nota):
    """Pendências da remessa. total_nota = valor da nota para a Ponte."""
    nomes = nome_por_cnpj(contratos)
    out = []
    # divergência positiva por lojista (contestar com a Ponte) + excesso na nota (S13)
    pos = [o for o in resultado if o["divergente"] and o["status"] == "VALIDA"]
    for cnpj, ls in sorted(_agrupar(pos).items()):
        total = soma(o["diferenca"] for o in ls)
        ap = sorted({fmt_pct(o["spread_pct"] * 100) for o in ls})
        out.append({"tipo": "DIVERGENCIA_SPREAD_REMESSA", "ref_origem": f"CNPJ {cnpj}", "valor": total,
                    "motivo": (f"Ponte aplicou spread diferente do contratado ({fmt_pct(ls[0]['contratado'] * 100)}%) "
                               f"em {len(ls)} operações de {nomes.get(cnpj, cnpj)} (aplicado de {ap[0]}% a {ap[-1]}%). "
                               f"Valor cheio pago a mais pelo lojista (R22/S10). Devolver ao lojista {fmt_br(total)}; "
                               f"recuperar do parceiro (Ponte) {fmt_br(total)} (R60/S34). Contestar com a Ponte (S15)."
                               + (" " + config.CONTEXTO_PENDENCIA[("REMESSA", cnpj)]
                                  if ("REMESSA", cnpj) in config.CONTEXTO_PENDENCIA else "")),
                    "quem_decide": config.QUEM_HELENA,
                    "rastro": [("ponte", o["op"], o["diferenca"], "pago a mais") for o in ls]})
        metade = [(o, arred(o["diferenca"] * config.PARTICIPACAO_REMESSA)) for o in ls]
        out.append({"tipo": "EXCESSO_NA_NOTA_REMESSA", "ref_origem": f"CNPJ {cnpj}",
                    "valor": soma(v for _, v in metade),
                    "motivo": (f"A nota de remessa inclui 50% do spread realizado, inclusive o excesso de "
                               f"{nomes.get(cnpj, cnpj)} (S13/R20). Se a Ponte devolver, a metade da Tarvo sai no mês do ajuste."),
                    "quem_decide": config.QUEM_HELENA,
                    "rastro": [("ponte", o["op"], v, "50% do excesso") for o, v in metade]})
    # spread negativo (R23, R53): 1 pendência por lojista (R64/S38), rastro por operação
    neg = [o for o in resultado if o["status"] == "NEGATIVA"]
    for cnpj, ls in sorted(_agrupar(neg).items()):
        total = soma(o["spread_brl"] for o in ls)
        det = "; ".join(f"{o['op']} {fmt_br(o['spread_brl'])} ({fmt_pct(o['spread_pct'] * 100)}%, estimado D-1 "
                        f"{fmt_br(o['spread_estimado'])}, obs Ponte '{o['obs']}')" for o in ls)
        out.append({"tipo": "SPREAD_NEGATIVO", "ref_origem": f"CNPJ {cnpj}", "valor": total,
                    "motivo": (f"Spread realizado negativo em {len(ls)} operação(ões) de {nomes.get(cnpj, ls[0]['cliente'])}, "
                               f"total {fmt_br(total)}: {det}. Fora da comissão e da nota (R23); prejuízo da Tarvo com a "
                               "Ponte, não divergência do lojista (R53/S25); contestar com a Ponte (S15)."),
                    "quem_decide": config.QUEM_HELENA,
                    "rastro": [("ponte", o["op"], o["spread_brl"], "Spread R$ realizado") for o in ls]})
    # duplicata (R24, H09)
    for o in resultado:
        if o["status"] == "DUPLICATA":
            out.append({"tipo": "OPERACAO_DUPLICADA", "ref_origem": o["op"], "valor": o["spread_brl"],
                        "motivo": (f"Nº de operação repetido no relatório da Ponte (linha Excel {o['linha_excel']}, obs "
                                   f"'{o['obs']}'). Contado uma vez (R24). Valor = Spread R$ da linha repetida (H09). "
                                   "Pedir à Ponte para corrigir o relatório (S15)."),
                        "quem_decide": config.QUEM_HELENA,
                        "rastro": [("ponte", o["op"], o["spread_brl"], f"linha repetida Excel {o['linha_excel']}")]})
    # operações fora da competência (R03): 1 pendência por mês de contratação, não 1 por operação
    fora = OrderedDict()
    for o in resultado:
        if o["status"] == "FORA_COMPETENCIA":
            fora.setdefault(f"{o['data']:%m/%Y}", []).append(o)
    for mes, ls in fora.items():
        total = soma(o["spread_brl"] for o in ls)
        out.append({"tipo": "REMESSA_FORA_COMPETENCIA", "ref_origem": f"contratação {mes}", "valor": total,
                    "motivo": (f"{len(ls)} operações do relatório da Ponte contratadas em {mes}, fora da competência "
                               f"(R03). Não entraram na comissão nem na nota (Spread R$ {fmt_br(total)}). "
                               "Verificar se o relatório recebido é o do mês certo."),
                    "quem_decide": config.QUEM_HELENA,
                    "rastro": [("ponte", o["op"], o["spread_brl"], "Spread R$") for o in ls]})
    for o in resultado:
        if o["contrato_erro"] and o["status"] not in ("DUPLICATA", "FORA_COMPETENCIA"):
            out.append({"tipo": "REMESSA_SEM_CONTRATO", "ref_origem": o["op"], "valor": None,
                        "motivo": (f"CNPJ {o['cnpj']}: {o['contrato_erro']}. Comissão contada; divergência não verificada. "
                                   "Abrir cadastro com o Comercial (R58/R63)."),
                        "quem_decide": config.QUEM_COMERCIAL, "rastro": []})
    # conferir o TED de repasse (R26/S14)
    validas = [o for o in resultado if o["status"] == "VALIDA"]
    if validas:
        quando = f"em {meta_ponte['data_repasse']:%d/%m/%Y}" if meta_ponte.get("data_repasse") else "quando cair"
        total_rel = soma(o["spread_brl"] for o in resultado)          # todas as linhas do relatório
        metade_rel = arred(total_rel * config.PARTICIPACAO_REMESSA)
        n_dup = sum(1 for o in resultado if o["status"] == "DUPLICATA")
        n_neg = sum(1 for o in resultado if o["status"] == "NEGATIVA")
        out.append({"tipo": "CONFERIR_REPASSE_PONTE", "ref_origem": "Nota REMESSA", "valor": total_nota,
                    "motivo": (f"Ponte informa repasse dos 50% {quando}. Fato: o total do relatório da Ponte "
                               f"({fmt_br(total_rel)}) inclui {n_dup} linha(s) duplicada(s) e {n_neg} spread(s) negativo(s); "
                               f"50% dele ({fmt_br(metade_rel)}) difere da nota ({fmt_br(total_nota)}) em "
                               f"{fmt_br(abs(total_nota - metade_rel))}. Conferir o TED quando cair, sem presumir "
                               "desconto (R26/S14)."),
                    "quem_decide": config.QUEM_HELENA,
                    "rastro": [("ponte", o["op"], o["comissao"], "50% Spread R$") for o in validas]})
    return out
