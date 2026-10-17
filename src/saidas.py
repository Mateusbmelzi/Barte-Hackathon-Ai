"""Escrita dos 6 CSVs no formato do edital: separador ';', ponto decimal, datas AAAA-MM-DD,
CNPJ 14 dígitos, colunas obrigatórias primeiro (extras ao final), UTF-8."""
import csv
from pathlib import Path

from . import config
from .dinheiro import fmt, fmt_pct

COLUNAS = {
    "comissoes_por_lojista.csv": ["id_saida", "cnpj", "lojista", "linha_negocio", "comissao_brl",
                                  "qtd_transacoes", "ec_orbe", "comissao_mdr_brl", "comissao_antecipacao_brl", "regra"],
    "divergencias_taxa.csv": ["id_saida", "cnpj", "linha_negocio", "ref_origem", "taxa_contratada_pct",
                              "taxa_aplicada_pct", "diferenca_brl", "lojista", "ec_orbe", "tipo_lancamento",
                              "data", "valor_base", "regra", "natureza", "cobrar_parceiro"],
    "notas_a_emitir.csv": ["id_saida", "tomador_cnpj", "tomador", "linha_negocio", "valor_brl", "discriminacao",
                           "qtd_linhas_origem"],
    "lancamentos_classificados.csv": ["id_saida", "banco", "ref_origem", "data", "descricao", "valor",
                                      "conta_codigo", "metodo", "confianca", "conta_descricao", "regra", "observacao"],
    "pendencias.csv": ["id_saida", "tipo", "ref_origem", "valor_brl", "motivo", "quem_decide"],
    "rastro.csv": ["id_saida", "arquivo_origem", "ref_origem", "valor", "detalhe"],
}


def _data(d):
    return d.isoformat() if d else ""


def _m(v):
    return "" if v is None else fmt(v)


def linhas_comissoes(itens):
    return [[c["id"], c["cnpj"], c["lojista"], c["linha_negocio"], fmt(c["comissao"]), c["qtd"], c["ec_orbe"],
             _m(c.get("comissao_mdr")), _m(c.get("comissao_antecipacao")), c["regra"]] for c in itens]


def linhas_divergencias(itens):
    return [[d["id"], d["cnpj"], d["linha_negocio"], d["ref_origem"], fmt_pct(d["contratada_pct"]),
             fmt_pct(d["aplicada_pct"]), fmt(d["diferenca"]), d["lojista"], d["ec_orbe"], d["tipo_lancamento"],
             _data(d["data"]), str(d["valor_base"]), d["regra"], d["natureza"],
             config.COBRAR_PARCEIRO[d["natureza"]]] for d in itens]


def linhas_notas(itens):
    return [[n["id"], n["tomador_cnpj"], n["tomador"], n["linha_negocio"], fmt(n["valor"]), n["discriminacao"],
             len(n["rastro"])] for n in itens]


def linhas_lancamentos(itens):
    return [[l["id"], l["banco"], l["ref"], _data(l["data"]), l["descricao"], fmt(l["valor"]), l["conta"],
             l["metodo"], f"{l['confianca']:.2f}", l["conta_descricao"], l["regra"], l["observacao"]] for l in itens]


def linhas_pendencias(itens):
    return [[p["id"], p["tipo"], p["ref_origem"], _m(p["valor"]), p["motivo"], p["quem_decide"]] for p in itens]


def linhas_rastro(itens_com_rastro, arquivos, origem_orbe=None):
    """origem_orbe: {id_transacao: nome do arquivo Orbe}. Chave 'orbe' usa esse mapa (cada transação aponta
    o seu arquivo); 'orbe@<arquivo>' aponta direto o arquivo (linha repetida em outro arquivo)."""
    out = []
    for it in itens_com_rastro:
        for chave, ref, valor, detalhe in it["rastro"]:
            if chave.startswith("orbe@"):
                arq = chave[5:]
            elif chave == "orbe" and origem_orbe and ref in origem_orbe:
                arq = origem_orbe[ref]
            else:
                arq = arquivos[chave]
            out.append([it["id"], arq, ref, fmt(valor), detalhe])
    return out


def escrever(pasta, nome, linhas, status=None):
    """status=None: arquivo no formato do edital (completo). status='PROVISORIO': fechamento parcial, ganha a
    coluna extra 'status' ao final (S53); no fechamento completo nada muda, byte a byte."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    try:
        with open(pasta / nome, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";", lineterminator="\n")
            if status is None:
                w.writerow(COLUNAS[nome])
                w.writerows(linhas)
            else:
                w.writerow(COLUNAS[nome] + ["status"])
                w.writerows(l + [status] for l in linhas)
    except PermissionError as e:
        raise PermissionError(f"Feche o arquivo {nome} no Excel (ou em outro programa) e rode de novo.") from e
