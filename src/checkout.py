"""Linha CHECKOUT (Orbe): comissão por transação pela taxa CONTRATADA, divergências e pendências."""
from collections import OrderedDict
from decimal import Decimal

from . import config
from .dinheiro import arred, soma, fmt_br, fmt_pct

ZERO = Decimal("0")


# ---------------------------------------------------------------- contratos
def contratos_ativos(contratos):
    return [c for c in contratos if not c["riscado"]]


def nome_por_cnpj(contratos):
    """Nome do lojista = 1ª linha (ordem da planilha) daquele CNPJ."""
    nomes = {}
    for c in contratos_ativos(contratos):
        nomes.setdefault(c["cnpj"], c["lojista"])
    return nomes


def contrato_vigente(candidatos, data):
    """H05: escolhe a linha vigente na data. Devolve (contrato, erro)."""
    if not candidatos:
        return None, "EC/CNPJ sem linha na aba vigente da planilha de taxas"
    ruins = [c for c in candidatos if not c["vigencia_ok"]]
    if ruins:
        return None, f"vigência não reconhecida na planilha (linha {ruins[0]['linha']}: {ruins[0]['vigencia_texto']!r})"
    ok = [c for c in candidatos
          if (c["inicio"] is None or c["inicio"] <= data) and (c["fim"] is None or data <= c["fim"])]
    if len(ok) == 1:
        return ok[0], None
    if not ok:
        return None, f"nenhuma vigência cobre a data {data:%d/%m/%Y}"
    return None, f"mais de uma vigência cobre a data {data:%d/%m/%Y} (linhas {[c['linha'] for c in ok]})"


def candidatos_por_ec(contratos, ec):
    """Orbe -> planilha pelo EC; ECs sem código usam o de-para S03 (R14) por CNPJ. Sem fuzzy."""
    ativos = contratos_ativos(contratos)
    cand = [c for c in ativos if c["ec"] == ec]
    if not cand and ec in config.DEPARA_EC_CNPJ:
        cnpj = config.DEPARA_EC_CNPJ[ec]
        cand = [c for c in ativos if c["cnpj"] == cnpj]
    return cand


# ---------------------------------------------------------------- uma transação
def faixa(modalidade, parcelas, tipo):
    """Coluna da planilha que vale para a transação (doc §2.2)."""
    if tipo in ("ANTECIPACAO", "REVERSAO ANTECIPACAO"):
        return "ANTECIPACAO"
    if modalidade in ("DEBITO", "CREDITO A VISTA", "PIX"):
        return modalidade
    if modalidade == "CREDITO PARCELADO" and parcelas:
        if 2 <= parcelas <= 6:
            return "PARC_2_6"
        if 7 <= parcelas <= 12:
            return "PARC_7_12"
    return None


def referencia_taxa(linha, por_id):
    """Data e faixa que definem a taxa contratada.
    VENDA/ANTECIPACAO: data do movimento (H05).
    ESTORNO: data da venda original (R11/S02), ligada por id_referencia quando faltar a data.
    REVERSAO: taxa da antecipação que ela reverte (R12), ligada por id_referencia.
    Nunca por bandeira (doc A6)."""
    tipo = linha["tipo"]
    if tipo in ("VENDA", "ANTECIPACAO"):
        return linha["data"], faixa(linha["modalidade"], linha["parcelas"], tipo), None
    if tipo in ("ESTORNO", "REVERSAO ANTECIPACAO"):
        orig = por_id.get(linha["id_ref"]) if linha["id_ref"] else None
        data = linha["data_orig"] or (orig["data"] if orig else None)
        if data is None:
            return None, None, "estorno/reversão sem data da venda original e sem id_referencia no arquivo"
        if tipo == "REVERSAO ANTECIPACAO":
            if orig is not None and orig["tipo"] != "ANTECIPACAO":
                return None, None, f"reversão aponta para {linha['id_ref']}, que não é antecipação"
            return data, "ANTECIPACAO", None
        mod, parc = linha["modalidade"], linha["parcelas"]
        if orig is not None and not mod:
            mod, parc = orig["modalidade"], orig["parcelas"]
        return data, faixa(mod, parc, tipo), None
    return None, None, f"tipo_lancamento desconhecido: {tipo}"


def taxa_contratada(linha, contratos, por_id):
    """Devolve (taxa_pct, contrato, regra, erro)."""
    data, fx, erro = referencia_taxa(linha, por_id)
    if erro:
        return None, None, None, erro
    if fx is None:
        return None, None, None, f"modalidade/parcelas sem faixa na planilha ({linha['modalidade']} {linha['parcelas']})"
    contrato, erro = contrato_vigente(candidatos_por_ec(contratos, linha["ec"]), data)
    if erro:
        return None, None, None, erro
    taxa = contrato["taxas"].get(fx)
    if taxa is None:
        return None, contrato, None, f"planilha sem taxa de {fx} para o lojista"
    regra = f"R10 taxa {fx} da linha {contrato['linha']} vigente em {data:%d/%m/%Y}"
    zero = config.TAXA_ZERO_CHECKOUT.get(linha["ec"])
    if zero and zero[0] <= data <= zero[1]:
        taxa, regra = ZERO, f"R17 taxa zero ({zero[0]:%d/%m}-{zero[1]:%d/%m/%Y}) na data {data:%d/%m/%Y}"
    if linha["tipo"] == "ESTORNO":
        regra += " (R11 data da venda original)"
    if linha["tipo"] == "REVERSAO ANTECIPACAO":
        regra += f" (R12 anula a antecipação {linha['id_ref']})"
    return taxa, contrato, regra, None


# ---------------------------------------------------------------- processamento
def calcular(orbe, contratos):
    """Classifica cada linha Orbe em FATURAVEL ou EXCLUIDA e calcula comissão/divergência."""
    por_id = {l["id"]: l for l in orbe}
    resultado = []
    for l in orbe:
        r = dict(l)
        if l["ec"] in config.ECS_BLOQUEADOS:
            r.update(status="EXCLUIDA", motivo="BLOQUEADO", erro=config.ECS_BLOQUEADOS[l["ec"]])
            resultado.append(r)
            continue
        taxa, contrato, regra, erro = taxa_contratada(l, contratos, por_id)
        if erro:
            r.update(status="EXCLUIDA", motivo="SEM_TAXA", erro=erro)
            resultado.append(r)
            continue
        comissao = arred(l["bruto"] * taxa / config.DIVISAO_PCT)            # R10/R01 por linha
        divergente = l["taxa_aplicada"] != taxa                               # R13 (taxa, não valor: R02)
        dif = arred(l["bruto"] * (l["taxa_aplicada"] - taxa) / config.DIVISAO_PCT) if divergente else ZERO
        r.update(status="FATURAVEL", cnpj=contrato["cnpj"], contratada=taxa, regra=regra,
                 comissao=comissao, divergente=divergente, diferenca=dif)
        resultado.append(r)
    return resultado


def _agrupar(linhas, chave):
    g = OrderedDict()
    for l in linhas:
        g.setdefault(l[chave], []).append(l)
    return g


def comissoes(resultado, contratos):
    """Uma linha por lojista (CNPJ). Comissão = soma das comissões por linha (R30)."""
    nomes = nome_por_cnpj(contratos)
    fat = [l for l in resultado if l["status"] == "FATURAVEL"]
    saida = []
    for cnpj, ls in sorted(_agrupar(fat, "cnpj").items()):
        mdr = soma(l["comissao"] for l in ls if l["tipo"] in ("VENDA", "ESTORNO"))
        ant = soma(l["comissao"] for l in ls if l["tipo"] in ("ANTECIPACAO", "REVERSAO ANTECIPACAO"))
        saida.append({
            "cnpj": cnpj, "lojista": nomes[cnpj], "linha_negocio": "CHECKOUT",
            "comissao": mdr + ant, "comissao_mdr": mdr, "comissao_antecipacao": ant,
            "qtd": len(ls), "ec_orbe": "|".join(sorted({l["ec"] for l in ls})),
            "regra": "R10/R11/R12/R14/R17 taxa contratada x bruto, half-up por linha (R01)",
            "rastro": [("orbe", l["id"], l["comissao"], f"{l['tipo']} {fmt_pct(l['contratada'])}%") for l in ls],
        })
    return saida


def notas(comissoes_chk, competencia):
    """R30/R31/H16: 1 nota por lojista com saldo > 0."""
    out = []
    for c in comissoes_chk:
        if c["comissao"] <= 0:
            continue
        txt = (f"Servicos de intermediacao de pagamentos (checkout) - competencia {competencia} - "
               f"MDR {fmt_br(c['comissao_mdr'])} e antecipacao {fmt_br(c['comissao_antecipacao'])} "
               f"({c['qtd']} transacoes Orbe)")
        out.append({"tomador_cnpj": c["cnpj"], "tomador": c["lojista"], "linha_negocio": "CHECKOUT",
                    "valor": c["comissao"], "discriminacao": txt, "rastro": c["rastro"]})
    return out


def divergencias(resultado, contratos):
    nomes = nome_por_cnpj(contratos)
    out = []
    for l in resultado:
        if l["status"] == "FATURAVEL" and l["divergente"]:
            out.append({
                "cnpj": l["cnpj"], "linha_negocio": "CHECKOUT", "ref_origem": l["id"],
                "contratada_pct": l["contratada"], "aplicada_pct": l["taxa_aplicada"], "diferenca": l["diferenca"],
                "lojista": nomes[l["cnpj"]], "ec_orbe": l["ec"], "tipo_lancamento": l["tipo"],
                "data": l["data"], "valor_base": l["bruto"], "regra": "R13 bruto x (aplicada - contratada); " + l["regra"],
                "rastro": [("orbe", l["id"], l["diferenca"], f"{l['tipo']} bruto {l['bruto']}")],
            })
    return out


def pendencias(resultado, comissoes_chk, contratos):
    nomes = nome_por_cnpj(contratos)
    out = []
    fat = [l for l in resultado if l["status"] == "FATURAVEL"]
    # divergências por lojista (R13, H02, H03, H04)
    for cnpj, ls in sorted(_agrupar([l for l in fat if l["divergente"]], "cnpj").items()):
        total = soma(l["diferenca"] for l in ls)
        a_mais = sum(1 for l in ls if l["diferenca"] > 0 and l["bruto"] > 0)
        a_menos = sum(1 for l in ls if l["taxa_aplicada"] < l["contratada"])
        zero = any(l["contratada"] == 0 for l in ls)
        motivo = (f"Orbe aplicou taxa diferente da contratada em {len(ls)} transações de {nomes[cnpj]} "
                  f"(EC {ls[0]['ec']}); líquido {fmt_br(total)}, já com estornos de vendas divergentes (H02). ")
        if zero:
            motivo += "Contrato com taxa zero set-dez (R17/H03): tudo que a Orbe cobrou deve voltar ao lojista. "
        if a_menos:
            motivo += f"{a_menos} transações com taxa ABAIXO do contrato (H04): cobrar diferença. "
        motivo += "Decidir devolução ao lojista e cobrança da Orbe (R13/S01). Lista em divergencias_taxa.csv."
        out.append({"tipo": "DIVERGENCIA_TAXA_CHECKOUT", "ref_origem": f"EC {ls[0]['ec']}", "valor": total,
                    "motivo": motivo, "quem_decide": config.QUEM_HELENA,
                    "rastro": [("orbe", l["id"], l["diferenca"], l["tipo"]) for l in ls]})
    # saldo <= 0 (R31)
    for c in comissoes_chk:
        if c["comissao"] <= 0:
            out.append({"tipo": "SALDO_CHECKOUT_NAO_POSITIVO", "ref_origem": f"CNPJ {c['cnpj']}", "valor": c["comissao"],
                        "motivo": (f"{c['lojista']} fechou o checkout em {fmt_br(c['comissao'])}: não emite nota e o saldo "
                                   "negativo não transporta (R31/S04). Ex.: estorno de venda de mês anterior abatido à taxa "
                                   "vigente na venda original (H01). Decidir tratamento."),
                        "quem_decide": config.QUEM_HELENA, "rastro": c["rastro"]})
    # linhas excluídas
    exc = [l for l in resultado if l["status"] == "EXCLUIDA"]
    for ec, ls in _agrupar(exc, "ec").items():
        bloqueado = ls[0]["motivo"] == "BLOQUEADO"
        vt = soma(l["valor_taxa"] for l in ls)
        bruto = soma(l["bruto"] for l in ls)
        if bloqueado:
            motivo = (f"{ls[0]['erro']}. {len(ls)} transações (bruto {fmt_br(bruto)}) fora de comissões e notas. "
                      f"Valor = taxa que a Orbe cobrou ({fmt_br(vt)}), só referência. Confirmar taxa contratada para faturar.")
            tipo = "LOJISTA_SEM_CONTRATO"
        else:
            erros = sorted({l["erro"] for l in ls})
            motivo = (f"EC {ec}: {len(ls)} transações sem taxa contratada determinável ({'; '.join(erros)}). "
                      f"Fora de comissões e notas até corrigir a planilha. Valor = taxa Orbe {fmt_br(vt)}.")
            tipo = "TAXA_CONTRATADA_INDEFINIDA"
        out.append({"tipo": tipo, "ref_origem": f"EC {ec}", "valor": vt, "motivo": motivo,
                    "quem_decide": config.QUEM_COMERCIAL,
                    "rastro": [("orbe", l["id"], l["valor_taxa"], "valor_taxa Orbe") for l in ls]})
        if bloqueado:
            r = risco_antecipacao(ls)
            if r:
                out.append(r)
    return out


def risco_antecipacao(ls):
    """H15: primeira data em que as antecipações acumuladas superam as vendas acumuladas."""
    ants = sorted((l for l in ls if l["tipo"] == "ANTECIPACAO"), key=lambda l: l["data"])
    for dia in sorted({l["data"] for l in ants}):
        ate = [l for l in ants if l["data"] <= dia]
        total_ant = soma(l["bruto"] for l in ate)
        vendas = soma(l["bruto"] for l in ls if l["tipo"] == "VENDA" and l["data"] <= dia)
        if total_ant > vendas:
            break
    else:
        return None
    rev = sum(1 for l in ls if l["tipo"] == "REVERSAO ANTECIPACAO")
    total_mes = soma(l["bruto"] for l in ants)
    return {"tipo": "RISCO_ANTECIPACAO", "ref_origem": f"EC {ls[0]['ec']}", "valor": total_ant,
            "motivo": (f"Lojista sem contrato antecipou {fmt_br(total_ant)} em {len(ate)} operações até "
                       f"{dia:%d/%m/%Y}, acima das vendas acumuladas até a data ({fmt_br(vendas)}). "
                       f"No mês: {len(ants)} antecipações ({fmt_br(total_mes)}) e {rev} reversões. "
                       "Avaliar risco/compliance (H15)."),
            "quem_decide": config.QUEM_RISCO,
            "rastro": [("orbe", l["id"], l["bruto"], "ANTECIPACAO bruto") for l in ate]}
