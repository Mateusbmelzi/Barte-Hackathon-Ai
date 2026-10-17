"""CLI do fechamento mensal.

Uso:  python -m src.fechamento --entrada <pasta com os arquivos do mês> --saida <pasta> [--cadastro <pasta>] [--ia]
Defaults: entrada = raiz do projeto; saida = <raiz>/saida; cadastro = <raiz>/cadastro (condições comerciais por cliente).
--ia: além do dossiê, pede hipóteses à IA (src/ia.py) e grava em execucoes/cli_<data_hora>/investigacao_ia.json
      (fora de saida/, que fica determinística). Sem chave/biblioteca: avisa e segue.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import cadastro as cad, checkout, config, extratos, investigacao, remessa, saidas
from .dinheiro import soma, fmt_br
from .leitores import ler_taxas_antigas, ler_tudo_parcial

RAIZ = Path(__file__).resolve().parent.parent
CADASTRO_PADRAO = RAIZ / "cadastro"


def _competencia(orbe):
    """Mês mais frequente de data_movimento na Orbe -> ((ano, mes), 'MM/AAAA')."""
    (ano, mes), _ = Counter((l["data"].year, l["data"].month) for l in orbe).most_common(1)[0]
    return (ano, mes), f"{mes:02d}/{ano}"


def _numerar(itens, prefixo):
    for i, it in enumerate(itens, start=1):
        it["id"] = f"{prefixo}-{i:04d}"
    return itens


def _conferir_rastro(itens, valor_de):
    """Regra central do edital: soma do rastro por id_saida == valor reportado, ao centavo."""
    for it in itens:
        v = valor_de(it)
        if v is None:
            continue
        s = soma(r[2] for r in it["rastro"])
        if s != v:
            raise AssertionError(f"rastro de {it['id']} soma {s} != valor reportado {v}")


def _competencia_alternativa(d):
    """Sem Orbe: competência pelo mês mais frequente das datas da Ponte ou, na falta, dos extratos."""
    for datas in ([o["data"] for o in d["ponte"]], [m["data"] for m in d["aurora"] + d["meridiano"]]):
        if datas:
            (ano, mes), _ = Counter((x.year, x.month) for x in datas).most_common(1)[0]
            return (ano, mes), f"{mes:02d}/{ano}"
    return None, "indisponível"


def _pendencias_bloqueio(bloqueios):
    """Uma pendência por fonte bloqueada (valor 0): qual arquivo, o que ficou bloqueado, quem libera."""
    out = []
    for b in bloqueios:
        f = b["fonte"]
        rotulo = config.ROTULO_FONTE.get(f, f)
        efeito = config.EFEITO_BLOQUEIO.get(f, "parte do fechamento não calculada")
        if b["tipo"] == "CADASTRO_AUSENTE":
            motivo = (f"Condições comerciais não aplicadas: o cadastro ({b['detalhe']}) não foi encontrado. Isenções, "
                      "taxas especiais, de-para de EC e bloqueios de faturamento foram ignorados; notas e comissões "
                      "podem estar erradas (ex.: lojista isento volta a ser faturado). O fechamento foi marcado como "
                      "PROVISORIO. Restaurar o cadastro (pasta cadastro/ ou --cadastro <pasta>) e rodar de novo, "
                      "ou liberar o mês assim.")
            out.append({"tipo": b["tipo"], "ref_origem": b["arquivo"], "valor": Decimal("0"), "motivo": motivo,
                        "quem_decide": config.QUEM_HELENA_COMERCIAL, "rastro": []})
            continue
        if b["tipo"] == "FONTE_AUSENTE":
            motivo = (f"Falta o arquivo da fonte {rotulo} (esperado nome '{b['arquivo']}'). Bloqueado: {efeito}. "
                      "O restante foi fechado e está marcado como PROVISORIO. Enviar o arquivo e rodar de novo, "
                      "ou liberar o mês assim.")
        else:
            motivo = (f"O arquivo {b['arquivo']} ({rotulo}) veio com layout diferente do esperado: "
                      f"{b['detalhe'].split(': ', 1)[-1]}. Bloqueado: {efeito}. O restante foi fechado e está "
                      "marcado como PROVISORIO. Conferir com quem gerou o arquivo ou ajustar o leitor.")
            if f == "orbe":
                motivo += (" O checkout inteiro ficou bloqueado: nenhum arquivo Orbe foi usado, porque calcular "
                           "com só parte deles daria comissões, notas e saldos errados.")
        out.append({"tipo": b["tipo"], "ref_origem": b["arquivo"], "valor": Decimal("0"), "motivo": motivo,
                    "quem_decide": config.QUEM_HELENA, "rastro": []})
    return out


def _reapontar_ponte(itens, origem):
    """2+ relatórios da Ponte: o rastro de cada operação aponta o e-mail de onde ela foi usada ('ponte@<e-mail>')."""
    for it in itens:
        it["rastro"] = [(f"ponte@{origem[r[1]]}", *r[1:]) if r[0] == "ponte" and r[1] in origem else r
                        for r in it["rastro"]]


def _carregar_cadastro(pasta):
    """Lê as condições comerciais. Pasta/arquivo ausente NÃO derruba o fechamento: segue só com a planilha, mas conta como
    bloqueio (fechamento PARCIAL, S53): pendência CADASTRO_AUSENTE e notas/comissões PROVISORIO. Cadastro malformado
    levanta CadastroInvalido (ValueError, mensagem legível). Devolve (condicoes, bloqueio|None)."""
    try:
        return cad.ler(pasta), None
    except cad.CadastroAusente:
        return [], {"fonte": "cadastro", "tipo": "CADASTRO_AUSENTE", "arquivo": cad.ARQ_CONDICOES,
                    "detalhe": f"cadastro de condições comerciais não encontrado em {pasta}"}


def _neutralizar_conciliacoes(lancs, pend, sem_ponte, bancos_ausentes):
    """Sem a Ponte (ou sem o outro banco) a conciliação de TED/PIX/transferência não pode ser feita: em vez de
    pendências enganosas ('não bate', 'em trânsito'), o lançamento fica com a classificação por regra e uma
    observação dizendo que a conciliação está bloqueada."""
    tipos = set()
    if sem_ponte:
        tipos |= {"TED_PONTE_NAO_CONCILIADO", "ACOMPANHAR_REMESSA_FUTURA"}
    if bancos_ausentes:
        tipos |= {"TRANSFERENCIA_EM_TRANSITO"}
    for l in lancs:
        if l["pendencia"] and l["pendencia"][0] in tipos:
            tipo = l["pendencia"][0]
            l["pendencia"] = None
            if tipo == "TRANSFERENCIA_EM_TRANSITO":
                l["observacao"] = "conciliação bloqueada: falta o extrato do outro banco"
            else:
                l["regra"] = l["regra"].split("; S22")[0]
                l["observacao"] = "conciliação bloqueada: e-mail da Ponte ausente"
                l["metodo"], l["confianca"] = "HUMANO", config.CONF_NAO_CONCILIADO
    return [p for p in pend if p["tipo"] not in tipos]


def executar(entrada=RAIZ, saida=RAIZ / "saida", investigar=True, cadastro=None):
    """`cadastro` = pasta do cadastro de condições comerciais (padrão: cadastro/ na raiz do projeto)."""
    condicoes, bloq_cadastro = _carregar_cadastro(CADASTRO_PADRAO if cadastro is None else cadastro)
    d = ler_tudo_parcial(entrada)
    ok, bloqueios = d["ok"], list(d["bloqueios"])
    if not ok:
        raise ValueError("Nenhum arquivo do mês pôde ser lido:\n" + "\n".join(
            f"- {config.ROTULO_FONTE.get(b['fonte'], b['fonte'])}: "
            + ("arquivo não encontrado" if b["tipo"] == "FONTE_AUSENTE" else b["detalhe"]) for b in bloqueios))
    if bloq_cadastro:
        bloqueios.append(bloq_cadastro)
    chk_ok = "orbe" in ok and "taxas" in ok
    rem_ok = "ponte" in ok
    lan_ok = "plano" in ok and ("aurora" in ok or "meridiano" in ok)
    parcial = bool(bloqueios)
    sem_taxas = "taxas" not in ok

    if "orbe" in ok:
        comp_mes, comp_txt = _competencia(d["orbe"])
    else:
        comp_mes, comp_txt = _competencia_alternativa(d)

    # checkout (precisa de Orbe + taxas)
    chk, com_chk, nf_chk, div_chk, pen_chk = [], [], [], [], []
    if chk_ok:
        chk = checkout.calcular(d["orbe"], d["contratos"], condicoes)
        com_chk = checkout.comissoes(chk, d["contratos"])
        nf_chk = checkout.notas(com_chk, comp_txt)
        div_chk = checkout.divergencias(chk, d["contratos"])
        pen_chk = checkout.pendencias(chk, com_chk, d["contratos"], condicoes) + checkout.pendencias_linha_duplicada(d["orbe_duplicadas"])

    # remessa (precisa do e-mail da Ponte; sem taxas não há divergência nem cadastro para conferir)
    rem, com_rem, nf_rem, div_rem, pen_rem = [], [], [], [], []
    if rem_ok:
        rem = remessa.calcular(d["ponte"], d["contratos"], comp_mes, condicoes)
        com_rem = remessa.comissoes(rem, d["contratos"])
        nf_rem = remessa.nota(rem, comp_txt)
        div_rem = remessa.divergencias(rem, d["contratos"])
        pen_rem = remessa.pendencias(rem, d["contratos"], d["meta_ponte"], nf_rem[0]["valor"] if nf_rem else None, condicoes)
        if sem_taxas:
            pen_rem = [p for p in pen_rem if p["tipo"] != "REMESSA_SEM_CONTRATO"]

    # extratos (precisam do plano de contas; cada banco é independente)
    lancs, pen_ext = [], []
    if lan_ok:
        lancs, pen_ext = extratos.classificar(d["aurora"], d["meridiano"], rem, d["plano"], d["meta_aurora"],
                                               sorted(checkout.nome_por_cnpj(d["contratos"]).values()))
        if parcial:
            pen_ext = _neutralizar_conciliacoes(lancs, pen_ext, not rem_ok,
                                                [b for b in ("aurora", "meridiano") if b not in ok])
        for l in lancs:
            # com 2+ versões do extrato, a linha aponta o arquivo de onde foi usada ('banco@arquivo')
            chave = f"{l['banco'].lower()}@{l['arquivo_origem']}" if l.get("arquivo_origem") else l["banco"].lower()
            l["rastro"] = [(chave, l["ref"], l["valor"], l["descricao"])]

    # ids legíveis
    pen_bloq = _pendencias_bloqueio(bloqueios)
    _numerar(com_chk, "COM-CHK"); _numerar(com_rem, "COM-REM")
    divs = _numerar(div_chk + div_rem, "DIV")
    notas = _numerar(nf_chk + nf_rem, "NF")
    _numerar(lancs, "LAN")
    pends = _numerar(pen_bloq + d["pend_versoes"] + pen_chk + pen_rem + pen_ext, "PEN")
    comissoes = com_chk + com_rem
    if d["origem_ponte"]:                      # 2+ relatórios da Ponte: cada operação aponta o seu e-mail
        _reapontar_ponte(comissoes + divs + notas + pends, d["origem_ponte"])

    _conferir_rastro(comissoes, lambda x: x["comissao"])
    _conferir_rastro(divs, lambda x: x["diferenca"])
    _conferir_rastro(notas, lambda x: x["valor"])
    _conferir_rastro(lancs, lambda x: x["valor"])
    _conferir_rastro(pends, lambda x: x["valor"])

    arquivos = dict(d["arquivos"])
    if rem_ok:
        arquivos["ponte"] = f"{d['arquivos']['ponte']}#{d['meta_ponte']['anexo']}"
    arquivos.update(d["rastro_arquivos"])
    status = config.STATUS_PROVISORIO if parcial else None   # completo: os CSVs ficam idênticos aos de sempre
    saidas.escrever(saida, "comissoes_por_lojista.csv", saidas.linhas_comissoes(comissoes), status)
    saidas.escrever(saida, "divergencias_taxa.csv", saidas.linhas_divergencias(divs))
    saidas.escrever(saida, "notas_a_emitir.csv", saidas.linhas_notas(notas), status)
    saidas.escrever(saida, "lancamentos_classificados.csv", saidas.linhas_lancamentos(lancs))
    saidas.escrever(saida, "pendencias.csv", saidas.linhas_pendencias(pends))
    com_valor = [p for p in pends if p["valor"] is not None]
    origem_orbe = {l["id"]: l["arquivo"] for l in d["orbe"]}
    saidas.escrever(saida, "rastro.csv", saidas.linhas_rastro(comissoes + divs + notas + com_valor + lancs, arquivos, origem_orbe))

    # o que ficou bloqueado, para o resumo e a tela (S53)
    efeitos = []
    for b in bloqueios:
        motivo = "falta" if b["tipo"] in ("FONTE_AUSENTE", "CADASTRO_AUSENTE") else "layout inesperado em"
        efeitos.append(f"{config.EFEITO_BLOQUEIO.get(b['fonte'], b['fonte'])} "
                       f"({motivo} {config.ROTULO_FONTE.get(b['fonte'], b['fonte'])})")
    r = {"competencia": comp_txt, "dados": d, "checkout": chk, "remessa": rem,
         "comissoes": comissoes, "divergencias": divs, "notas": notas, "lancamentos": lancs,
         "pendencias": pends, "saida": Path(saida), "investigacao": None, "investigacao_erro": None,
         "versoes": d["versoes"], "parcial": parcial, "bloqueios": bloqueios, "condicoes": condicoes, "cadastro_ausente": bool(bloq_cadastro),
         "bloqueado": {"checkout": not chk_ok, "remessa": not rem_ok,
                       "divergencias_remessa": not rem_ok or sem_taxas,
                       "AURORA": not (lan_ok and "aurora" in ok), "MERIDIANO": not (lan_ok and "meridiano" in ok)},
         "aviso_parcial": ("FECHAMENTO PARCIAL — bloqueado: " + "; ".join(efeitos)) if parcial else None}

    # dossiê de investigação (PLANO_IA_01 Fase 1): só LÊ o resultado, depois dos 6 CSVs gravados.
    # Um erro aqui não desfaz nem altera o fechamento; fica registrado e avisado.
    # Só roda com checkout e remessa disponíveis (ele cruza as duas linhas com a planilha de taxas).
    if investigar and chk_ok and rem_ok:
        try:
            antigas = ler_taxas_antigas(Path(entrada) / d["arquivos"]["taxas"])
            r["investigacao"] = investigacao.gerar(r, antigas)
            investigacao.escrever(r["investigacao"], saida)
        except Exception as e:  # noqa: BLE001
            r["investigacao_erro"] = f"{type(e).__name__}: {e}"
            print(f"AVISO: dossiê de investigação não gerado ({r['investigacao_erro']})", file=sys.stderr)
    return r


def resumo(r):
    c, dv, n = r["comissoes"], r["divergencias"], r["notas"]
    def tot(xs, k): return soma(x[k] for x in xs)
    chk = [x for x in c if x["linha_negocio"] == "CHECKOUT"]
    rem = [x for x in c if x["linha_negocio"] == "REMESSA"]
    linhas = [
        f"Fechamento competência {r['competencia']}  ->  {r['saida']}",
        f"  Comissão CHECKOUT : {fmt_br(tot(chk, 'comissao')):>16}  ({len(chk)} lojistas, {sum(x['qtd'] for x in chk)} transações)",
        f"  Comissão REMESSA  : {fmt_br(tot(rem, 'comissao')):>16}  ({len(rem)} lojistas, {sum(x['qtd'] for x in rem)} operações)",
    ]
    for ln in ("CHECKOUT", "REMESSA"):
        xs = [x for x in n if x["linha_negocio"] == ln]
        linhas.append(f"  Notas {ln:<9}   : {fmt_br(tot(xs, 'valor')):>16}  ({len(xs)} notas)")
    for ln in ("CHECKOUT", "REMESSA"):
        xs = [x for x in dv if x["linha_negocio"] == ln]
        linhas.append(f"  Divergências {ln:<9}: {fmt_br(tot(xs, 'diferenca')):>13}  ({len(xs)} linhas)")
    for b in ("AURORA", "MERIDIANO"):
        xs = [x for x in r["lancamentos"] if x["banco"] == b]
        reg = sum(1 for x in xs if x["metodo"] == "REGRA")
        linhas.append(f"  Lançamentos {b:<9} : {len(xs)} ({reg} por REGRA)")
    por_quem = Counter(p["quem_decide"] for p in r["pendencias"])
    linhas.append(f"  Pendências        : {len(r['pendencias'])}  " + ", ".join(f"{k}: {v}" for k, v in por_quem.items()))
    vers = [v["texto"] for v in r.get("versoes", {}).values() if len(v["arquivos"]) > 1]
    if vers:
        linhas.append("  Versões de arquivos (reenvios consolidados, sem duplicar):")
        linhas += [f"    {t}" for t in vers]
    if r.get("investigacao"):
        linhas.append(f"  Investigação      : {len(r['investigacao']['grupos'])} grupos de divergência  ->  "
                      "investigacao/dossie.md")
    if r.get("parcial"):
        linhas = _marcar_bloqueios(linhas, r)
    return "\n".join(linhas)


def _marcar_bloqueios(linhas, r):
    """Fechamento parcial (S53): aviso grande no topo e 'BLOQUEADO' nas linhas que não puderam ser calculadas."""
    b = r["bloqueado"]
    chaves = []                                  # (prefixo da linha do resumo, bloqueada?)
    for ln in ("CHECKOUT", "REMESSA"):
        chaves += [(f"  Comissão {ln}", b[ln.lower()]), (f"  Notas {ln}", b[ln.lower()])]
    chaves += [("  Divergências CHECKOUT", b["checkout"]), ("  Divergências REMESSA", b.get("divergencias_remessa", b["remessa"]))]
    chaves += [(f"  Lançamentos {k}", b[k]) for k in ("AURORA", "MERIDIANO")]
    out = []
    for l in linhas:
        bloqueada = any(bloq and l.startswith(k) for k, bloq in chaves)
        out.append(l.split(":")[0] + ": BLOQUEADO (sem os dados necessários)" if bloqueada else l)
    barra = "=" * 78
    topo = [barra, r["aviso_parcial"],
            "Notas e comissões saem com status=PROVISORIO. Cada bloqueio virou uma pendência (FONTE_AUSENTE /",
            "LAYOUT_INESPERADO) para Helena (Financeiro), que decide a liberação.", barra]
    return topo + out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fechamento mensal Tarvo (checkout + remessa + extratos)")
    ap.add_argument("--entrada", default=str(RAIZ), help="pasta com os arquivos de origem (default: raiz do projeto)")
    ap.add_argument("--saida", default=str(RAIZ / "saida"), help="pasta de saída (default: saida/)")
    ap.add_argument("--cadastro", default=str(CADASTRO_PADRAO),
                    help="pasta do cadastro de condições comerciais (default: cadastro/ na raiz do projeto)")
    ap.add_argument("--ia", action="store_true", help="gera hipóteses com IA em execucoes/cli_<data_hora>/")
    a = ap.parse_args(argv)
    try:
        r = executar(Path(a.entrada), Path(a.saida), cadastro=Path(a.cadastro))
    except (PermissionError, FileNotFoundError, ValueError) as e:
        sys.exit(f"ERRO: {e}")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(resumo(r))
    if a.ia:
        print(hipoteses_ia(r))


def hipoteses_ia(r, pasta_execucoes=RAIZ / "execucoes"):
    """--ia: hipóteses por grupo do dossiê, em arquivo fora de saida/. Nunca interrompe o fechamento."""
    if not r.get("investigacao"):
        return f"IA: dossiê não gerado ({r.get('investigacao_erro')}); nada a investigar."
    from . import ia
    ok, motivo = ia.disponivel()
    if not ok:
        return f"IA: {motivo} Seguindo sem hipóteses; o dossiê está em {r['saida'] / 'investigacao' / 'dossie.md'}."
    res = ia.investigar(r["investigacao"])
    pasta = Path(pasta_execucoes) / datetime.now().strftime("cli_%Y-%m-%d_%H%M%S")
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "investigacao_ia.json"
    destino.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    linhas = [f"IA ({res['modelo']}, prompt {res['versao_prompt']}):"]
    for g in res["grupos"]:
        linhas.append(f"  {g['id_grupo']} {g.get('lojista')}: " + (g["erro"] if g.get("erro") else
                      f"{len(g['hipoteses'])} hipótese(s), {g['hipoteses_descartadas']} descartada(s)"))
    linhas.append(f"  Gravado em {destino}")
    return "\n".join(linhas)


if __name__ == "__main__":
    main()
