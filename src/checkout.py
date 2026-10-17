"""Linha CHECKOUT (Orbe): comissão por transação pela taxa CONTRATADA, divergências e pendências."""
from collections import Counter, OrderedDict
from datetime import date
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
    """Orbe -> planilha pelo EC; ECs sem código usam o de-para S03 (CC04) por CNPJ. Sem fuzzy."""
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
        cond = config.ISENCAO_CONDICAO.get(linha["ec"], "cadastro")
        taxa, regra = ZERO, (f"R52 isenção {cond}: taxa zero ({zero[0]:%d/%m}-{zero[1]:%d/%m/%Y}) "
                             f"na data {data:%d/%m/%Y}")
    if linha["tipo"] == "ESTORNO":
        regra += " (R11 data da venda original)"
    if linha["tipo"] == "REVERSAO ANTECIPACAO":
        regra += f" (R12 anula a antecipação {linha['id_ref']})"
    return taxa, contrato, regra, None


def acima_do_maximo(linha, por_id):
    """S38: parcelado acima de MAX_PARCELAS (no estorno, olha a venda original se faltar o dado)."""
    mod, parc = linha["modalidade"], linha["parcelas"]
    if linha["tipo"] == "ESTORNO" and not mod and linha["id_ref"] in por_id:
        mod, parc = por_id[linha["id_ref"]]["modalidade"], por_id[linha["id_ref"]]["parcelas"]
    return mod == "CREDITO PARCELADO" and parc is not None and parc > config.MAX_PARCELAS


# ---------------------------------------------------------------- processamento
def estornos_duplicados(orbe):
    """Dupla reversão: ids das linhas ESTORNO/REVERSAO cujo id_referencia já foi estornado/revertido
    por uma linha ANTERIOR (ordem do arquivo/nome). Devolve {id da 2ª linha: linha da 1ª}."""
    primeira, dup = {}, {}
    for l in orbe:
        if l["tipo"] in ("ESTORNO", "REVERSAO ANTECIPACAO") and l["id_ref"]:
            if l["id_ref"] in primeira:
                dup[l["id"]] = primeira[l["id_ref"]]
            else:
                primeira[l["id_ref"]] = l
    return dup


def calcular(orbe, contratos):
    """Classifica cada linha Orbe em FATURAVEL ou EXCLUIDA e calcula comissão/divergência."""
    por_id = {l["id"]: l for l in orbe}
    duplos = estornos_duplicados(orbe)
    resultado = []
    for l in orbe:
        r = dict(l)
        if l["id"] in duplos and l["ec"] not in config.ECS_BLOQUEADOS:
            r["estorno_duplicado_de"] = duplos[l["id"]]["id"]
            if not config.APLICAR_ESTORNO_DUPLICADO:
                r.update(status="EXCLUIDA", motivo="ESTORNO_DUPLICADO",
                         erro=f"{l['tipo'].lower()} de {l['id_ref']}, que já foi estornado/revertido por {duplos[l['id']]['id']}")
                resultado.append(r)
                continue
        if l["ec"] in config.ECS_BLOQUEADOS:
            r.update(status="EXCLUIDA", motivo="BLOQUEADO", erro=config.ECS_BLOQUEADOS[l["ec"]])
            resultado.append(r)
            continue
        if acima_do_maximo(l, por_id):
            r.update(status="EXCLUIDA", motivo="ACIMA_12X",
                     erro=f"venda em {l['parcelas']}x, acima do máximo de {config.MAX_PARCELAS}x (R57/S38)")
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
        bolso = l["valor_taxa"] - comissao        # S51: o que saiu do bolso do lojista (descontado pela Orbe - contratado)
        natureza = config.NATUREZA_ISENCAO if regra.startswith("R52") else config.NATUREZA_CONTRATO
        r.update(status="FATURAVEL", cnpj=contrato["cnpj"], contratada=taxa, regra=regra,
                 comissao=comissao, divergente=divergente, diferenca=dif, bolso=bolso, natureza=natureza)
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
            "regra": "R10/R11/R12 taxa contratada x bruto (CC01/CC04 cadastro), half-up por linha (R01)",
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
                "natureza": l["natureza"],
                "rastro": [("orbe", l["id"], l["diferenca"], f"{l['tipo']} bruto {l['bruto']}")],
            })
    return out


def pendencias(resultado, comissoes_chk, contratos):
    nomes = nome_por_cnpj(contratos)
    out = []
    fat = [l for l in resultado if l["status"] == "FATURAVEL"]
    # divergências por lojista e natureza (R13, H02, H04; S18/S34/S37/S38)
    div = [l for l in fat if l["divergente"]]
    for cnpj, ls_cnpj in sorted(_agrupar(div, "cnpj").items()):
        for natureza in (config.NATUREZA_ISENCAO, config.NATUREZA_CONTRATO):
            ls = [l for l in ls_cnpj if l["natureza"] == natureza]
            if ls:
                out.append(_pendencia_divergencia(ls, nomes[cnpj], natureza))
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
    # dupla reversão: uma pendência por linha (cada uma é uma decisão); ver pendencias_estorno_duplicado
    out += pendencias_estorno_duplicado(resultado)
    exc = [l for l in exc if l["motivo"] != "ESTORNO_DUPLICADO"]
    grupos = OrderedDict()
    for l in exc:
        grupos.setdefault((l["ec"], l["motivo"] == "ACIMA_12X"), []).append(l)
    for (ec, _), ls in grupos.items():
        bloqueado = ls[0]["motivo"] == "BLOQUEADO"
        vt = soma(l["valor_taxa"] for l in ls)
        bruto = soma(l["bruto"] for l in ls)
        if ls[0]["motivo"] == "ACIMA_12X":
            parc = ", ".join(sorted({f"{l['parcelas']}x" for l in ls}))
            motivo = (f"EC {ec}: {len(ls)} transação(ões) parcelada(s) acima de {config.MAX_PARCELAS}x ({parc}). "
                      f"A Tarvo não vende acima de {config.MAX_PARCELAS}x (R57/S38): fora de comissões e notas até "
                      f"esclarecer. Valor = taxa Orbe {fmt_br(vt)}.")
            out.append({"tipo": "PARCELAMENTO_ACIMA_12X", "ref_origem": f"EC {ec}", "valor": vt, "motivo": motivo,
                        "quem_decide": config.QUEM_HELENA_COMERCIAL,
                        "rastro": [("orbe", l["id"], l["valor_taxa"], f"{l['parcelas']}x valor_taxa Orbe") for l in ls]})
            continue
        if bloqueado:
            cnpj_b = config.CNPJ_EC_BLOQUEADO.get(ec)
            ident = (f" CNPJ {cnpj_b} (aba antiga da planilha, S45: só identifica o lojista; a taxa daquela aba não vale)."
                     if cnpj_b else "")
            motivo = (f"{ls[0]['erro']}.{ident} {len(ls)} transações (bruto {fmt_br(bruto)}) fora de comissões e notas "
                      "(o repasse ao lojista continua, S39/S45). "
                      f"Valor = taxa que a Orbe cobrou ({fmt_br(vt)}), só referência. Confirmar taxa contratada para faturar (cadastro/contrato: Comercial, R15/R63).")
            tipo = "LOJISTA_SEM_CONTRATO"
        else:
            erros = sorted({l["erro"] for l in ls})
            motivo = (f"EC {ec}: {len(ls)} transações sem taxa contratada determinável ({'; '.join(erros)}). "
                      f"Fora de comissões e notas até corrigir a planilha (cadastro/contrato: Comercial, R63). Valor = taxa Orbe {fmt_br(vt)}.")
            tipo = "TAXA_CONTRATADA_INDEFINIDA"
        out.append({"tipo": tipo, "ref_origem": f"EC {ec}", "valor": vt, "motivo": motivo,
                    "quem_decide": config.QUEM_COMERCIAL,
                    "rastro": [("orbe", l["id"], l["valor_taxa"], "valor_taxa Orbe") for l in ls]})
    out += alertas_antecipacao(resultado)
    return out


def pendencias_estorno_duplicado(resultado):
    """ORBE_ESTORNO_DUPLICADO: estorno/reversão de original já estornada/revertida. Não é aplicada
    (config.APLICAR_ESTORNO_DUPLICADO=False) ou é aplicada com aviso (True); o gestor decide."""
    out = []
    for l in resultado:
        if "estorno_duplicado_de" not in l:
            continue
        aplicada = l["status"] == "FATURAVEL"
        motivo = (f"{l['tipo']} {l['id']} (EC {l['ec']}, {l['arquivo']}) referencia {l['id_ref']}, que já foi "
                  f"estornada/revertida por {l['estorno_duplicado_de']}. Valor bruto {fmt_br(l['bruto'])}, "
                  f"taxa Orbe {fmt_br(l['valor_taxa'])}. ")
        motivo += ("Aplicada mesmo assim (config.APLICAR_ESTORNO_DUPLICADO=True): confirmar se é devida."
                   if aplicada else
                   "NÃO aplicada: fora de comissões e notas até decidir se a segunda reversão é devida "
                   "(config.APLICAR_ESTORNO_DUPLICADO).")
        out.append({"tipo": "ORBE_ESTORNO_DUPLICADO", "ref_origem": l["id"], "valor": l["valor_taxa"], "motivo": motivo,
                    "quem_decide": config.QUEM_HELENA,
                    "rastro": [(f"orbe@{l['arquivo']}", l["id"], l["valor_taxa"], f"{l['tipo']} duplicado valor_taxa Orbe")]})
    return out


def pendencias_linha_duplicada(duplicadas):
    """ORBE_LINHA_DUPLICADA: mesmo id_transacao repetido (entre arquivos ou no mesmo). Idêntica: conta uma vez.
    Valores diferentes (S52, critério nosso): vale a linha do arquivo de AJUSTE (o último em ordem de nome); a anterior
    sai do fechamento. Cada item: os campos da linha que SAIU + 'original' = a linha que vale."""
    out = []
    for l in duplicadas:
        o = l["original"]
        val = lambda x: (f"bruto {fmt_br(x['bruto'])}, taxa aplicada {x['taxa_aplicada']}%, "
                         f"valor_taxa {fmt_br(x['valor_taxa'])}, líquido {fmt_br(x['liquido'])}")
        if l["identica"]:
            motivo = (f"{l['id']} aparece de novo em {l['arquivo']} (linha {l['linha']}), idêntica a {o['arquivo']} "
                      f"(linha {o['linha']}). Contada uma vez só; a repetição foi ignorada. "
                      "Valor = taxa Orbe da linha repetida, só referência.")
        else:
            motivo = (f"{l['id']} aparece em dois arquivos com VALORES DIFERENTES. Vale a linha do arquivo de ajuste "
                      f"{o['arquivo']} (linha {o['linha']}): {val(o)}. Saiu do fechamento a linha de {l['arquivo']} "
                      f"(linha {l['linha']}): {val(l)}. Critério nosso (S52): o ajuste da Orbe substitui a linha anterior; "
                      "Helena confirma qual vale. Valor = valor_taxa da linha que saiu, só referência.")
        out.append({"tipo": "ORBE_LINHA_DUPLICADA", "ref_origem": l["id"], "valor": l["valor_taxa"],
                    "motivo": motivo, "quem_decide": config.QUEM_HELENA,
                    "rastro": [(f"orbe@{l['arquivo']}", l["id"], l["valor_taxa"],
                                "linha repetida (ignorada)" if l["identica"] else "linha substituída pelo ajuste (saiu)")]})
    return out


def competencia_mes(linhas):
    """(ano, mês) mais frequente de data_movimento (mesmo critério do fechamento)."""
    return Counter((l["data"].year, l["data"].month) for l in linhas).most_common(1)[0][0]


def alertas_antecipacao(resultado):
    """S42/S50 (critério nosso, config.ALERTA_ANTECIPACAO_SO_LOJISTA_NOVO): lojista NOVO (nenhuma transação com data de
    referência anterior ao mês e primeira transação depois do 1º dia) cuja antecipação acumulada, líquida das reversões
    já ocorridas, supera em algum dia as vendas acumuladas até a data. Alerta pelo PICO; o motivo cita as reversões
    posteriores e o saldo líquido no fim do mês. Vale para qualquer lojista, com ou sem contrato (R54/S23, H15)."""
    if not resultado:
        return []
    ano, mes = competencia_mes(resultado)
    primeiro_dia = date(ano, mes, 1)
    por_id = {l["id"]: l for l in resultado}
    por_ec = OrderedDict()
    for l in resultado:
        por_ec.setdefault(l["ec"], []).append(l)

    def data_ref(l):                                  # estorno/reversão: data da venda/antecipação original
        if l["tipo"] in ("ESTORNO", "REVERSAO ANTECIPACAO"):
            return l["data_orig"] or (por_id[l["id_ref"]]["data"] if l["id_ref"] in por_id else l["data"])
        return l["data"]

    out = []
    for ec, ls in por_ec.items():
        ants = [l for l in ls if l["tipo"] == "ANTECIPACAO"]
        if not ants:
            continue
        primeira = min(data_ref(l) for l in ls)
        if config.ALERTA_ANTECIPACAO_SO_LOJISTA_NOVO and not primeira > primeiro_dia:
            continue
        movs = sorted((l for l in ls if l["tipo"] in ("ANTECIPACAO", "REVERSAO ANTECIPACAO")),
                      key=lambda l: (l["data"], l["id"]))
        pico = None
        for dia in sorted({l["data"] for l in ants}):
            liq = soma(l["bruto"] for l in movs if l["data"] <= dia)
            vendas = soma(l["bruto"] for l in ls if l["tipo"] == "VENDA" and l["data"] <= dia)
            if liq > vendas and (pico is None or liq > pico[1]):
                pico = (dia, liq, vendas)
        if pico is None:
            continue
        dia, liq, vendas = pico
        ate = [l for l in movs if l["data"] <= dia]
        revs_dep = [l for l in movs if l["tipo"] == "REVERSAO ANTECIPACAO" and l["data"] > dia]
        total_ants = soma(l["bruto"] for l in ants)
        total_revs = soma(l["bruto"] for l in movs if l["tipo"] == "REVERSAO ANTECIPACAO")
        bloqueado = ec in config.ECS_BLOQUEADOS
        cnpj_b = config.CNPJ_EC_BLOQUEADO.get(ec)
        quem = f"{ls[0]['nome']} (EC {ec}" + (f", CNPJ {cnpj_b}" if cnpj_b else "") + ")"
        motivo = (f"Lojista novo {quem}: primeira transação em {primeira:%d/%m/%Y}, sem histórico antes do mês. "
                  f"Pico de antecipação acumulada de {fmt_br(liq)} em {dia:%d/%m/%Y} ({len(ate)} lançamentos de "
                  f"antecipação/reversão até a data), acima das vendas acumuladas até a data ({fmt_br(vendas)}). "
                  + (f"Reversões posteriores ao pico: {len(revs_dep)} ({fmt_br(soma(l['bruto'] for l in revs_dep))}). "
                     if revs_dep else "Sem reversões posteriores ao pico. ")
                  + f"No mês: {len(ants)} antecipações ({fmt_br(total_ants)}) e reversões de {fmt_br(-total_revs)}; "
                  f"saldo líquido de antecipação no fim do mês {fmt_br(total_ants + total_revs)}. "
                  "Antecipação deveria ser só sobre o que o lojista já vendeu e não há trava (R54/S23); critério do alerta "
                  "nosso (pico, lojista novo; S42/S50): alerta para Helena e Comercial"
                  + (", agravado por não haver contrato (H15)." if bloqueado else "."))
        out.append({"tipo": "ALERTA_ANTECIPACAO", "ref_origem": f"EC {ec}", "valor": liq, "motivo": motivo,
                    "quem_decide": config.QUEM_RISCO,
                    "rastro": [("orbe", l["id"], l["bruto"], f"{l['tipo']} bruto") for l in ate]})
    return out


def _pendencia_divergencia(ls, nome, natureza):
    """Uma pendência por lojista e natureza (S38). S51: o valor a devolver é o que saiu do bolso do lojista
    (valor_taxa da Orbe - comissão contratada, nas linhas divergentes); a lista divergencias_taxa.csv segue a fórmula
    bruto x diferença de taxa (S11), e a diferença entre as duas é o truncamento da Orbe. S41: concessão comercial
    fora do contrato = só devolver ao lojista (S18/S37); contrato = devolver e recuperar do parceiro (S34)."""
    formula = soma(l["diferenca"] for l in ls)
    total = soma(l["bolso"] for l in ls)
    ec = ls[0]["ec"]
    rastro = [("orbe", l["id"], l["bolso"], f"{l['tipo']} {natureza} valor_taxa Orbe - comissão contratada") for l in ls]
    base = (f"{len(ls)} transações de {nome} (EC {ec}); a devolver {fmt_br(total)} (valor_taxa descontado pela Orbe menos "
            "a comissão contratada, S51), já com estornos de vendas divergentes (H02). ")
    trunc = (f"A fórmula da lista de divergências (bruto x diferença de taxa) soma {fmt_br(formula)}; a diferença de "
             f"{fmt_br(formula - total)} é truncamento da Orbe (S51). ")
    if natureza == config.NATUREZA_ISENCAO:
        desc = config.DESCRICAO_NATUREZA[natureza]
        motivo = (f"{desc[0].upper() + desc[1:]} (R52/S41): a Orbe cobrou pela planilha em {base}"
                  f"Taxa zero acordada pelo Comercial ({config.ISENCAO_CONDICAO.get(ec, 'cadastro')}/S07), fora do contrato, "
                  "que ninguém comunicou à Orbe (S18/S30). NÃO entra na cobrança da "
                  f"Orbe: é devolução ao lojista de {fmt_br(total)}, do caixa da Tarvo (S18/S34/S37). {trunc}"
                  "Detalhe por transação em divergencias_taxa.csv (natureza ISENCAO_NAO_INFORMADA, cobrar_parceiro N).")
        return {"tipo": "DEVOLUCAO_LOJISTA_ISENCAO", "ref_origem": f"EC {ec}", "valor": total, "motivo": motivo,
                "quem_decide": config.QUEM_HELENA_COMERCIAL, "rastro": rastro}
    a_menos = sum(1 for l in ls if l["taxa_aplicada"] < l["contratada"])
    motivo = ("Orbe aplicou taxa diferente da contratada (o que decide é a condição contratada, aditivo/negociação "
              f"registrada, não o aviso à Orbe: S41) em {base}")
    if a_menos:
        motivo += f"{a_menos} transações com taxa ABAIXO do contrato (H04/S24): Helena decide caso a caso. "
    if total >= 0:
        motivo += f"Devolver ao lojista {fmt_br(total)}; recuperar do parceiro (Orbe) {fmt_br(total)} (R60/S34/S51). "
    motivo += trunc + "Lista em divergencias_taxa.csv (natureza CONTRATO, cobrar_parceiro S)."
    return {"tipo": "DIVERGENCIA_TAXA_CHECKOUT", "ref_origem": f"EC {ec}", "valor": total, "motivo": motivo,
            "quem_decide": config.QUEM_HELENA, "rastro": rastro}
