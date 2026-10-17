"""Assistente de cadastro: texto livre -> condição(ões) de cliente (PLANO_03).

A IA converte o texto da analista em condições no schema de `src.cadastro`; o código confere tudo:
- lojista só dentre a lista recebida (cnpj/ec/nome); ambíguo ou inexistente -> `duvidas` e nenhuma condição;
- ISENCAO e TAXA_ESPECIAL exigem `aprovado_por` que apareça no texto; senão `duvidas` e nenhuma condição;
- taxa, datas e EC têm de aparecer no texto (a IA não inventa valor nem data);
- tipos só ISENCAO, TAXA_ESPECIAL, BLOQUEIO_FATURAMENTO, DE_PARA_EC, NOTA_PENDENCIA;
- depois valida com `cadastro.validar(condicao, pasta)` (dry-run) e devolve os erros legíveis;
- `antes_depois` por faixa com `cadastro.taxa_efetiva` (antes = sem a condição; depois = com), na data
  de início da vigência.
NUNCA grava: a gravação é do botão "Confirmar" (`cadastro.adicionar_varias`).

Saída: {"condicoes", "resumo", "antes_depois", "duvidas", "erros", "aviso", "erro", ...}.
`erros` não vazio significa que a prévia não pode ser confirmada.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src import cadastro, ia, ia_acoes
from src.ia_acoes import sem_acento

AVISO = "Proposta da IA — confira a prévia antes de confirmar. Nada foi gravado."
TIPOS_PERMITIDOS = ["ISENCAO", "TAXA_ESPECIAL", "BLOQUEIO_FATURAMENTO", "DE_PARA_EC", "NOTA_PENDENCIA"]
MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]
GENERICAS = {"ltda", "eireli", "epp", "escola", "escolas", "viagens", "intercambio", "idiomas", "turismo",
             "agencia", "cia", "servicos"}
CAMPOS_MODELO = ["tipo", "cnpj", "ec_orbe", "lojista", "linha_negocio", "campo", "valor", "vigencia_inicio",
                 "vigencia_fim", "aprovado_por", "fonte", "observacao"]

SCHEMA_SAIDA = {
    "type": "object",
    "properties": {
        "condicoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string", "enum": TIPOS_PERMITIDOS},
                    **{c: {"type": "string"} for c in CAMPOS_MODELO if c != "tipo"},
                },
                "required": CAMPOS_MODELO,
                "additionalProperties": False,
            },
        },
        "resumo": {"type": "string"},
        "duvidas": {"type": "string"},
    },
    "required": ["condicoes", "resumo", "duvidas"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- prompt e mensagem
def versao_prompt() -> str:
    m = re.search(r"versao:\s*([\w.\-]+)", ia._ler_prompt("cadastro.md"))
    return m.group(1) if m else "desconhecida"


def montar_system() -> str:
    return ia._ler_prompt("contexto_tarvo.md").strip() + "\n\n---\n\n" + ia._ler_prompt("cadastro.md").strip()


def _so_digitos(t) -> str:
    return re.sub(r"\D", "", str(t or ""))


def _nome(l: dict) -> str:
    return str(l.get("lojista") or l.get("nome") or "").strip()


def _ec(l: dict) -> str:
    return _so_digitos(l.get("ec") or l.get("ec_orbe"))


def _resumo_condicao(c: dict) -> dict:
    return {k: c.get(k) for k in ("id_condicao", "tipo", "lojista", "cnpj", "ec_orbe", "linha_negocio", "campo",
                                  "valor", "vigencia_inicio", "vigencia_fim") if c.get(k)}


def montar_mensagem(texto: str, lojistas: list[dict], vigentes: list[dict], hoje: date) -> str:
    dados = {
        "hoje": hoje.isoformat(),
        "texto": texto,
        "lojistas": [{"lojista": _nome(l), "cnpj": _so_digitos(l.get("cnpj")), "ec_orbe": _ec(l)} for l in lojistas],
        "condicoes_vigentes": [_resumo_condicao(c) for c in vigentes],
        "tipos": TIPOS_PERMITIDOS,
        "faixas": cadastro.FAIXAS,
        "linhas_negocio": cadastro.LINHAS,
    }
    return ("Texto da analista e contexto do cadastro (JSON):\n\n"
            + json.dumps(dados, ensure_ascii=False, indent=2, default=str)
            + "\n\nResponda no formato pedido. Se faltar dado, devolva `condicoes` vazio e a pergunta em `duvidas`.")


# ---------------------------------------------------------------- conferências contra o texto
def _data_no_texto(iso: str, texto: str) -> bool:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except ValueError:
        return False
    n = sem_acento(texto)
    simples = [f"{d:02d}/{m:02d}/{y}", f"{d}/{m}/{y}", f"{d:02d}/{m:02d}/{y % 100:02d}", iso,
               f"{d:02d}.{m:02d}.{y}", f"{d:02d}-{m:02d}-{y}"]
    if any(re.search(rf"(?<![\d/]){re.escape(s)}(?![\d])", n) for s in simples):
        return True
    if re.search(rf"(?<![\d/]){d}/{m}(?![\d/])|(?<![\d/]){d:02d}/{m:02d}(?![\d/])", n):
        return True
    return bool(re.search(rf"\b0?{d}\s*[ºo°]?\s+de\s+{MESES[m - 1]}\b", n))


def _valor_no_texto(valor: str, texto: str) -> bool:
    try:
        v = Decimal(valor)
    except InvalidOperation:
        return False
    formas = {format(v.normalize(), "f"), f"{v:.2f}", f"{v:.1f}"}
    n = texto.replace(" ", "")
    for f in list(formas):
        for forma in {f, f.replace(".", ",")}:
            if re.search(rf"(?<![\d.,]){re.escape(forma)}(?![\d])", n):
                return True
    return False


def _lojista_no_texto(l: dict, texto: str) -> bool:
    n = sem_acento(texto)
    dig = _so_digitos(texto)
    if (_so_digitos(l.get("cnpj")) and _so_digitos(l.get("cnpj")) in dig) or (_ec(l) and _ec(l) in dig):
        return True
    palavras = [p for p in re.findall(r"[a-z0-9]+", sem_acento(_nome(l)))]
    chaves = [p for p in palavras if len(p) >= 4 and p not in GENERICAS] or palavras
    return any(re.search(rf"\b{re.escape(p)}\b", n) for p in chaves)


def _achar_lojista(lojistas: list[dict], cnpj: str, ec: str) -> dict | None:
    cnpj, ec = _so_digitos(cnpj), _so_digitos(ec)
    por_cnpj = [l for l in lojistas if cnpj and _so_digitos(l.get("cnpj")) == cnpj]
    por_ec = [l for l in lojistas if ec and _ec(l) == ec]
    if cnpj and ec:
        return next((l for l in por_cnpj if l in por_ec), None) or (por_cnpj[0] if por_cnpj and not por_ec else None)
    achados = por_cnpj or por_ec
    return achados[0] if achados else None


# ---------------------------------------------------------------- validação (dry-run) e antes/depois
def _validar_dry(c: dict, pasta, contratos=None) -> tuple[dict, list[str]]:
    """Dry-run com `cadastro.validar(condicao, pasta)` (devolve a lista de erros legíveis, vazia = ok).
    Devolve também a condição normalizada pelo próprio cadastro, para o antes/depois."""
    try:
        norm = cadastro._validar({**c, "data_registro": date.today().isoformat()}, "Condição nova")
        norm = {**norm, "id_condicao": "", "data_registro": ""}
    except cadastro.CadastroInvalido as exc:
        return c, [str(exc)]
    try:
        r = cadastro.validar(c, pasta, contratos=contratos)
    except cadastro.CadastroInvalido as exc:
        return norm, [str(exc)]
    return norm, [str(e) for e in (r or [])] if isinstance(r, (list, tuple)) else []


def _fmt_taxa(v, faixa: str) -> str:
    if v is None:
        return "—"
    p = Decimal(v) * (Decimal(100) if faixa == cadastro.FAIXA_REMESSA else Decimal(1))
    return f"{p:.2f}".replace(".", ",") + "%"


def antes_depois(condicao: dict, lojista: dict | None, vigentes: list[dict]) -> list[dict]:
    """Linhas {"faixa","antes","depois","origem"} das faixas que a condição altera (ISENCAO/TAXA_ESPECIAL)."""
    if condicao["tipo"] not in ("ISENCAO", "TAXA_ESPECIAL") or lojista is None:
        return []
    linha = {"taxas": {}, "spread": None, "linha": None, **copy.deepcopy(lojista)}
    linha["cnpj"] = _so_digitos(condicao.get("cnpj") or lojista.get("cnpj"))
    linha["ec"] = _ec(lojista) or None
    data = date.fromisoformat(condicao["vigencia_inicio"])
    nova = {c: condicao.get(c, "") for c in cadastro.COLUNAS}
    nova["id_condicao"] = nova["id_condicao"] or "NOVA"
    linhas = []
    for faixa in cadastro._faixas_da_condicao(nova):
        antes, _ = cadastro.taxa_efetiva(linha, vigentes, data, faixa)
        depois, origem = cadastro.taxa_efetiva(linha, vigentes + [nova], data, faixa)
        linhas.append({"faixa": cadastro.ROTULO_FAIXA.get(faixa, faixa), "faixa_codigo": faixa,
                       "antes": _fmt_taxa(antes, faixa), "depois": _fmt_taxa(depois, faixa), "origem": origem})
    return linhas


# ---------------------------------------------------------------- execução
def _resultado(**kw) -> dict:
    r = {"condicoes": [], "resumo": "", "antes_depois": [], "duvidas": "", "erros": [], "aviso": AVISO,
         "erro": None, "provedor": None, "modelo": ia.MODELO, "versao_prompt": versao_prompt()}
    r.update(kw)
    return r


def _conferir(bruto: dict, texto: str, lojistas: list[dict]) -> tuple[list[dict], list[tuple[dict, dict | None]], list[str]]:
    """(condições normalizadas, [(condição, lojista)], dúvidas). Qualquer dúvida zera as condições."""
    duvidas, saida = [], []
    for n, c in enumerate(bruto.get("condicoes") or [], start=1):
        pre = f"Condição {n}: " if len(bruto.get("condicoes") or []) > 1 else ""
        tipo = str(c.get("tipo") or "").strip().upper()
        if tipo not in TIPOS_PERMITIDOS:
            duvidas.append(f"{pre}tipo '{tipo}' não permitido pelo assistente.")
            continue
        loj = _achar_lojista(lojistas, c.get("cnpj"), c.get("ec_orbe"))
        if loj is None:
            duvidas.append(f"{pre}não encontrei o lojista (CNPJ '{c.get('cnpj') or ''}', EC "
                           f"'{c.get('ec_orbe') or ''}') na lista de clientes. Qual é o lojista?")
            continue
        if not _lojista_no_texto(loj, texto):
            duvidas.append(f"{pre}não consegui confirmar pelo texto que o lojista é {_nome(loj)}. Qual é o lojista?")
            continue
        out = {k: str(c.get(k) or "").strip() for k in cadastro.COLUNAS}
        out.update({"tipo": tipo, "cnpj": _so_digitos(loj.get("cnpj")), "lojista": _nome(loj) or out["lojista"],
                    "campo": out["campo"].upper() if out["campo"].lower() != "todas" else "todas",
                    "linha_negocio": out["linha_negocio"].upper(), "id_condicao": "", "data_registro": "",
                    "fonte": out["fonte"] or "Assistente de cadastro (IA)"})
        out["ec_orbe"] = _so_digitos(c.get("ec_orbe")) if tipo == "DE_PARA_EC" else (_ec(loj) or _so_digitos(c.get("ec_orbe")))
        if tipo == "DE_PARA_EC" and out["ec_orbe"] and out["ec_orbe"] not in _so_digitos(texto):
            duvidas.append(f"{pre}o EC {out['ec_orbe']} não aparece no texto. Qual é o EC da Orbe?")
            continue
        if tipo in cadastro.EXIGEM_APROVACAO:
            aprov = out["aprovado_por"]
            if not aprov or sem_acento(aprov) not in sem_acento(texto):
                duvidas.append(f"{pre}quem do Comercial aprovou {cadastro.ROTULO_TIPO[tipo]}? "
                               "O texto não diz o aprovador.")
                continue
        for campo_data in ("vigencia_inicio", "vigencia_fim"):
            iso = out[campo_data]
            if not iso:
                continue
            try:
                date.fromisoformat(iso)
            except ValueError:
                duvidas.append(f"{pre}{campo_data} '{iso}' não é uma data válida (AAAA-MM-DD).")
                break
            if not _data_no_texto(iso, texto):
                duvidas.append(f"{pre}a data {iso} não aparece no texto. Qual é a data de "
                               f"{'início' if campo_data == 'vigencia_inicio' else 'fim'} da vigência?")
                break
        else:
            if not out["vigencia_inicio"]:
                duvidas.append(f"{pre}qual é a data de início da vigência?")
                continue
            if tipo == "TAXA_ESPECIAL" and not _valor_no_texto(out["valor"], texto):
                duvidas.append(f"{pre}a taxa '{out['valor']}' não aparece no texto. Qual é a taxa?")
                continue
            saida.append((out, loj))
            continue
        continue
    return [o for o, _ in saida], saida, duvidas


def propor(texto: str, lojistas: list[dict], condicoes_vigentes: list[dict], pasta_cadastro, *, cliente=None,
           hoje: date | None = None, raiz: Path | None = None) -> dict:
    """Proposta (sem gravar) a partir do texto livre. Nunca levanta exceção por falta de chave ou erro da API.

    `lojistas`: lista de dicts com `lojista` (ou `nome`), `cnpj`, `ec` (ou `ec_orbe`) e, para o antes/depois,
    o contrato da planilha (`taxas`, `spread`, `linha`), como em `leitores.ler_taxas`.
    """
    hoje = hoje or date.today()
    texto = str(texto or "").strip()
    if not texto:
        return _resultado(duvidas="Escreva a condição que quer cadastrar.")
    if cliente is None:
        cliente, motivo = ia_acoes.criar_cliente(SCHEMA_SAIDA, "condicoes_cadastro", raiz)
        if cliente is None:
            return _resultado(erro=f"IA indisponível: {motivo}")
    cliente = ia._como_cliente(cliente)
    base = {"provedor": getattr(cliente, "provedor", None), "modelo": getattr(cliente, "modelo", ia.MODELO)}
    try:
        bruto, modelo_resposta = cliente.gerar(montar_system(),
                                               montar_mensagem(texto, lojistas, condicoes_vigentes or [], hoje))
    except Exception as exc:  # noqa: BLE001
        return _resultado(erro=f"IA indisponível: {ia._mensagem_erro(exc)}", **base)
    base["modelo_resposta"] = modelo_resposta
    if not isinstance(bruto, dict):
        return _resultado(erro="IA indisponível: resposta da IA não é um JSON válido.", **base)
    resumo = " ".join(str(bruto.get("resumo") or "").split())
    duvida_ia = " ".join(str(bruto.get("duvidas") or "").split())
    if duvida_ia:  # a IA pediu esclarecimento: nenhuma condição segue
        return _resultado(resumo=resumo, duvidas=duvida_ia, **base)
    condicoes, pares, duvidas = _conferir(bruto, texto, lojistas)
    if duvidas:
        return _resultado(resumo=resumo, duvidas=" ".join(duvidas), **base)
    if not pares:
        return _resultado(resumo=resumo, duvidas="Não identifiquei nenhuma condição no texto. "
                          "Informe lojista, tipo, faixa, taxa, início e quem aprovou.", **base)
    finais, erros, linhas = [], [], []
    vigentes = list(condicoes_vigentes or [])
    for n, (c, loj) in enumerate(pares, start=1):
        norm, errs = _validar_dry(c, pasta_cadastro, lojistas)
        prefixo = f"Condição {n}: " if len(pares) > 1 else ""
        erros.extend(prefixo + e for e in errs)
        finais.append({k: norm.get(k, c.get(k, "")) for k in cadastro.COLUNAS})
        if not errs:
            try:
                linhas.extend(antes_depois(norm, loj, vigentes))
            except Exception as exc:  # noqa: BLE001 — a prévia é auxiliar; o erro aparece, não derruba
                erros.append(f"Não foi possível calcular o antes/depois ({type(exc).__name__}).")
    return _resultado(condicoes=finais, resumo=resumo, antes_depois=linhas, erros=erros, **base)
