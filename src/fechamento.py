"""CLI do fechamento mensal.

Uso:  python -m src.fechamento --entrada <pasta com os arquivos do mês> --saida <pasta> [--ia]
Defaults: entrada = raiz do projeto; saida = <raiz>/saida.
--ia: além do dossiê, pede hipóteses à IA (src/ia.py) e grava em execucoes/cli_<data_hora>/investigacao_ia.json
      (fora de saida/, que fica determinística). Sem chave/biblioteca: avisa e segue.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import checkout, extratos, investigacao, remessa, saidas
from .dinheiro import soma, fmt_br
from .leitores import descobrir_arquivos, ler_taxas_antigas, ler_tudo

RAIZ = Path(__file__).resolve().parent.parent


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


def executar(entrada=RAIZ, saida=RAIZ / "saida", investigar=True):
    d = ler_tudo(entrada)
    comp_mes, comp_txt = _competencia(d["orbe"])

    # checkout
    chk = checkout.calcular(d["orbe"], d["contratos"])
    com_chk = checkout.comissoes(chk, d["contratos"])
    nf_chk = checkout.notas(com_chk, comp_txt)
    div_chk = checkout.divergencias(chk, d["contratos"])
    pen_chk = checkout.pendencias(chk, com_chk, d["contratos"]) + checkout.pendencias_linha_duplicada(d["orbe_duplicadas"])

    # remessa
    rem = remessa.calcular(d["ponte"], d["contratos"], comp_mes)
    com_rem = remessa.comissoes(rem, d["contratos"])
    nf_rem = remessa.nota(rem, comp_txt)
    div_rem = remessa.divergencias(rem, d["contratos"])
    pen_rem = remessa.pendencias(rem, d["contratos"], d["meta_ponte"], nf_rem[0]["valor"] if nf_rem else None)

    # extratos
    lancs, pen_ext = extratos.classificar(d["aurora"], d["meridiano"], rem, d["plano"], d["meta_aurora"],
                                           sorted(checkout.nome_por_cnpj(d["contratos"]).values()))
    for l in lancs:
        l["rastro"] = [(l["banco"].lower(), l["ref"], l["valor"], l["descricao"])]

    # ids legíveis
    _numerar(com_chk, "COM-CHK"); _numerar(com_rem, "COM-REM")
    divs = _numerar(div_chk + div_rem, "DIV")
    notas = _numerar(nf_chk + nf_rem, "NF")
    _numerar(lancs, "LAN")
    pends = _numerar(pen_chk + pen_rem + pen_ext, "PEN")
    comissoes = com_chk + com_rem

    _conferir_rastro(comissoes, lambda x: x["comissao"])
    _conferir_rastro(divs, lambda x: x["diferenca"])
    _conferir_rastro(notas, lambda x: x["valor"])
    _conferir_rastro(lancs, lambda x: x["valor"])
    _conferir_rastro(pends, lambda x: x["valor"])

    arquivos = dict(d["arquivos"])
    arquivos["ponte"] = f"{d['arquivos']['ponte']}#{d['meta_ponte']['anexo']}"
    saidas.escrever(saida, "comissoes_por_lojista.csv", saidas.linhas_comissoes(comissoes))
    saidas.escrever(saida, "divergencias_taxa.csv", saidas.linhas_divergencias(divs))
    saidas.escrever(saida, "notas_a_emitir.csv", saidas.linhas_notas(notas))
    saidas.escrever(saida, "lancamentos_classificados.csv", saidas.linhas_lancamentos(lancs))
    saidas.escrever(saida, "pendencias.csv", saidas.linhas_pendencias(pends))
    com_valor = [p for p in pends if p["valor"] is not None]
    origem_orbe = {l["id"]: l["arquivo"] for l in d["orbe"]}
    saidas.escrever(saida, "rastro.csv", saidas.linhas_rastro(comissoes + divs + notas + com_valor + lancs, arquivos, origem_orbe))

    r = {"competencia": comp_txt, "dados": d, "checkout": chk, "remessa": rem,
         "comissoes": comissoes, "divergencias": divs, "notas": notas, "lancamentos": lancs,
         "pendencias": pends, "saida": Path(saida), "investigacao": None, "investigacao_erro": None}

    # dossiê de investigação (PLANO_IA_01 Fase 1): só LÊ o resultado, depois dos 6 CSVs gravados.
    # Um erro aqui não desfaz nem altera o fechamento; fica registrado e avisado.
    if investigar:
        try:
            antigas = ler_taxas_antigas(descobrir_arquivos(entrada)["taxas"])
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
    if r.get("investigacao"):
        linhas.append(f"  Investigação      : {len(r['investigacao']['grupos'])} grupos de divergência  ->  "
                      "investigacao/dossie.md")
    return "\n".join(linhas)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fechamento mensal Tarvo (checkout + remessa + extratos)")
    ap.add_argument("--entrada", default=str(RAIZ), help="pasta com os arquivos de origem (default: raiz do projeto)")
    ap.add_argument("--saida", default=str(RAIZ / "saida"), help="pasta de saída (default: saida/)")
    ap.add_argument("--ia", action="store_true", help="gera hipóteses com IA em execucoes/cli_<data_hora>/")
    a = ap.parse_args(argv)
    try:
        r = executar(Path(a.entrada), Path(a.saida))
    except PermissionError as e:
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
