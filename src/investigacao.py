"""Dossiê determinístico de investigação das divergências (PLANO_IA_01, Fase 1).

Um GRUPO por contraparte (ORBE/PONTE) x lojista x natureza. Para cada grupo, só FATOS calculados dos
arquivos (com as refs de origem), a condição contratual e as respostas do financeiro (S##) copiadas de
config.RESPOSTAS_FINANCEIRO. Nenhuma hipótese, nenhum texto livre: isso é papel da IA (Fase 2), que lê
este dossiê.

Saída: <saida>/investigacao/dossie.json (schema fixo, o Dev B programa contra ele) e dossie.md (legível).
Mesma entrada -> bytes idênticos (ordenação estável, sem data/hora). Os 6 CSVs oficiais não dependem
deste módulo: ele só LÊ o resultado do fechamento.
"""
import json
from collections import Counter, OrderedDict
from decimal import Decimal
from pathlib import Path

from . import config
from .checkout import contratos_ativos, nome_por_cnpj, referencia_taxa
from .dinheiro import fmt, fmt_br, soma

FAIXAS = ["DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX", "ANTECIPACAO"]
ROTULO = {"DEBITO": "débito", "CREDITO A VISTA": "crédito à vista", "PARC_2_6": "2–6x", "PARC_7_12": "7–12x",
          "PIX": "Pix", "ANTECIPACAO": "antecipação"}
CONTRAPARTE = {"CHECKOUT": "ORBE", "REMESSA": "PONTE"}
NOME_CONTRAPARTE = {"ORBE": "Orbe", "PONTE": "Ponte"}
ROTULO_NATUREZA = {config.NATUREZA_CONTRATO: "divergência de contrato",
                   config.NATUREZA_ISENCAO: "concessão comercial fora do contrato (devolução do bolso da Tarvo)"}   # S41
ZERO = Decimal("0")
CEM = Decimal("100")


# ---------------------------------------------------------------- formatação pt-BR (texto dos fatos)
def _num(x, casas_max=4):
    s = f"{Decimal(x):.{casas_max}f}".rstrip("0").rstrip(".")
    if s in ("", "-0"):
        s = "0"
    if "." in s and len(s.split(".")[1]) == 1:
        s += "0"                                     # 2,5 -> 2,50 (taxas com 2 casas)
    return s.replace(".", ",")


def _pct(x):
    return f"{_num(x)}%"


def _pp(x):
    return ("+" if x > 0 else "") + f"{_num(x)} p.p."


def _d(d):
    return f"{d:%d/%m/%Y}"


def _porc(a, b):
    v = (Decimal(a) * CEM / Decimal(b)).quantize(Decimal("0.1"))
    s = f"{v:.1f}".replace(".", ",")
    return (s[:-2] if s.endswith(",0") else s) + "%"


def _frase(txt):
    return txt if txt.endswith(".") else txt + "."


def _vig(c):
    if c["inicio"] and c["fim"]:
        return f"de {_d(c['inicio'])} a {_d(c['fim'])}"
    if c["inicio"]:
        return f"desde {_d(c['inicio'])}"
    if c["fim"]:
        return f"até {_d(c['fim'])}"
    return f"vigência '{c['vigencia_texto']}'"


def _lista(itens):
    return ", ".join(itens)


def _lista_e(itens):
    itens = list(itens)
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


# ---------------------------------------------------------------- montagem dos grupos
def _fato(fatos, texto, refs=()):
    fatos.append({"id": f"F{len(fatos) + 1}", "texto": texto, "refs": list(refs)[:3]})


def _respostas(linha, cnpj):
    return [{"id": s, "texto": config.TEXTOS_FINANCEIRO[s]}
            for s in config.RESPOSTAS_FINANCEIRO.get((linha, cnpj), [])]


def _linhas_lojista(contratos, cnpj):
    return sorted((c for c in contratos_ativos(contratos) if c["cnpj"] == cnpj), key=lambda c: c["linha"])


def _vigente(linhas, data):
    ok = [c for c in linhas if c["vigencia_ok"] and (c["inicio"] is None or c["inicio"] <= data)
          and (c["fim"] is None or data <= c["fim"])]
    return ok[0] if len(ok) == 1 else None


def _fato_vigencia(fatos, linhas, d0, d1, refs):
    if len(linhas) == 1:
        c = linhas[0]
        _fato(fatos, f"Planilha: linha única do lojista (linha {c['linha']}, {_vig(c)}), sem mudança de vigência; "
                     f"a divergência começa em {_d(d0)}.", refs)
        return
    partes = [f"linha {c['linha']} {_vig(c)}" for c in linhas]
    inicios = {c["inicio"] for c in linhas if c["inicio"]}
    if all(c["inicio"] for c in linhas):          # a linha mais antiga não é mudança
        inicios -= {min(inicios)}
    mudancas = sorted(inicios)
    txt = f"Planilha: {'; '.join(partes)}."
    for m in mudancas:
        dias = (d0 - m).days
        rel = "no mesmo dia" if dias == 0 else (f"{dias} dia(s) depois" if dias > 0 else f"{-dias} dia(s) antes")
        txt += f" Mudança de vigência em {_d(m)}; a divergência começa {rel} ({_d(d0)}) e termina em {_d(d1)}."
    _fato(fatos, txt, refs)


def _grupos_checkout(r, antigas):
    d = r["dados"]
    contratos = d["contratos"]
    nomes = nome_por_cnpj(contratos)
    por_id = {l["id"]: l for l in d["orbe"]}
    fat = [l for l in r["checkout"] if l["status"] == "FATURAVEL"]
    ref = {}
    for l in fat:
        data, fx, _ = referencia_taxa(l, por_id)
        ref[l["id"]] = (data, fx)
    grupos = OrderedDict()
    for l in fat:
        if l["divergente"]:
            grupos.setdefault((l["cnpj"], l["natureza"]), []).append(l)
    out = []
    for (cnpj, natureza), ls in sorted(grupos.items()):
        out.append(_grupo_checkout(cnpj, natureza, ls, fat, ref, contratos, nomes, antigas))
    return out


def _grupo_checkout(cnpj, natureza, ls, fat, ref, contratos, nomes, antigas):
    chave = lambda l: (ref[l["id"]][0], l["id"])
    ls = sorted(ls, key=chave)
    todas = sorted((l for l in fat if l["cnpj"] == cnpj), key=chave)
    linhas = _linhas_lojista(contratos, cnpj)
    total = soma(l["diferenca"] for l in ls)                    # fórmula da lista de divergências (S11)
    devolver = soma(l["bolso"] for l in ls)                     # S51: valor_taxa Orbe - comissão contratada
    recuperar = devolver if natureza == config.NATUREZA_CONTRATO else ZERO
    d0, d1 = ref[ls[0]["id"]][0], ref[ls[-1]["id"]][0]
    janela = [l for l in todas if d0 <= ref[l["id"]][0] <= d1]
    fx_div = Counter(ref[l["id"]][1] for l in ls)
    afetadas = [f for f in FAIXAS if f in fx_div]
    fatos = []

    # F: quantidade e valor
    n_est = sum(1 for l in ls if l["tipo"] == "ESTORNO")
    txt = f"{len(ls)} transações divergentes, líquido {fmt_br(total)}"
    if n_est:
        txt += f" (inclui {n_est} estorno(s) de vendas divergentes, com sinal negativo)"
    txt += (f". A devolver ao lojista (o que saiu do bolso dele: valor_taxa da Orbe menos a comissão contratada, S51): "
            f"{fmt_br(devolver)}; a recuperar da {NOME_CONTRAPARTE['ORBE']}: {fmt_br(recuperar)}. "
            f"A diferença para o líquido pela fórmula ({fmt_br(total - devolver)}) é truncamento da Orbe.")
    _fato(fatos, txt, _exemplos(ls))
    # F: datas
    dias = (d1 - d0).days + 1
    _fato(fatos, f"Primeira transação divergente em {_d(d0)} e última em {_d(d1)} ({dias} dia(s) corrido(s)), "
                 "pela data da venda (no estorno, a da venda original).", [ls[0]["id"], ls[-1]["id"]])
    # F: faixas afetadas e não afetadas no mesmo período
    _fato(fatos, "Faixas afetadas: " + _lista(f"{ROTULO[f]} ({fx_div[f]})" for f in afetadas) + ".",
          [next(l["id"] for l in ls if ref[l["id"]][1] == f) for f in afetadas])
    ok_jan = [l for l in janela if not l["divergente"]]
    fx_ok = Counter(ref[l["id"]][1] for l in ok_jan)
    nao_afetadas = [f for f in FAIXAS if f in fx_ok and f not in fx_div]
    parciais = [f for f in FAIXAS if f in fx_ok and f in fx_div]
    if nao_afetadas:
        _fato(fatos, f"No mesmo período ({_d(d0)} a {_d(d1)}), sem divergência: "
                     + _lista(f"{ROTULO[f]} ({fx_ok[f]})" for f in nao_afetadas) + ".",
              [next(l["id"] for l in ok_jan if ref[l["id"]][1] == f) for f in nao_afetadas])
    else:
        _fato(fatos, f"No mesmo período ({_d(d0)} a {_d(d1)}), não houve transação do lojista em faixa sem divergência.")
    if parciais:
        _fato(fatos, "Faixas com transações divergentes e não divergentes no período: "
                     + _lista(f"{ROTULO[f]} ({fx_ok[f]} sem divergência)" for f in parciais) + ".",
              [next(l["id"] for l in ok_jan if ref[l["id"]][1] == f) for f in parciais])
    # F: diferença em p.p.
    deltas = {f: sorted({l["taxa_aplicada"] - l["contratada"] for l in ls if ref[l["id"]][1] == f}) for f in afetadas}
    todos = sorted({x for v in deltas.values() for x in v})
    if len(todos) == 1:
        _fato(fatos, f"Diferença constante de {_pp(todos[0])} sobre a taxa contratada em todas as "
                     f"{len(ls)} transações.")
        contr = {f: sorted({l["contratada"] for l in ls if ref[l["id"]][1] == f}) for f in afetadas}
        aplic = {f: sorted({l["taxa_aplicada"] for l in ls if ref[l["id"]][1] == f}) for f in afetadas}
        if len(afetadas) > 1 and all(len(contr[f]) == 1 and len(aplic[f]) == 1 for f in afetadas):
            _fato(fatos, f"Em todas as faixas afetadas, a taxa aplicada = contratada {_pp(todos[0])}: "
                         + "; ".join(f"{ROTULO[f]} {_pct(contr[f][0])} → {_pct(aplic[f][0])}" for f in afetadas) + ".")
    elif all(len(v) == 1 for v in deltas.values()):
        _fato(fatos, f"Diferença variável de {_pp(todos[0])} a {_pp(todos[-1])}, constante dentro de cada faixa: "
                     + _frase("; ".join(f"{ROTULO[f]} {_pp(deltas[f][0])}" for f in afetadas)))
    else:
        _fato(fatos, f"Diferença variável de {_pp(todos[0])} a {_pp(todos[-1])}.")
    # F: a taxa aplicada coincide com...
    _fatos_coincidencia(fatos, cnpj, natureza, ls, ref, afetadas, linhas, contratos, nomes, antigas, d0, d1, ok_jan)
    # F: vigência na planilha x início da divergência
    _fato_vigencia(fatos, linhas, d0, d1, [ls[0]["id"]])
    if natureza == config.NATUREZA_ISENCAO:
        ecs = sorted({l["ec"] for l in ls})
        for ec in ecs:
            ini, fim = config.TAXA_ZERO_CHECKOUT[ec]
            dias = (d0 - ini).days
            rel = "no mesmo dia" if dias == 0 else f"{dias} dia(s) depois"
            _fato(fatos, "A planilha de taxas não registra a isenção; ela vem do acordo comercial informado pelo "
                         f"financeiro (S07), válido de {_d(ini)} a {_d(fim)}; a divergência começa {rel}"
                         f"{'' if dias == 0 else f' ({_d(d0)})'}.", [ls[0]["id"]])
    # F: proporção
    jan_af = [l for l in janela if ref[l["id"]][1] in fx_div]
    n_div_jan = sum(1 for l in janela if l["divergente"])
    _fato(fatos, f"Entre {_d(d0)} e {_d(d1)}, {sum(1 for l in jan_af if l['divergente'])} de {len(jan_af)} transações "
                 f"das faixas afetadas divergem ({_porc(sum(1 for l in jan_af if l['divergente']), len(jan_af))}); "
                 f"somando todas as faixas, {n_div_jan} de {len(janela)} ({_porc(n_div_jan, len(janela))}).")
    fora = [l for l in todas if not d0 <= ref[l["id"]][0] <= d1]
    if fora:
        antes = [l for l in fora if ref[l["id"]][0] < d0]
        depois = [l for l in fora if ref[l["id"]][0] > d1]
        n_div_fora = sum(1 for l in fora if l["divergente"])
        partes = []
        if antes:
            partes.append(f"{len(antes)} com data de referência antes de {_d(d0)}")
        if depois:
            partes.append(f"{len(depois)} depois de {_d(d1)}")
        _fato(fatos, f"Fora desse período, o lojista teve {len(fora)} transação(ões) faturável(is) no relatório do mês "
                     f"({'; '.join(partes)}), " + ("nenhuma divergente." if not n_div_fora else f"{n_div_fora} divergente(s)."),
              [l["id"] for l in (antes[:1] + depois[:1])])
    else:
        _fato(fatos, f"Todas as {len(todas)} transações faturáveis do lojista no relatório do mês estão nesse período.")

    ecs = sorted({l["ec"] for l in ls})
    return {
        "id_grupo": None, "contraparte": "ORBE", "linha_negocio": "CHECKOUT", "lojista": nomes[cnpj], "cnpj": cnpj,
        "ec_orbe": "|".join(ecs), "natureza": natureza, "qtd": len(ls),
        "valor_divergencia_brl": fmt(total), "valor_devolver_lojista_brl": fmt(devolver),
        "valor_recuperar_parceiro_brl": fmt(recuperar),
        "condicao_contratual": _condicao_checkout(linhas, ecs),
        "fatos": fatos, "respostas_financeiro": _respostas("CHECKOUT", cnpj), "exemplos": _exemplos(ls),
        "_total": total,
    }


def _fatos_coincidencia(fatos, cnpj, natureza, ls, ref, afetadas, linhas, contratos, nomes, antigas, d0, d1, ok_jan):
    aplic = {f: sorted({l["taxa_aplicada"] for l in ls if ref[l["id"]][1] == f}) for f in afetadas}
    unicas = {f: v[0] for f, v in aplic.items() if len(v) == 1}
    # faixas NÃO afetadas com transações no período: taxa aplicada (= contratada, por não divergirem)
    ap_ok = {}
    for l in ok_jan:
        f = ref[l["id"]][1]
        if f not in afetadas:
            ap_ok.setdefault(f, set()).add(l["taxa_aplicada"])
    nao_afetadas = {f: min(v) for f, v in ap_ok.items() if len(v) == 1}
    explicada = set()
    vig0 = _vigente(linhas, d0)
    # vigência anterior / posterior do mesmo lojista
    for rot, cand in (("anterior", [c for c in linhas if c["fim"] and c["fim"] < d0]),
                      ("posterior", [c for c in linhas if c["inicio"] and c["inicio"] > d1])):
        for c in cand:
            bate = [f for f, a in unicas.items() if c["taxas"].get(f) == a]
            if bate:
                explicada.update(bate)
                _fato(fatos, f"Taxa aplicada = vigência {rot} do mesmo lojista na planilha (linha {c['linha']}, "
                             f"{_vig(c)}) em: " + _lista(f"{ROTULO[f]} {_pct(unicas[f])}" for f in bate)
                      + (f"; a vigente no período (linha {vig0['linha']}) é "
                         + _lista(f"{ROTULO[f]} {_pct(vig0['taxas'][f])}" for f in bate) if vig0 else "") + ".")
    # taxa "cheia" da própria linha, vigente antes da isenção
    if natureza == config.NATUREZA_ISENCAO and vig0:
        bate = [f for f, a in unicas.items() if vig0["taxas"].get(f) == a]
        if bate:
            explicada.update(bate)
            n = sum(1 for l in ls if ref[l["id"]][1] in bate)
            _fato(fatos, f"Taxa aplicada = taxa da linha {vig0['linha']} da planilha ({_vig(vig0)}), a cobrada antes da "
                         f"isenção, em {n} de {len(ls)} transações: "
                         + _lista(f"{ROTULO[f]} {_pct(unicas[f])}" for f in bate) + ".")
    # aba de ano anterior (mesmo CNPJ)
    for aba in sorted({a["aba"] for a in antigas}):
        linha_ant = next((a for a in antigas if a["aba"] == aba and a["cnpj"] == cnpj), None)
        if not linha_ant:
            continue
        ant = linha_ant["taxas"]
        bate_af = [f for f, a in unicas.items() if ant.get(f) == a]
        if not bate_af:
            continue
        explicada.update(bate_af)
        # todas as faixas com transação no período e taxa na aba antiga (afetadas e não afetadas)
        aplicada = {**{f: a for f, a in nao_afetadas.items()}, **unicas}
        comparaveis = [f for f in FAIXAS if f in aplicada and ant.get(f) is not None]
        bate = [f for f in comparaveis if ant[f] == aplicada[f]]
        nao_af = [f for f in comparaveis if f in unicas and f not in bate]
        nao_ok = [f for f in comparaveis if f not in unicas and f not in bate]
        if len(bate) == len(comparaveis):
            _fato(fatos, f"A aba '{aba}' da planilha (mesmo CNPJ) coincide com a taxa aplicada em todas as "
                         f"{len(comparaveis)} faixas com transações no período: "
                         + _lista(f"{ROTULO[f]} {_pct(aplicada[f])}" for f in bate) + ".")
            continue
        txt = (f"A aba '{aba}' da planilha (mesmo CNPJ) coincide com a taxa aplicada em {len(bate)} de "
               f"{len(comparaveis)} faixas com transações no período ("
               + _lista(f"{ROTULO[f]} {_pct(aplicada[f])}" for f in bate) + ")")
        partes = []
        if nao_af:
            partes.append(_lista_e(f"{ROTULO[f]} (aplicada {_pct(aplicada[f])}; aba {_pct(ant[f])})" for f in nao_af))
        if nao_ok:
            seg = _lista_e(f"{ROTULO[f]} (aplicada {_pct(aplicada[f])}; aba {_pct(ant[f])})" for f in nao_ok)
            seg += (f", que seguiram a taxa contratada vigente (linha {vig0['linha']}, {_vig(vig0)})" if vig0
                    else ", que seguiram a taxa contratada")
            partes.append(seg)
        txt += "; não explica " + (", nem ".join(partes)) + "."
        _fato(fatos, txt)
    # taxa vigente de outro lojista (só para faixas ainda não explicadas pelo próprio lojista)
    sem = [f for f in afetadas if f in unicas and f not in explicada]
    outros = [c for c in contratos_ativos(contratos) if c["cnpj"] != cnpj and _vigente([c], d0)]
    nenhuma = []
    for f in sem:
        quem = sorted({nomes[c["cnpj"]] for c in outros if c["taxas"].get(f) == unicas[f]})
        if quem:
            extra = f" e mais {len(quem) - 3}" if len(quem) > 3 else ""
            _fato(fatos, f"Taxa aplicada em {ROTULO[f]} ({_pct(unicas[f])}) = taxa vigente de outro(s) lojista(s) na "
                         f"planilha: {_lista(quem[:3])}{extra}.")
        else:
            nenhuma.append(f)
    if nenhuma:
        _fato(fatos, "Taxa aplicada sem correspondência na planilha (vigente, outras vigências, abas antigas ou outros "
                     "lojistas) em: " + _lista(f"{ROTULO[f]} {_pct(unicas[f])}" for f in nenhuma) + ".")


def _condicao_checkout(linhas, ecs):
    partes = []
    for c in linhas:
        tx = "; ".join(f"{ROTULO[f]} {_pct(c['taxas'][f])}" for f in FAIXAS if c["taxas"].get(f) is not None)
        obs = f" (obs: '{c['obs']}')" if c["obs"] else ""
        partes.append(f"Planilha linha {c['linha']} ({_vig(c)}): {tx}{obs}")
    for ec in ecs:
        if ec in config.TAXA_ZERO_CHECKOUT:
            ini, fim = config.TAXA_ZERO_CHECKOUT[ec]
            partes.append(f"Isenção {config.ISENCAO_CONDICAO.get(ec, 'cadastro')}/S07: taxa zero no checkout (MDR e antecipação) de {_d(ini)} a {_d(fim)}")
    return " | ".join(partes)


def _exemplos(ls):
    return [l.get("id") or l.get("op") for l in sorted(ls, key=lambda l: (-abs(l["diferenca"]), l.get("id") or l.get("op")))[:3]]


def _grupos_remessa(r):
    contratos = r["dados"]["contratos"]
    nomes = nome_por_cnpj(contratos)
    validas = [o for o in r["remessa"] if o["status"] == "VALIDA"]
    grupos = OrderedDict()
    for o in validas:
        if o["divergente"]:
            grupos.setdefault(o["cnpj"], []).append(o)
    out = []
    for cnpj, ops in sorted(grupos.items()):
        ops = sorted(ops, key=lambda o: (o["data"], o["op"]))
        todas = sorted((o for o in validas if o["cnpj"] == cnpj), key=lambda o: (o["data"], o["op"]))
        linhas = _linhas_lojista(contratos, cnpj)
        total = soma(o["diferenca"] for o in ops)                # fórmula da lista de divergências (S11)
        a_mais = soma(o["dif_contrato"] for o in ops)            # S51: Spread R$ efetivamente cobrado a mais
        d0, d1 = ops[0]["data"], ops[-1]["data"]
        fatos = []
        _fato(fatos, f"{len(ops)} operações com spread acima do contratado; Spread R$ efetivamente cobrado a mais "
                     f"(realizado menos contratado x PTAX x Valor ME, S51) {fmt_br(a_mais)}; pela fórmula da lista de "
                     f"divergências {fmt_br(total)}. A devolver ao lojista: {fmt_br(a_mais)}; a recuperar da Ponte: "
                     f"{fmt_br(a_mais)}.",
              _exemplos_rem(ops))
        _fato(fatos, f"Primeira operação divergente contratada em {_d(d0)} e última em {_d(d1)} "
                     f"({(d1 - d0).days + 1} dia(s) corrido(s)).", [ops[0]["op"], ops[-1]["op"]])
        moedas = Counter(o["moeda"] for o in ops)
        _fato(fatos, "Moedas das operações divergentes: " + _lista(f"{m} ({n})" for m, n in sorted(moedas.items())) + ".")
        deltas = sorted((o["spread_pct"] - o["contratado"]) * CEM for o in ops)
        if deltas[0] == deltas[-1]:
            _fato(fatos, f"Diferença constante de {_pp(deltas[0])} sobre o spread contratado.")
        else:
            _fato(fatos, f"Diferença variável de {_pp(deltas[0])} a {_pp(deltas[-1])} sobre o spread contratado "
                         f"({_pct(ops[0]['contratado'] * CEM)}).")
        aplic = sorted(o["spread_pct"] for o in ops)
        perto = [o for o in ops if abs(o["spread_pct"] - config.SPREAD_PADRAO) < config.TOLERANCIA_SPREAD]
        if perto:
            _fato(fatos, f"Spread aplicado de {_pct(aplic[0] * CEM)} a {_pct(aplic[-1] * CEM)}: coincide com o spread "
                         f"padrão de {_pct(config.SPREAD_PADRAO * CEM)} (CC03) dentro da tolerância de 0,01 p.p. (H06) em "
                         f"{len(perto)} de {len(ops)} operações; contratado {_pct(ops[0]['contratado'] * CEM)}.",
                  [perto[0]["op"]])
        else:
            _fato(fatos, f"Spread aplicado de {_pct(aplic[0] * CEM)} a {_pct(aplic[-1] * CEM)}; não coincide com o "
                         f"spread padrão de {_pct(config.SPREAD_PADRAO * CEM)}.")
        _fato_vigencia(fatos, linhas, d0, d1, [ops[0]["op"]])
        jan = [o for o in todas if d0 <= o["data"] <= d1]
        _fato(fatos, f"Entre {_d(d0)} e {_d(d1)}, {len(ops)} de {len(jan)} operações válidas do lojista divergem "
                     f"({_porc(len(ops), len(jan))}); no mês, {len(todas)} operações válidas do lojista.")
        outros = OrderedDict()
        for o in validas:
            if o["cnpj"] != cnpj and o["contratado"] is not None and o["contratado"] != config.SPREAD_PADRAO:
                outros.setdefault(o["cnpj"], []).append(o)
        if outros:
            n_ops = sum(len(v) for v in outros.values())
            n_div = sum(1 for v in outros.values() for o in v if o["divergente"])
            desc = _lista(f"{nomes.get(c, c)} {_pct(v[0]['contratado'] * CEM)}" for c, v in sorted(outros.items()))
            _fato(fatos, f"No mês, outros {len(outros)} lojista(s) com spread contratado diferente do padrão ({desc}) "
                         f"tiveram {n_ops} operações válidas, " + ("nenhuma divergente." if not n_div else f"{n_div} divergente(s)."),
                  [v[0]["op"] for _, v in sorted(outros.items())])
        out.append({
            "id_grupo": None, "contraparte": "PONTE", "linha_negocio": "REMESSA", "lojista": nomes.get(cnpj, ops[0]["cliente"]),
            "cnpj": cnpj, "ec_orbe": None, "natureza": config.NATUREZA_CONTRATO, "qtd": len(ops),
            "valor_divergencia_brl": fmt(total), "valor_devolver_lojista_brl": fmt(a_mais),
            "valor_recuperar_parceiro_brl": fmt(a_mais),
            "condicao_contratual": _condicao_remessa(linhas),
            "fatos": fatos, "respostas_financeiro": _respostas("REMESSA", cnpj), "exemplos": _exemplos_rem(ops),
            "_total": total,
        })
    return out


def _exemplos_rem(ops):
    return [o["op"] for o in sorted(ops, key=lambda o: (-abs(o["diferenca"]), o["op"]))[:3]]


def _condicao_remessa(linhas):
    partes = []
    for c in linhas:
        sp = (f"spread remessa {_pct(c['spread'] * CEM)}" if c["spread"] is not None
              else f"spread remessa padrão {_pct(config.SPREAD_PADRAO * CEM)} (célula em branco/'padrão', CC03)")
        obs = f" (obs: '{c['obs']}')" if c["obs"] else ""
        partes.append(f"Planilha linha {c['linha']} ({_vig(c)}): {sp}{obs}")
    partes.append(f"Padrão quando em branco: {_pct(config.SPREAD_PADRAO * CEM)} sobre PTAX (CC03)")
    return " | ".join(partes)


# ---------------------------------------------------------------- API
def gerar(r, antigas=()):
    """r = resultado de fechamento.executar; antigas = leitores.ler_taxas_antigas(planilha)."""
    grupos = _grupos_checkout(r, list(antigas)) + _grupos_remessa(r)
    grupos.sort(key=lambda g: (-g["_total"], g["contraparte"], g["cnpj"], g["natureza"]))
    for i, g in enumerate(grupos, start=1):
        g["id_grupo"] = f"G{i:02d}"
        del g["_total"]
    chaves = ["id_grupo", "contraparte", "linha_negocio", "lojista", "cnpj", "ec_orbe", "natureza", "qtd",
              "valor_divergencia_brl", "valor_devolver_lojista_brl", "valor_recuperar_parceiro_brl",
              "condicao_contratual", "fatos", "respostas_financeiro", "exemplos"]
    return {"competencia": r["competencia"], "grupos": [{k: g[k] for k in chaves} for g in grupos]}


def markdown(dossie):
    L = [f"# Dossiê de investigação das divergências — competência {dossie['competencia']}", "",
         "Gerado pelo fechamento, de forma determinística: só **fatos** calculados dos arquivos do mês, com a "
         "transação ou operação de origem. Não há hipótese de causa aqui; quem decide é a analista.", "",
         "| Grupo | Parceiro | Lojista | Natureza | Qtd | Divergência | Devolver ao lojista | Recuperar do parceiro |",
         "|---|---|---|---|---:|---:|---:|---:|"]
    for g in dossie["grupos"]:
        L.append(f"| {g['id_grupo']} | {NOME_CONTRAPARTE[g['contraparte']]} | {g['lojista']} | "
                 f"{ROTULO_NATUREZA[g['natureza']]} | {g['qtd']} | {fmt_br(Decimal(g['valor_divergencia_brl']))} | "
                 f"{fmt_br(Decimal(g['valor_devolver_lojista_brl']))} | "
                 f"{fmt_br(Decimal(g['valor_recuperar_parceiro_brl']))} |")
    for g in dossie["grupos"]:
        ident = f"CNPJ {g['cnpj']}" + (f" · EC {g['ec_orbe']}" if g["ec_orbe"] else "")
        L += ["", f"## {g['id_grupo']} — {g['lojista']} ({NOME_CONTRAPARTE[g['contraparte']]}, "
                  f"{g['linha_negocio'].lower()}, {ROTULO_NATUREZA[g['natureza']]})", "",
              f"- {ident}",
              f"- Divergência: {fmt_br(Decimal(g['valor_divergencia_brl']))} em {g['qtd']} "
              f"{'transações' if g['linha_negocio'] == 'CHECKOUT' else 'operações'}",
              f"- Devolver ao lojista: {fmt_br(Decimal(g['valor_devolver_lojista_brl']))} · Recuperar do parceiro: "
              f"{fmt_br(Decimal(g['valor_recuperar_parceiro_brl']))}",
              f"- Condição contratual: {g['condicao_contratual']}", "", "### Fatos", ""]
        for f in g["fatos"]:
            refs = f" _(ref.: {', '.join(f['refs'])})_" if f["refs"] else ""
            L.append(f"- **{f['id']}** {f['texto']}{refs}")
        L += ["", "### O que o financeiro já respondeu", ""]
        L += [f"- **{s['id']}** {s['texto']}" for s in g["respostas_financeiro"]] or ["- Nenhuma resposta específica."]
        L += ["", f"Exemplos: {', '.join(g['exemplos'])}"]
    return "\n".join(L) + "\n"


def escrever(dossie, pasta):
    pasta = Path(pasta) / "investigacao"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "dossie.json").write_bytes((json.dumps(dossie, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (pasta / "dossie.md").write_bytes(markdown(dossie).encode("utf-8"))
    return pasta
