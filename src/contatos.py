"""Contatos (quem receber e-mail sobre uma pendência/divergência): cadastro/contatos.csv.

    contatos.csv            id_contato;papel;cnpj;nome;email;observacao
    contatos_removidos.csv  mesmas colunas + removido_em;removido_por     (remover MOVE para cá, não apaga)

Papéis (config.PAPEIS_CONTATO): LOJISTA (um por CNPJ), ORBE, PONTE, COMERCIAL, BANCO_AURORA, BANCO_MERIDIANO,
CONTABILIDADE, FINANCEIRO_INTERNO. Só LOJISTA tem cnpj. UTF-8, separador ';'. Nada é enviado: o e-mail só abre pronto
no cliente de e-mail (mailto) da analista. Os e-mails atuais são fictícios, para substituir pelos reais.
Todas as funções recebem `pasta` (padrão: cadastro/ na raiz do projeto).
"""
import csv
import re
from datetime import datetime
from pathlib import Path

from . import config
from . import cadastro
from .cadastro import _escrever_csv

RAIZ = Path(__file__).resolve().parent.parent
CADASTRO_PADRAO = RAIZ / "cadastro"
ARQ_CONTATOS = "contatos.csv"
ARQ_REMOVIDOS = "contatos_removidos.csv"
COLUNAS = ["id_contato", "papel", "cnpj", "nome", "email", "observacao"]
COLUNAS_REMOVIDOS = COLUNAS + ["removido_em", "removido_por"]
_EMAIL = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>.]+$")


class ContatoInvalido(ValueError):
    """Contato malformado ou operação recusada (mensagem em português)."""


def _pasta(pasta):
    return Path(pasta) if pasta is not None else CADASTRO_PADRAO


def _ler_csv(caminho):
    if not Path(caminho).exists():
        return []
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in l.items() if k} for l in csv.DictReader(f, delimiter=";")]


def ler(pasta=None):
    """Lista de contatos (dicts com as COLUNAS). Arquivo ausente: lista vazia."""
    return [{c: l.get(c, "") for c in COLUNAS} for l in _ler_csv(_pasta(pasta) / ARQ_CONTATOS)]


def ler_removidos(pasta=None):
    return _ler_csv(_pasta(pasta) / ARQ_REMOVIDOS)


def _cnpj_do_ec(pasta, ec):
    """CNPJ ligado ao EC Orbe pelo cadastro (DE_PARA_EC ou BLOQUEIO_FATURAMENTO, sem olhar a vigência) ou ''."""
    alvo = re.sub(r"\D", "", ec or "")
    try:
        condicoes = cadastro.ler(_pasta(pasta))
    except (cadastro.CadastroAusente, cadastro.CadastroInvalido):
        return ""
    for c in condicoes:
        if alvo and c["ec_orbe"] == alvo and c["cnpj"] and c["tipo"] in ("DE_PARA_EC", "BLOQUEIO_FATURAMENTO"):
            return c["cnpj"]
    return ""


def para(papel, cnpj=None, pasta=None, ec=None):
    """Contatos do papel (LOJISTA: só os do CNPJ pedido, 14 dígitos ou formatado). Sem CNPJ, `ec=` (EC Orbe) é
    resolvido pelo de-para/bloqueio do cadastro. Lista vazia se não houver."""
    papel = (papel or "").strip().upper()
    alvo = re.sub(r"\D", "", cnpj or "") or (_cnpj_do_ec(pasta, ec) if papel == "LOJISTA" and ec else "")
    return [c for c in ler(pasta) if c["papel"] == papel and (papel != "LOJISTA" or (alvo and c["cnpj"] == alvo))]


def validar(contato, existentes=(), ignorar_id=None):
    """Lista de erros do contato (vazia = ok). `existentes` = contatos atuais (para detectar duplicidade)."""
    erros = []
    papel = (contato.get("papel") or "").strip().upper()
    cnpj = re.sub(r"\D", "", contato.get("cnpj") or "")
    email = (contato.get("email") or "").strip()
    if papel not in config.PAPEIS_CONTATO:
        erros.append(f"Papel '{contato.get('papel', '')}' inválido. Papéis: {', '.join(config.PAPEIS_CONTATO)}.")
    if not (contato.get("nome") or "").strip():
        erros.append("Informe o nome do contato.")
    if not email:
        erros.append("Informe o e-mail do contato.")
    elif not _EMAIL.match(email):
        erros.append(f"E-mail '{email}' inválido (esperado nome@dominio.com.br; um endereço só).")
    if papel == "LOJISTA":
        if cnpj and len(cnpj) != 14:
            erros.append(f"CNPJ '{cnpj}' deve ter 14 dígitos.")
    elif cnpj:
        erros.append(f"Só contato de LOJISTA tem CNPJ (papel {papel}).")
    if not erros:
        for o in existentes:
            if o["id_contato"] != ignorar_id and (o["papel"], o["cnpj"], o["email"].lower()) == (papel, cnpj, email.lower()):
                erros.append(f"Já existe o contato {o['id_contato']} ({o['nome']}) com este papel e e-mail.")
                break
    return erros


def _normalizar(c):
    out = {k: (c.get(k) or "").strip() for k in COLUNAS}
    out["papel"] = out["papel"].upper()
    out["cnpj"] = re.sub(r"\D", "", out["cnpj"])
    return out


def _proximo_id(contatos, removidos=()):
    n = 0
    for c in list(contatos) + list(removidos):
        m = re.fullmatch(r"K(\d+)", c.get("id_contato", ""))
        if m:
            n = max(n, int(m.group(1)))
    return f"K{n + 1:03d}"


def _gravar(pasta, contatos):
    _escrever_csv(_pasta(pasta) / ARQ_CONTATOS, COLUNAS, contatos)


def adicionar(pasta, contato, usuario=""):
    """Valida e grava um contato novo (gera o id K###). Devolve o contato gravado."""
    atuais = ler(pasta)
    c = _normalizar(contato)
    erros = validar(c, atuais)
    if erros:
        raise ContatoInvalido(" ".join(erros))
    c["id_contato"] = _proximo_id(atuais, ler_removidos(pasta))
    _gravar(pasta, atuais + [c])
    return c


def atualizar(pasta, id_contato, campos, usuario=""):
    """Altera campos (papel, cnpj, nome, email, observacao) de um contato; valida o resultado. Devolve o contato."""
    atuais = ler(pasta)
    alvo = next((c for c in atuais if c["id_contato"] == id_contato), None)
    if alvo is None:
        raise ContatoInvalido(f"Contato {id_contato} não encontrado.")
    novo = _normalizar({**alvo, **{k: v for k, v in campos.items() if k in COLUNAS and k != "id_contato"}})
    novo["id_contato"] = id_contato
    erros = validar(novo, atuais, ignorar_id=id_contato)
    if erros:
        raise ContatoInvalido(" ".join(erros))
    _gravar(pasta, [novo if c["id_contato"] == id_contato else c for c in atuais])
    return novo


def remover(pasta, id_contato, usuario=""):
    """Tira o contato de contatos.csv e o MOVE para contatos_removidos.csv (com data e quem removeu). Devolve o contato."""
    atuais = ler(pasta)
    alvo = next((c for c in atuais if c["id_contato"] == id_contato), None)
    if alvo is None:
        raise ContatoInvalido(f"Contato {id_contato} não encontrado.")
    hist = ler_removidos(pasta) + [{**alvo, "removido_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "removido_por": (usuario or "").strip()}]
    _escrever_csv(_pasta(pasta) / ARQ_REMOVIDOS, COLUNAS_REMOVIDOS, hist)
    _gravar(pasta, [c for c in atuais if c["id_contato"] != id_contato])
    return alvo
