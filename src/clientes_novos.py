"""Clientes novos: lojista que aparece nos arquivos do mês e ainda não está no registro de clientes conhecidos.

Registro: `cadastro/clientes_conhecidos.csv` (UTF-8, `;`), semeado com os lojistas da planilha vigente + o
de-para/bloqueio do cadastro (a Atlas entra como CONTRATO_PENDENTE: sem contrato). Cresce quando um cliente é
adicionado (`adicionar_novo`) e muda de status (`registrar_contrato`, `marcar`).

    cnpj;ec_orbe;nome;origem;primeira_vez_visto;status;contrato_arquivo;atualizado_em;atualizado_por

Status: CONTRATO_PENDENTE -> CONTRATO_ANALISADO (contrato lido pela IA) -> CONFIRMADO (analista aprovou).

A detecção (`detectar`) só LÊ: é metadado do resultado/tela e não altera nenhum dos 6 CSVs oficiais. Quem grava
o cliente novo no registro é o servidor (`adicionar_novo`).
"""
from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import cadastro as cad, config
from .dinheiro import soma

ARQ_CLIENTES = "clientes_conhecidos.csv"
PASTA_CONTRATOS = "contratos"
COLUNAS = ["cnpj", "ec_orbe", "nome", "origem", "primeira_vez_visto", "status", "contrato_arquivo",
           "atualizado_em", "atualizado_por"]
ORIGENS = ["ORBE", "PONTE"]


class ClienteInvalido(ValueError):
    """Dado inválido ao mexer no registro de clientes (mensagem em português)."""


def _digitos(t) -> str:
    return re.sub(r"\D", "", str(t or ""))


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- arquivo
def caminho(pasta) -> Path:
    return Path(pasta) / ARQ_CLIENTES


def ler(pasta) -> list[dict]:
    """Registro de clientes (lista de dicts com COLUNAS). Arquivo ausente -> lista vazia."""
    arq = caminho(pasta)
    if not arq.exists():
        return []
    with open(arq, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    return [{c: (l.get(c) or "").strip() for c in COLUNAS} for l in linhas]


def _gravar(pasta, linhas) -> None:
    arq = caminho(pasta)
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(COLUNAS)
        for l in linhas:
            w.writerow([l.get(c, "") for c in COLUNAS])
    os.replace(tmp, arq)


def _casa(l, chave) -> bool:
    """`chave` = CNPJ (com ou sem máscara) ou, para cliente sem CNPJ conhecido, o EC Orbe."""
    d = _digitos(chave)
    return bool(d) and (l["cnpj"] == d or (not l["cnpj"] and l["ec_orbe"] == d))


def _achar(linhas, chave):
    for l in linhas:
        if _casa(l, chave):
            return l
    raise ClienteInvalido(f"Cliente {chave} não está no registro de clientes conhecidos.")


def _validar_status(status):
    if status not in config.STATUS_CLIENTE:
        raise ClienteInvalido(f"Status '{status}' inválido. Use: {', '.join(config.STATUS_CLIENTE)}.")


def adicionar_novo(pasta, cliente: dict, usuario: str = "") -> dict:
    """Inclui o cliente no registro (status padrão CONTRATO_PENDENTE). Já existente: devolve a linha atual."""
    cnpj, ec = _digitos(cliente.get("cnpj")), _digitos(cliente.get("ec_orbe"))
    if not (cnpj or ec):
        raise ClienteInvalido("Informe o CNPJ ou o EC Orbe do cliente.")
    if cnpj and len(cnpj) != 14:
        raise ClienteInvalido(f"CNPJ '{cnpj}' deve ter 14 dígitos.")
    origem = (cliente.get("origem") or ("ORBE" if ec else "PONTE")).upper()
    if origem not in ORIGENS:
        raise ClienteInvalido("Origem deve ser ORBE ou PONTE.")
    status = cliente.get("status") or "CONTRATO_PENDENTE"
    _validar_status(status)
    linhas = ler(pasta)
    for l in linhas:
        if (cnpj and l["cnpj"] == cnpj) or (ec and l["ec_orbe"] == ec):
            return l
    nova = {"cnpj": cnpj, "ec_orbe": ec, "nome": (cliente.get("nome") or "").strip(), "origem": origem,
            "primeira_vez_visto": cliente.get("primeira_vez_visto") or datetime.now().strftime("%Y-%m"),
            "status": status, "contrato_arquivo": cliente.get("contrato_arquivo") or "",
            "atualizado_em": _agora(), "atualizado_por": (usuario or "").strip()}
    _gravar(pasta, linhas + [nova])
    return nova


def marcar(pasta, cnpj, status, usuario: str = "") -> dict:
    """Muda o status do cliente (CONTRATO_PENDENTE | CONTRATO_ANALISADO | CONFIRMADO)."""
    _validar_status(status)
    linhas = ler(pasta)
    l = _achar(linhas, cnpj)
    l.update(status=status, atualizado_em=_agora(), atualizado_por=(usuario or "").strip())
    _gravar(pasta, linhas)
    return l


def registrar_contrato(pasta, cnpj, arquivo, usuario: str = "") -> dict:
    """Guarda o nome do arquivo do contrato e marca o cliente como CONTRATO_ANALISADO."""
    if not (arquivo or "").strip():
        raise ClienteInvalido("Informe o arquivo do contrato.")
    linhas = ler(pasta)
    l = _achar(linhas, cnpj)
    l.update(contrato_arquivo=arquivo.strip(), status="CONTRATO_ANALISADO", atualizado_em=_agora(),
             atualizado_por=(usuario or "").strip())
    _gravar(pasta, linhas)
    return l


def guardar_contrato(pasta, cnpj, nome_arquivo: str, conteudo: bytes) -> str:
    """Copia o upload para `<pasta>/contratos/<cnpj>/<arquivo>` sem sobrescrever (_v2, _v3... se repetido).
    Devolve o nome do arquivo gravado (relativo à pasta do cliente)."""
    chave = _digitos(cnpj)
    if not chave:
        raise ClienteInvalido("Informe o CNPJ (ou EC) do cliente para guardar o contrato.")
    base = re.sub(r"[^\w.\- ]", "_", Path(nome_arquivo or "contrato").name).strip() or "contrato"
    destino_dir = Path(pasta) / PASTA_CONTRATOS / chave
    destino_dir.mkdir(parents=True, exist_ok=True)
    p = Path(base)
    alvo, n = destino_dir / base, 1
    while alvo.exists():
        n += 1
        alvo = destino_dir / f"{p.stem}_v{n}{p.suffix}"
    alvo.write_bytes(conteudo)
    return alvo.name


# ---------------------------------------------------------------- detecção
def _cnpj_do_ec(ec, contratos, condicoes) -> str:
    """CNPJ do EC Orbe: planilha vigente, senão de-para do cadastro, senão bloqueio (Atlas)."""
    for c in contratos:
        if not c.get("riscado") and c.get("ec") == ec:
            return c["cnpj"]
    cnpj = cad.cnpj_do_ec(condicoes, ec, None)
    if cnpj:
        return cnpj
    b = cad.bloqueio(condicoes, ec)
    return (b or {}).get("cnpj") or ""


def _dinheiro(v) -> str:
    return f"{Decimal(v).quantize(Decimal('0.01'))}"


def _conhecido(registro, cnpj, ec):
    for l in registro:
        if (cnpj and l["cnpj"] == cnpj) or (ec and l["ec_orbe"] == ec):
            return l
    return None


def detectar(resultado_dados: dict, cadastro_pasta) -> list[dict]:
    """Campos de valor/quantidade de cada cliente: `qtd_transacoes` = todas as linhas do mês (Orbe: vendas, estornos,
    antecipações...; Ponte: operações); `qtd_vendas` e `valor_bruto_vendas` = só lançamentos VENDA da Orbe (na Ponte, o
    valor das operações em R$); `valor_bruto` = o mesmo que `valor_bruto_vendas` (mantido por compatibilidade);
    `valor_bruto_antecipacoes` = soma do bruto dos lançamentos ANTECIPACAO. Valores como texto com 2 casas ("135428.90").

    Clientes que aparecem nos arquivos do mês e precisam de atenção: os que NÃO estão em
    `clientes_conhecidos.csv` (status CONTRATO_PENDENTE) e os conhecidos ainda não CONFIRMADO (ex.: Atlas, sem
    contrato). `resultado_dados` = `r["dados"]` do fechamento. Sem o registro (arquivo ausente) não há base
    de comparação e devolve lista vazia. Só lê."""
    registro = ler(cadastro_pasta)
    if not registro:
        return []
    try:
        condicoes = cad.ler(cadastro_pasta)
    except (cad.CadastroAusente, cad.CadastroInvalido):
        condicoes = []
    contratos = resultado_dados.get("contratos") or []
    achados: dict[str, dict] = {}

    def somar(chave, cnpj, ec, nome, origem, qtd, valor, qtd_vendas=None, antecipacoes=Decimal("0")):
        a = achados.setdefault(chave, {"cnpj": cnpj, "ec_orbe": ec, "nome": nome, "origem": origem,
                                       "qtd_transacoes": 0, "_valor": Decimal("0"), "qtd_vendas": 0, "_antec": Decimal("0")})
        if cnpj and not a["cnpj"]:
            a["cnpj"] = cnpj
        if ec and not a["ec_orbe"]:
            a["ec_orbe"] = ec
        if origem == "ORBE":
            a["origem"] = "ORBE"
        a["qtd_transacoes"] += qtd
        a["_valor"] += valor
        a["qtd_vendas"] += qtd if qtd_vendas is None else qtd_vendas
        a["_antec"] += antecipacoes

    por_ec: dict[str, list] = {}
    for l in resultado_dados.get("orbe") or []:
        por_ec.setdefault(l["ec"], []).append(l)
    for ec, ls in por_ec.items():
        cnpj = _cnpj_do_ec(ec, contratos, condicoes)
        valor = soma(l["bruto"] for l in ls if l["tipo"] == "VENDA")
        antec = soma(l["bruto"] for l in ls if l["tipo"] == "ANTECIPACAO")
        somar(cnpj or f"EC:{ec}", cnpj, ec, ls[0].get("nome") or "", "ORBE", len(ls), valor,
              qtd_vendas=sum(1 for l in ls if l["tipo"] == "VENDA"), antecipacoes=antec)
    for o in resultado_dados.get("ponte") or []:
        cnpj = _digitos(o.get("cnpj"))
        if cnpj:
            somar(cnpj, cnpj, "", o.get("cliente") or "", "PONTE", 1, Decimal(o.get("valor_brl") or 0))

    saida = []
    for a in achados.values():
        cnpj, ec = a["cnpj"], a["ec_orbe"]
        reg = _conhecido(registro, cnpj, ec)
        if reg is not None and reg["status"] == "CONFIRMADO":
            continue
        if reg is None:
            status = "CONTRATO_PENDENTE"
            motivo = ("Cliente novo: aparece nos arquivos do mês e ainda não consta do registro de clientes. "
                      "Pedir o contrato para extrair as taxas e as regras negociadas.")
        else:
            status = reg["status"]
            motivo = ("Cliente sem contrato analisado: enviar o contrato para a IA extrair as taxas e as regras."
                      if status == "CONTRATO_PENDENTE"
                      else "Contrato analisado, aguardando confirmação: revisar a extração e confirmar.")
        saida.append({"cnpj": cnpj, "ec_orbe": ec or (reg or {}).get("ec_orbe", ""),
                      "nome": a["nome"] or (reg or {}).get("nome", ""), "origem": a["origem"],
                      "qtd_transacoes": a["qtd_transacoes"], "valor_bruto": _dinheiro(a["_valor"]),
                      "qtd_vendas": a["qtd_vendas"], "valor_bruto_vendas": _dinheiro(a["_valor"]),
                      "valor_bruto_antecipacoes": _dinheiro(a["_antec"]),
                      "motivo": motivo, "status": status})
    return sorted(saida, key=lambda x: (x["status"], x["nome"].lower()))


# ---------------------------------------------------------------- contratos do cadastro como base
def contratos_do_cadastro(contratos, condicoes) -> list[dict]:
    """Linhas de planilha SINTÉTICAS para lojista que tem TAXA_ESPECIAL de checkout no cadastro (vinda de um
    contrato) mas nenhuma linha na planilha vigente: a taxa do cadastro vira a base do cálculo. Faixas sem taxa
    no cadastro ficam sem taxa (a transação sai como SEM_TAXA, nunca por chute). Nada muda para quem tem linha
    na planilha. Bloqueio de faturamento do cadastro continua valendo (a Atlas segue bloqueada pelo C005)."""
    ativos = [c for c in contratos if not c.get("riscado")]
    cnpjs = {c["cnpj"] for c in ativos}
    ecs = {c["ec"] for c in ativos if c.get("ec")}
    novos, vistos = [], set()
    for c in condicoes:
        if c["tipo"] != "TAXA_ESPECIAL" or c["linha_negocio"] == "REMESSA" or c["campo"] == cad.FAIXA_REMESSA:
            continue
        cnpj = c["cnpj"]
        if not cnpj or cnpj in cnpjs or cnpj in vistos:
            continue
        ec = c["ec_orbe"] or next((o["ec_orbe"] for o in condicoes if o["cnpj"] == cnpj and o["ec_orbe"]), "")
        if ec and ec in ecs:
            continue
        vistos.add(cnpj)
        novos.append({"linha": "cadastro", "lojista": c["lojista"] or cnpj, "cnpj": cnpj, "ec": ec or None,
                      "taxas": {}, "spread": None, "spread_bruto": None, "vigencia_texto": "contrato (cadastro)",
                      "inicio": None, "fim": None, "vigencia_ok": True, "obs": "base = taxas do contrato no cadastro",
                      "riscado": False, "sintetico": True})
    return list(contratos) + novos
