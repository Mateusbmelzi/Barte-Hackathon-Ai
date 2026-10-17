"""Ação sugerida pela IA para itens da fila de trabalho (PLANO_03).

Para cada pendência ou divergência a IA diz, em 1 ou 2 frases, o que fazer e rascunha e-mails
curtos para os destinos permitidos. Nada é enviado: a analista revisa e envia no próprio e-mail.

Reaproveita de `src.ia` os provedores (OpenRouter/Anthropic), a leitura da chave, o tratamento de
erro e a saída estruturada; aqui só mudam o schema, o prompt e os guarda-corpos:
- destino fora dos permitidos é removido; e-mail para destino removido também;
- todo valor "R$ ..." do texto tem de existir no item, senão o e-mail é descartado (ajuste);
- texto que afirma que a devolução/cobrança já foi feita é descartado;
- promessa de devolução/crédito/pagamento sem "conforme aprovação" é descartada;
- assunto até 90 caracteres (cortado); corpo até 1500 (senão descartado, limite do mailto).
Nenhum valor vem da IA. Sem chave ou com erro da API o resultado traz `erro` legível.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src import ia

VERSAO_FALLBACK = "desconhecida"
AVISO = "Rascunho da IA — revise antes de enviar"
ASSINATURA_PADRAO = "Helena — Financeiro Tarvo"
EMPRESA_PADRAO = "Tarvo"
PAPEIS = ["LOJISTA", "ORBE", "PONTE", "COMERCIAL", "BANCO_AURORA", "BANCO_MERIDIANO",
          "CONTABILIDADE", "FINANCEIRO_INTERNO"]
DESTINO_PADRAO = ["FINANCEIRO_INTERNO"]
MAX_ASSUNTO = 90
MAX_CORPO = 1500
ARQ_CACHE = "sugestoes_ia.json"

# Campos do item que vão para o modelo (nada além disto).
CAMPOS_ITEM = ["chave", "tipo", "titulo", "valor", "motivo", "quem_decide", "lojista", "cnpj", "ec",
               "contraparte", "natureza", "qtd", "resumo_fatos", "acao_regra", "hipotese_principal", "rota_valores", "fatos"]

SCHEMA_SAIDA = {
    "type": "object",
    "properties": {
        "chave": {"type": "string"},
        "acao_resumo": {"type": "string"},
        "destinos": {"type": "array", "items": {"type": "string", "enum": PAPEIS}},
        "emails": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "papel": {"type": "string", "enum": PAPEIS},
                    "assunto": {"type": "string"},
                    "corpo": {"type": "string"},
                },
                "required": ["papel", "assunto", "corpo"],
                "additionalProperties": False,
            },
        },
        "nota_interna": {"type": "string"},
        "prazo_sugerido": {"type": "string"},
        "valores_citados": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["chave", "acao_resumo", "destinos", "emails", "nota_interna", "prazo_sugerido", "valores_citados"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- disponibilidade e cliente
def disponivel(raiz: Path | None = None) -> tuple[bool, str]:
    """(pode usar a IA?, motivo legível). Mesma regra de `src.ia.disponivel`."""
    return ia.disponivel(raiz)


class _SdkComEsquema:
    """Troca o schema da saída estruturada nas chamadas do SDK da Anthropic."""

    def __init__(self, sdk, schema):
        self._sdk, self._schema = sdk, schema
        self.messages = self

    def create(self, **kw):
        cfg = copy.deepcopy(kw.get("output_config") or {})
        cfg["format"] = {"type": "json_schema", "schema": self._schema}
        kw["output_config"] = cfg
        return self._sdk.messages.create(**kw)


class _OpenRouterComEsquema(ia.ClienteOpenRouter):
    def __init__(self, chave, schema, nome, **kw):
        super().__init__(chave, **kw)
        self._schema, self._nome = schema, nome

    def payload(self, system, mensagem):
        p = super().payload(system, mensagem)
        p["response_format"] = {"type": "json_schema",
                                "json_schema": {"name": self._nome, "strict": True, "schema": self._schema}}
        return p


def criar_cliente(schema: dict, nome: str, raiz: Path | None = None):
    """(cliente, motivo): cliente com a interface `gerar(system, mensagem)` usando `schema`, ou
    (None, motivo legível) se a IA não está disponível. Reaproveita provedor e chave de `src.ia`."""
    ok, motivo = ia.disponivel(raiz)
    if not ok:
        return None, motivo
    try:
        provedor, chave = ia.selecionar_provedor(raiz)
        if provedor == "openrouter":
            return _OpenRouterComEsquema(chave, schema, nome), ""
        import anthropic
        sdk = anthropic.Anthropic(api_key=chave, timeout=ia.TIMEOUT_S, max_retries=ia.MAX_TENTATIVAS)
        return ia.AdaptadorAnthropic(_SdkComEsquema(sdk, schema)), ""
    except Exception as exc:  # noqa: BLE001
        return None, ia._mensagem_erro(exc)


# ---------------------------------------------------------------- texto e valores
def sem_acento(texto: str) -> str:
    n = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


_RE_REAIS = re.compile(r"R\$\s*(-?\d[\d.]*(?:,\d{1,2})?)")


def _decimal_br(txt: str) -> Decimal | None:
    txt = txt.strip().rstrip(".")
    txt = txt.replace(".", "").replace(",", ".") if "," in txt else txt.replace(".", "")
    try:
        return abs(Decimal(txt)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def valores_reais(texto: str) -> list[Decimal]:
    """Valores 'R$ ...' do texto, em Decimal (módulo, 2 casas)."""
    return [v for v in (_decimal_br(m) for m in _RE_REAIS.findall(texto or "")) if v is not None]


def _valor_num(v) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return abs(Decimal(str(v))).quantize(Decimal("0.01"))
    except InvalidOperation:
        return _decimal_br(str(v))


_RE_NUM = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})(?![\d])")
_RE_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|p\.\s?p\.)")


def percentuais(texto: str) -> set[Decimal]:
    """Percentuais ('2,49%', '0,50 p.p.') do texto como Decimal normalizado."""
    out = set()
    for m in _RE_PCT.findall(texto or ""):
        try:
            out.add(Decimal(m.replace(",", ".")).normalize())
        except InvalidOperation:
            pass
    return out


def valores_permitidos(item: dict) -> set[Decimal]:
    """Valores que o texto da IA pode citar: o `valor` do item e os 'R$ ...' de qualquer texto do item."""
    ok = set()
    v = _valor_num(item.get("valor"))
    if v is not None:
        ok.add(v)
    corpo = json.dumps({c: item.get(c) for c in CAMPOS_ITEM if c in item}, ensure_ascii=False, default=str)
    ok.update(valores_reais(corpo.replace("\\n", " ")))
    return ok


_PART = r"(?:devolvid|creditad|estornad|ressarcid|reembolsad|pag[oa]s?|efetuad|realizad|feit[oa]s?|processad|concluid|quitad)\w*"
_SUBST = r"(?:devolucao|cobranca|estorno|credito|ressarcimento|reembolso|pagamento)s?"
_FEITO = re.compile(
    r"\b(?:"
    rf"{_SUBST}\s+(?:ja\s+)?(?:(?:foi|foram|esta|estao)\s+)?(?:feit|efetuad|realizad|processad|concluid|quitad)\w*"
    rf"|(?:ja\s+)?(?:foi|foram|esta|estao|fora)\s+{_PART}"
    r"|ja\s+(?:foi|foram|esta|estao)?\s*(?:cobrad|devolvid|creditad|estornad|ressarcid|reembolsad|pag[oa]s?)\w*"
    r"|(?:ja\s+)?(?:devolvemos|devolvi|estornamos|estornei|creditamos|creditei|ressarcimos|ressarci"
    r"|reembolsamos|reembolsei|pagamos|paguei|cobramos|cobrei)"
    r"|(?:ja\s+)?(?:efetuamos|realizamos|fizemos)\s+(?:a|o|as|os)\s+(?:devolucao|cobranca|estorno|credito|pagamento|ressarcimento)s?"
    r")\b")
_PROMESSA = re.compile(
    r"\b(?:devolveremos|estornaremos|creditaremos|ressarciremos|reembolsaremos|pagaremos"
    r"|faremos\s+(?:a|o)\s+(?:devolucao|estorno|credito|pagamento|ressarcimento)"
    r"|sera(?:o)?\s+(?:devolvid|estornad|creditad|ressarcid|reembolsad|pag|feit|efetuad|realizad)\w*"
    r"|vamos\s+(?:devolver|estornar|creditar|ressarcir|reembolsar|pagar)"
    r"|receber(?:a|ao))\b")
_CONFORME = re.compile(r"conforme\s+aprovacao")


_RE_DATA = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,4})(?:/\d{2,4})?(?![\d/])")


def datas_do_texto(texto: str) -> set[tuple[int, int]]:
    """Datas dd/mm (ou mm/aaaa) citadas no texto, sem o ano, como pares de inteiros."""
    out = {(int(a), int(b)) for a, b in _RE_DATA.findall(texto or "")}
    out |= {(int(d), int(m)) for m, d in re.findall(r"(?<!\d)\d{4}-(\d{2})-(\d{2})(?!\d)", texto or "")}
    return out


def _problema_texto(texto: str, permitidos: set[Decimal], promessa: bool = True,
                    datas: set[tuple[int, int]] | None = None, pcts: set[Decimal] | None = None) -> str | None:
    """Motivo (legível) pelo qual o texto viola um guarda-corpo, ou None."""
    for v in valores_reais(texto):
        if v not in permitidos:
            return f"valor R$ {_fmt(v)} não consta do item"
    if datas is not None:
        for d, m in datas_do_texto(texto):
            if (d, m) not in datas:
                return f"data {d:02d}/{m:02d} não consta do item"
    if pcts is not None:
        for q in sorted(percentuais(texto)):
            if q not in pcts:
                return f"percentual {format(q, 'f').replace('.', ',')} não consta do item"
    n = sem_acento(texto)
    if _FEITO.search(n):
        return "afirma que a devolução/cobrança já foi feita"
    if promessa and _PROMESSA.search(n) and not _CONFORME.search(n):
        return 'promete devolução/crédito/pagamento sem "conforme aprovação do financeiro"'
    return None


def _fmt(v: Decimal) -> str:
    inteiro, frac = f"{v:.2f}".split(".")
    return f"{int(inteiro):,}".replace(",", ".") + "," + frac


# ---------------------------------------------------------------- prompt e mensagem
def _ler_prompt(nome: str) -> str:
    return (ia.PASTA_PROMPTS / nome).read_text(encoding="utf-8")


def versao_prompt() -> str:
    m = re.search(r"versao:\s*([\w.\-]+)", _ler_prompt("acoes.md"))
    return m.group(1) if m else VERSAO_FALLBACK


def montar_system() -> str:
    return _ler_prompt("contexto_tarvo.md").strip() + "\n\n---\n\n" + _ler_prompt("acoes.md").strip()


def _contexto(contexto: dict | None) -> dict:
    c = dict(contexto or {})
    c.setdefault("empresa", EMPRESA_PADRAO)
    c.setdefault("assinatura", ASSINATURA_PADRAO)
    return c


def montar_mensagem(item: dict, contexto: dict, destinos: list[str]) -> str:
    contatos = contexto.get("contatos") or {}
    dados = {
        "competencia": contexto.get("competencia"),
        "empresa": contexto["empresa"],
        "assinatura": contexto["assinatura"],
        "objetivo": (contexto.get("objetivo") or item.get("objetivo")
                     or _acao_do_tipo(item.get("tipo"), contexto).get("objetivo") or ""),
        "destinos_permitidos": [{"papel": d, **({"contato": contatos[d]} if d in contatos else {})}
                                for d in destinos],
        "item": {c: copy.deepcopy(item.get(c)) for c in CAMPOS_ITEM if item.get(c) not in (None, "")},
    }
    v = _valor_num(item.get("valor"))
    if v is not None:
        dados["item"]["valor_formatado"] = f"R$ {_fmt(v)}"
    return ("Item da fila para sugerir a ação (JSON):\n\n"
            + json.dumps(dados, ensure_ascii=False, indent=2, default=str)
            + "\n\nResponda no formato pedido, escrevendo só para os destinos permitidos.")


# ---------------------------------------------------------------- guarda-corpos
def validar(bruto: dict, item: dict, contexto: dict, destinos_permitidos: list[str]) -> dict:
    """Aplica os guarda-corpos à resposta do modelo e devolve o resultado final (sem rede)."""
    contexto = _contexto(contexto)
    permitidos_papel = [d for d in destinos_permitidos if d in PAPEIS]
    permitidos_val = valores_permitidos(item)
    corpo_item = json.dumps({c: item.get(c) for c in CAMPOS_ITEM if c in item}, ensure_ascii=False, default=str)
    datas_ok = datas_do_texto(corpo_item.replace("\n", " ") + " " + str(contexto.get("competencia") or ""))
    pcts_ok = percentuais(corpo_item)
    ajustes = []

    destinos = []
    for d in bruto.get("destinos") or []:
        if d in permitidos_papel:
            if d not in destinos:
                destinos.append(d)
        else:
            ajustes.append(f"destino {d} removido: fora dos permitidos")

    emails = []
    nota_bruta = " ".join(str(bruto.get("nota_interna") or "").split())
    for e in bruto.get("emails") or []:
        if not isinstance(e, dict):
            continue
        papel = str(e.get("papel") or "")
        assunto = " ".join(str(e.get("assunto") or "").split())
        corpo = str(e.get("corpo") or "").strip()
        if papel not in permitidos_papel:
            ajustes.append(f"e-mail para {papel or '(sem destino)'} removido: destino fora dos permitidos")
            continue
        if papel == "FINANCEIRO_INTERNO":   # a própria Helena: vira nota interna, não e-mail
            if not nota_bruta:
                nota_bruta = corpo
            ajustes.append("e-mail para FINANCEIRO_INTERNO convertido em nota interna")
            if papel not in destinos:
                destinos.append(papel)
            continue
        if not assunto or not corpo:
            ajustes.append(f"e-mail para {papel} removido: assunto ou corpo vazio")
            continue
        assinatura = contexto["assinatura"]
        if assinatura and assinatura not in corpo:
            corpo = f"{corpo}\n\n{assinatura}"
        problema = _problema_texto(assunto + "\n" + corpo, permitidos_val, datas=datas_ok, pcts=pcts_ok)
        if problema:
            ajustes.append(f"e-mail para {papel} descartado: {problema}")
            continue
        if len(corpo) > MAX_CORPO:
            ajustes.append(f"e-mail para {papel} descartado: corpo com {len(corpo)} caracteres (máx. {MAX_CORPO})")
            continue
        if len(assunto) > MAX_ASSUNTO:
            assunto = assunto[:MAX_ASSUNTO - 1].rstrip() + "…"
            ajustes.append(f"assunto do e-mail para {papel} cortado em {MAX_ASSUNTO} caracteres")
        emails.append({"papel": papel, "assunto": assunto, "corpo": corpo})
        if papel not in destinos:
            destinos.append(papel)

    nota = " ".join(nota_bruta.split())[:600] if "FINANCEIRO_INTERNO" in permitidos_papel else ""
    if nota:
        problema = _problema_texto(nota, permitidos_val, promessa=False, datas=datas_ok, pcts=pcts_ok)
        if problema:
            ajustes.append(f"nota interna descartada: {problema}")
            nota = ""
    acao = " ".join(str(bruto.get("acao_resumo") or "").split())
    problema = _problema_texto(acao, permitidos_val, promessa=False, datas=datas_ok, pcts=pcts_ok) if acao else None
    if problema:
        ajustes.append(f"resumo da ação substituído pelo objetivo do playbook: {problema}. Texto original: {acao}")
        acao = str(contexto.get("objetivo") or item.get("objetivo")
                   or _acao_do_tipo(item.get("tipo"), contexto).get("objetivo") or "")
    citados = []
    for e in emails:
        for v in valores_reais(e["assunto"] + " " + e["corpo"]):
            txt = f"R$ {_fmt(v)}"
            if txt not in citados:
                citados.append(txt)
    return {
        "chave": item.get("chave"),
        "acao_resumo": acao,
        "destinos": destinos,
        "emails": emails,
        "nota_interna": nota,
        "prazo_sugerido": " ".join(str(bruto.get("prazo_sugerido") or "").split()),
        "valores_citados": citados,
        "aviso": AVISO,
        "ajustes": ajustes,
        "erro": None,
    }


def _base(item: dict, cliente=None) -> dict:
    return {
        "chave": item.get("chave"), "acao_resumo": "", "destinos": [], "emails": [],
        "nota_interna": "", "prazo_sugerido": "", "valores_citados": [], "aviso": AVISO, "ajustes": [], "erro": None,
        "provedor": getattr(cliente, "provedor", None), "modelo": getattr(cliente, "modelo", ia.MODELO),
        "modelo_resposta": None, "versao_prompt": versao_prompt(),
    }


def _com_erro(item: dict, mensagem: str, cliente=None, modelo_resposta=None) -> dict:
    r = _base(item, cliente)
    r["modelo_resposta"] = modelo_resposta
    r["erro"] = f"IA indisponível: {mensagem} O objetivo do playbook continua valendo."
    return r


# ---------------------------------------------------------------- execução
def _acao_do_tipo(tipo, contexto: dict | None = None) -> dict:
    """Entrada de ACOES_POR_TIPO (objetivo e destinos) do tipo; padrão FINANCEIRO_INTERNO."""
    mapa = (contexto or {}).get("acoes_por_tipo")
    if mapa is not None:
        return mapa.get(tipo) or {"objetivo": "", "destinos": list(DESTINO_PADRAO)}
    try:
        from src import config
        return config.acao_do_tipo(tipo)
    except (ImportError, AttributeError):
        return {"objetivo": "", "destinos": list(DESTINO_PADRAO)}


def _destinos_do_tipo(item: dict, contexto: dict) -> list[str]:
    if item.get("destinos_permitidos"):
        return list(item["destinos_permitidos"])
    return list(_acao_do_tipo(item.get("tipo"), contexto).get("destinos") or DESTINO_PADRAO)


def sugerir(item: dict, contexto: dict, destinos_permitidos: list[str], *, cliente=None,
            raiz: Path | None = None) -> dict:
    """Sugestão para UM item. Nunca levanta exceção por falta de chave, biblioteca ou erro da API."""
    contexto = _contexto(contexto)
    destinos_permitidos = [d for d in destinos_permitidos or DESTINO_PADRAO if d in PAPEIS] or list(DESTINO_PADRAO)
    if cliente is None:
        cliente, motivo = criar_cliente(SCHEMA_SAIDA, "acao_sugerida", raiz)
        if cliente is None:
            return _com_erro(item, motivo)
    cliente = ia._como_cliente(cliente)
    try:
        bruto, modelo_resposta = cliente.gerar(montar_system(), montar_mensagem(item, contexto, destinos_permitidos))
    except Exception as exc:  # noqa: BLE001 — qualquer falha vira erro legível do item
        modelo = exc.args[1] if isinstance(exc, ia.ErroIA) and len(exc.args) > 1 else None
        return _com_erro(item, ia._mensagem_erro(exc), cliente, modelo)
    r = _base(item, cliente)
    r["modelo_resposta"] = modelo_resposta
    r.update(validar(bruto if isinstance(bruto, dict) else {}, item, contexto, destinos_permitidos))
    return r


def _impressao(item: dict, contexto: dict, destinos: list[str]) -> str:
    base = json.dumps([montar_mensagem(item, _contexto(contexto), destinos), versao_prompt()],
                      ensure_ascii=False, default=str)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _ler_cache(caminho: Path) -> dict:
    try:
        d = json.loads(caminho.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def sugerir_todos(itens: list[dict], contexto: dict, *, cliente=None, max_paralelo: int = 4,
                  pasta: Path | None = None, raiz: Path | None = None) -> list[dict]:
    """Uma sugestão por item, na ordem recebida, em paralelo limitado. Os destinos vêm de
    `item['destinos_permitidos']` ou de `ACOES_POR_TIPO[item['tipo']]['destinos']` (config ou
    `contexto['acoes_por_tipo']`). Com `pasta`, usa/atualiza o cache `<pasta>/sugestoes_ia.json`
    (chave do item + impressão da entrada); resultados com erro não são guardados."""
    contexto = _contexto(contexto)
    destinos = [_destinos_do_tipo(i, contexto) for i in itens]
    cache_arq = Path(pasta) / ARQ_CACHE if pasta else None
    cache = _ler_cache(cache_arq) if cache_arq else {}
    imp = [_impressao(i, contexto, d) for i, d in zip(itens, destinos)]
    resultados: list[dict | None] = [None] * len(itens)
    pendentes = []
    for n, item in enumerate(itens):
        antigo = cache.get(str(item.get("chave")))
        if antigo and antigo.get("impressao") == imp[n] and not antigo.get("resultado", {}).get("erro"):
            resultados[n] = antigo["resultado"]
        else:
            pendentes.append(n)
    if pendentes:
        if cliente is None:
            cliente, motivo = criar_cliente(SCHEMA_SAIDA, "acao_sugerida", raiz)
            if cliente is None:
                for n in pendentes:
                    resultados[n] = _com_erro(itens[n], motivo)
                pendentes = []
        if pendentes:
            with ThreadPoolExecutor(max_workers=max(1, int(max_paralelo))) as ex:
                futuros = {n: ex.submit(sugerir, itens[n], contexto, destinos[n], cliente=cliente) for n in pendentes}
                for n, f in futuros.items():
                    resultados[n] = f.result()
    if cache_arq:
        novo = {str(i.get("chave")): {"impressao": imp[n], "resultado": resultados[n]}
                for n, i in enumerate(itens) if resultados[n] and not resultados[n].get("erro")}
        try:
            cache_arq.parent.mkdir(parents=True, exist_ok=True)
            cache_arq.write_text(json.dumps({**cache, **novo}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
    return resultados
