"""Fila de trabalho: memória do mês sobre o que foi feito com cada pendência e cada grupo de divergência.

`meses/<AAAA-MM>/fila_log.csv` só cresce (nunca se edita nem se apaga linha):
    data_hora;usuario;chave;tipo_item;acao;status_novo;detalhe
Status atual de um item = `status_novo` da última linha com status preenchido; sem linhas = ABERTA.

Chave estável (igual em toda execução do mesmo mês):
    pendência  -> "PEN|<tipo>|<ref_origem>"
    divergência -> "DIV|<contraparte>|<cnpj>|<natureza>"     (um grupo = contraparte x lojista x natureza, como no dossiê)

Transições válidas: ABERTA -> EM_ACOMPANHAMENTO | BAIXADA | DECLINADA (só divergência);
EM_ACOMPANHAMENTO -> BAIXADA | ABERTA (REABERTA); BAIXADA | DECLINADA -> ABERTA (REABERTA).
Nada aqui altera valores do fechamento nem envia e-mail.
"""
import csv
import re
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import config
from .checkout import nome_por_cnpj
from .dinheiro import soma
from .extratos import _sem_acento

ARQ_LOG = "fila_log.csv"
COLUNAS_LOG = ["data_hora", "usuario", "chave", "tipo_item", "acao", "status_novo", "detalhe"]
ABERTA, EM_ACOMPANHAMENTO, BAIXADA, DECLINADA = config.STATUS_FILA

TRANSICOES = {
    ABERTA: {EM_ACOMPANHAMENTO, BAIXADA, DECLINADA},
    EM_ACOMPANHAMENTO: {BAIXADA, ABERTA},
    BAIXADA: {ABERTA},
    DECLINADA: {ABERTA},
}
# acao -> status que ela produz ("" = não muda o status)
STATUS_DA_ACAO = {"BAIXA": BAIXADA, "DECLINADA": DECLINADA, "REABERTA": ABERTA, "EMAIL_ENVIADO": EM_ACOMPANHAMENTO,
                  "SUGESTAO_IA": "", "EMAIL_PREPARADO": "", "COMENTARIO": ""}
# ações que descrevem o que a analista fez; a sugestão da IA não entra em ultima_acao (nem nos CSVs oficiais)
ACOES_DA_ANALISTA = ("EMAIL_PREPARADO", "EMAIL_ENVIADO", "BAIXA", "DECLINADA", "REABERTA", "COMENTARIO")
ACOES_COM_COMENTARIO = ("BAIXA", "DECLINADA", "REABERTA", "COMENTARIO")


class FilaInvalida(ValueError):
    """Registro recusado (ação, status, tipo ou transição inválidos). Mensagem em português."""


# ---------------------------------------------------------------- chaves
def chave_pendencia(p):
    return f"PEN|{p['tipo']}|{p['ref_origem']}"


def _contraparte(g):
    if g.get("contraparte"):
        return g["contraparte"]
    return "ORBE" if g.get("linha_negocio") == "CHECKOUT" else "PONTE"


def chave_divergencia(grupo):
    """`grupo` = grupo do dossiê (contraparte, cnpj, natureza) ou uma linha de divergência (linha_negocio, cnpj, natureza)."""
    return f"DIV|{_contraparte(grupo)}|{grupo['cnpj']}|{grupo['natureza']}"


# ---------------------------------------------------------------- log
def _caminho(pasta_mes):
    return Path(pasta_mes) / ARQ_LOG


def ler_log(pasta_mes):
    """Linhas do fila_log.csv (lista de dicts, em ordem). Pasta None ou arquivo ausente: lista vazia."""
    if pasta_mes is None:
        return []
    arq = _caminho(pasta_mes)
    if not arq.exists():
        return []
    with open(arq, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def status_atual(log):
    """{chave: {status, ultima_acao, data_ultima_acao, responsavel, comentario}} só das chaves que têm linhas.
    status = status_novo da última linha com status preenchido. ultima_acao/data/responsavel = última ação da
    analista (a sugestão da IA não conta). comentario = detalhe da última baixa/declínio/reabertura/comentário."""
    out = OrderedDict()
    for l in log:
        s = out.setdefault(l["chave"], {"status": ABERTA, "ultima_acao": "", "data_ultima_acao": "",
                                        "responsavel": "", "comentario": ""})
        if l.get("status_novo"):
            s["status"] = l["status_novo"]
        if l["acao"] in ACOES_DA_ANALISTA:
            s["ultima_acao"], s["data_ultima_acao"], s["responsavel"] = l["acao"], l["data_hora"], l["usuario"]
        if l["acao"] in ACOES_COM_COMENTARIO:
            s["comentario"] = l.get("detalhe") or ""
    return out


def estado(status, chave):
    """Estado de uma chave no mapa de `status_atual`; sem linhas = ABERTA e vazio."""
    return status.get(chave) or {"status": ABERTA, "ultima_acao": "", "data_ultima_acao": "", "responsavel": "",
                                 "comentario": ""}


def registrar(pasta_mes, usuario, chave, tipo_item, acao, status_novo="", detalhe="", agora=None):
    """Acrescenta UMA linha ao fila_log.csv do mês (cria a pasta e o arquivo com cabeçalho se preciso).
    Valida acao, tipo_item, status e a transição a partir do status atual do item. `status_novo` vazio assume o status
    que a ação produz (BAIXA -> BAIXADA, DECLINADA -> DECLINADA, REABERTA -> ABERTA, EMAIL_ENVIADO -> EM_ACOMPANHAMENTO;
    SUGESTAO_IA, EMAIL_PREPARADO e COMENTARIO não mudam o status). Devolve a linha gravada (dict)."""
    usuario = (usuario or "").strip()
    if not usuario:
        raise FilaInvalida("Informe quem está registrando a ação (usuario).")
    chave = (chave or "").strip()
    if not chave.startswith(("PEN|", "DIV|")):
        raise FilaInvalida(f"Chave '{chave}' inválida (esperado PEN|... ou DIV|...).")
    if tipo_item not in config.TIPOS_ITEM_FILA:
        raise FilaInvalida(f"tipo_item '{tipo_item}' inválido. Use {' ou '.join(config.TIPOS_ITEM_FILA)}.")
    if (tipo_item == "PENDENCIA") != chave.startswith("PEN|"):
        raise FilaInvalida(f"A chave {chave} não corresponde ao tipo_item {tipo_item}.")
    if acao not in config.ACOES_FILA:
        raise FilaInvalida(f"Ação '{acao}' inválida. Ações: {', '.join(config.ACOES_FILA)}.")
    status_novo = (status_novo or "").strip()
    if status_novo and status_novo not in config.STATUS_FILA:
        raise FilaInvalida(f"Status '{status_novo}' inválido. Status: {', '.join(config.STATUS_FILA)}.")
    atual = estado(status_atual(ler_log(pasta_mes)), chave)["status"]
    esperado = STATUS_DA_ACAO[acao]
    if status_novo and status_novo != (esperado or atual):
        raise FilaInvalida(f"A ação {acao} não leva o item ao status {status_novo}.")
    novo = status_novo or esperado
    if acao == "DECLINADA" and tipo_item != "DIVERGENCIA":
        raise FilaInvalida("Só divergência pode ser declinada; pendência se encerra com baixa.")
    if novo and not (novo == atual == EM_ACOMPANHAMENTO) and novo not in TRANSICOES[atual]:
        raise FilaInvalida(f"Transição inválida: {atual} -> {novo}"
                           + (f" (o item está {atual.lower().replace('_', ' ')}; reabra antes)" if atual in config.STATUS_ENCERRADOS
                              and novo != ABERTA else "") + ".")
    linha = {"data_hora": (agora or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"), "usuario": usuario, "chave": chave,
             "tipo_item": tipo_item, "acao": acao, "status_novo": novo, "detalhe": detalhe or ""}
    arq = _caminho(pasta_mes)
    arq.parent.mkdir(parents=True, exist_ok=True)
    novo_arquivo = not arq.exists() or arq.stat().st_size == 0
    with open(arq, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        if novo_arquivo:
            w.writerow(COLUNAS_LOG)
        w.writerow([linha[c] for c in COLUNAS_LOG])
    return linha


def historico(log, chave):
    """Linhas do log de um item, em ordem."""
    return [l for l in log if l["chave"] == chave]


# ---------------------------------------------------------------- itens para a tela
def grupos_divergencia(divergencias):
    """Agrupa as linhas de divergência (como saem do fechamento) em grupos contraparte x CNPJ x natureza."""
    grupos = OrderedDict()
    for d in divergencias:
        grupos.setdefault((_contraparte(d), d["cnpj"], d["natureza"]), []).append(d)
    return grupos


def _cnpj_pelo_nome(descricao, nomes):
    """CNPJ do lojista cujo nome COMEÇA com o texto de nome da descrição do extrato (mesmo critério da S22 em
    extratos._pagador); só se for exatamente UM lojista, senão ''. Serve só para sugerir contato, nunca para cálculo."""
    resto = re.sub(r"^(PIX RECEB|DEVOLUCAO PIX)\s*-?\s*", "", descricao or "", flags=re.IGNORECASE).strip()
    if not resto:
        return ""
    r = _sem_acento(resto)       # o extrato trunca (começo do nome) ou acrescenta ("INTERC"): vale o início exato nos dois sentidos
    achados = {c for c, n in nomes.items() if _sem_acento(n).startswith(r) or r.startswith(_sem_acento(n))}
    return next(iter(achados)) if len(achados) == 1 else ""


# pendência que repete um grupo de divergência -> (contraparte, natureza)
_PEN_DO_GRUPO = {"DIVERGENCIA_TAXA_CHECKOUT": ("ORBE", config.NATUREZA_CONTRATO),
                 "DEVOLUCAO_LOJISTA_ISENCAO": ("ORBE", config.NATUREZA_ISENCAO),
                 "DIVERGENCIA_SPREAD_REMESSA": ("PONTE", config.NATUREZA_CONTRATO)}


def chaves_vinculadas(chave, itens):
    """[chave, + a chave do item vinculado, se houver]: ações e sugestão valem para o par (mesmo problema em dois itens)."""
    por = {i["chave"]: i for i in itens}
    outra = (por.get(chave) or {}).get("vinculado_a")
    return [chave] + ([outra] if outra else [])


def itens(resultado, log=None):
    """Lista unificada de itens da fila (pendências e grupos de divergência) para a tela.
    Cada item: chave, tipo_item (PENDENCIA|DIVERGENCIA), tipo, titulo, valor (Decimal|None; divergência = valor a devolver do dossiê, senão a soma), valor_formula (str da soma de diferenca; só divergência), status, ultima_acao,
    data_ultima_acao, responsavel, comentario, destinos, objetivo, lojista, cnpj, contraparte, natureza, qtd,
    ids (id_saida das linhas), ref_origem, motivo, quem_decide. Pendências na ordem do CSV; depois os grupos de
    divergência por valor decrescente."""
    st = status_atual(log or [])
    nomes = nome_por_cnpj(resultado["dados"]["contratos"]) if resultado.get("dados") else {}
    lanc = {l["ref"]: l for l in resultado.get("lancamentos", [])}
    divs_res = resultado["divergencias"]
    out = []
    for p in resultado["pendencias"]:
        chave = chave_pendencia(p)
        acao = config.acao_do_tipo(p["tipo"])
        cnpj, vinc = "", None
        if p["tipo"] in ("DEVOLUCAO_REPASSE", "ACOMPANHAR_REMESSA_FUTURA") and p["ref_origem"] in lanc:
            cnpj = _cnpj_pelo_nome(lanc[p["ref_origem"]]["descricao"], nomes)
        elif p["tipo"] in _PEN_DO_GRUPO:
            contra, nat = _PEN_DO_GRUPO[p["tipo"]]
            tipo_ref, _, ref = p["ref_origem"].partition(" ")
            for d in divs_res:
                if _contraparte(d) == contra and d["natureza"] == nat and (
                        d["ec_orbe"] == ref if tipo_ref == "EC" else d["cnpj"] == ref):
                    cnpj, vinc = d["cnpj"], chave_divergencia(d)
                    break
        out.append({"chave": chave, "tipo_item": "PENDENCIA", "tipo": p["tipo"],
                    "titulo": f"{acao['rotulo']} — {p['ref_origem']}", "valor": p["valor"], **estado(st, chave),
                    "destinos": list(acao["destinos"]), "objetivo": acao["objetivo"], "lojista": nomes.get(cnpj, ""), "cnpj": cnpj,
                    "vinculado_a": vinc, "contraparte": "", "natureza": "", "qtd": 1, "ids": [p["id"]], "ref_origem": p["ref_origem"],
                    "motivo": p["motivo"], "quem_decide": p["quem_decide"]})
    divs = []
    do_dossie = {chave_divergencia(g): g for g in ((resultado.get("investigacao") or {}).get("grupos") or [])}
    for (contraparte, cnpj, natureza), ls in grupos_divergencia(resultado["divergencias"]).items():
        g = {"contraparte": contraparte, "cnpj": cnpj, "natureza": natureza}
        chave = chave_divergencia(g)
        tipo = config.tipo_divergencia(natureza, ls[0]["linha_negocio"])
        acao = config.acao_do_tipo(tipo)
        formula = soma(l["diferenca"] for l in ls)
        g_dossie = do_dossie.get(chave)
        total = Decimal(g_dossie["valor_devolver_lojista_brl"]) if g_dossie else formula   # valor da AÇÃO (S51)
        divs.append({"chave": chave, "tipo_item": "DIVERGENCIA", "tipo": tipo,
                     "titulo": f"{acao['rotulo']} — {ls[0]['lojista']} ({len(ls)} {'linha' if len(ls) == 1 else 'linhas'})",
                     "valor": total, "valor_formula": str(formula), **estado(st, chave), "destinos": list(acao["destinos"]),
                     "objetivo": acao["objetivo"], "lojista": ls[0]["lojista"], "cnpj": cnpj,
                     "vinculado_a": None, "contraparte": contraparte, "natureza": natureza, "qtd": len(ls), "ids": [l["id"] for l in ls],
                     "ref_origem": "", "motivo": "", "quem_decide": config.QUEM_HELENA})
    divs.sort(key=lambda i: (-abs(i["valor"]), i["chave"]))
    por = {i["chave"]: i for i in divs}
    for i in out:                                   # o grupo aponta de volta para a pendência que o repete
        if i["vinculado_a"] in por:
            por[i["vinculado_a"]]["vinculado_a"] = i["chave"]
    return out + divs
