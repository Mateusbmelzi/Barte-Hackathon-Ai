"""Leitura de contrato com IA: texto do contrato -> taxas, condições especiais, regras de negócio e ações sugeridas.

Fluxo (cliente novo detectado em `src.clientes_novos`):
1. `ler_texto` extrai o texto de .txt/.md/.docx/.pdf (só biblioteca padrão; PDF usa pypdf/pdfminer se instalados).
2. `extrair` pede à IA (mesmo modelo e provedores de `src.ia`) uma saída estruturada e aplica GUARDA-CORPOS em código:
   - toda `evidencia` tem de ser trecho literal do contrato (comparação sem acento/caixa/espaços), senão o item sai;
   - todo valor numérico (taxa/percentual) tem de aparecer no contrato, senão o item sai;
   - faixa, tipo, assunto ou destino fora do enum: o item sai; destinos só os de `config.CONTRATO_DESTINOS`;
   - e-mails: percentuais e R$ só os extraídos; sem prometer pagamento/crédito nem dizer que algo já foi feito;
     corpo até `config.CONTRATO_MAX_CORPO`;
   - a IA nunca preenche aprovação (não existe esse campo); sem taxa/cláusula nenhuma, o texto "não é contrato"
     e só `duvidas` volta.
   Tudo que saiu vai para `ajustes`.
3. `para_cadastro` converte a extração em condições do cadastro (TAXA_ESPECIAL/ISENCAO) para a prévia. NUNCA grava:
   o servidor grava com `cadastro.adicionar_varias`, depois que a analista aprova.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src import cadastro, config, ia, ia_acoes
from src.ia_acoes import sem_acento

AVISO = "Extração da IA a partir do contrato — revise antes de confirmar"
VERSAO_PROMPT = "contrato-v1"
FAIXAS = ["DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX", "ANTECIPACAO", "SPREAD_REMESSA"]
TIPOS_CONDICAO = ["ISENCAO", "TAXA_ESPECIAL", "OUTRA"]
ASSUNTOS = ["FATURAMENTO", "REPASSE", "ANTECIPACAO", "ESTORNO", "MULTA", "REAJUSTE", "PRAZO", "OUTRA"]
DESTINOS = list(config.CONTRATO_DESTINOS)
MAX_ASSUNTO = 90
MIN_EVIDENCIA = 6
ASSINATURA_PADRAO = ia_acoes.ASSINATURA_PADRAO

_S = {"type": "string"}


def _lista(item):
    return {"type": "array", "items": item}


def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


SCHEMA_SAIDA = _obj({
    "partes": _obj({"lojista": _S, "cnpj": _S}),
    "vigencia_inicio": _S,
    "vigencia_fim": _S,
    "taxas": _lista(_obj({"faixa": {"type": "string", "enum": FAIXAS}, "valor": _S, "evidencia": _S})),
    "condicoes_especiais": _lista(_obj({
        "tipo": {"type": "string", "enum": TIPOS_CONDICAO}, "descricao": _S,
        "faixas": _lista({"type": "string", "enum": FAIXAS}), "valor": _S, "inicio": _S, "fim": _S,
        "evidencia": _S})),
    "regras_negocio": _lista(_obj({"assunto": {"type": "string", "enum": ASSUNTOS}, "texto": _S, "evidencia": _S})),
    "acoes_sugeridas": _lista(_obj({"destino": {"type": "string", "enum": DESTINOS}, "motivo": _S,
                                    "assunto": _S, "corpo": _S})),
    "duvidas": _lista(_S),
})


# ---------------------------------------------------------------- texto do contrato
def _limitar(texto: str) -> tuple[str, str]:
    lim = config.CONTRATO_LIMITE_CHARS
    if len(texto) <= lim:
        return texto, ""
    return texto[:lim], (f"Contrato truncado: só os primeiros {lim:,} de {len(texto):,} caracteres foram lidos "
                         "(o restante não foi analisado).").replace(",", ".")


def _decodificar(b: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1", errors="replace")


def _texto_docx(b: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab\s*/>", "\t", xml)
    xml = re.sub(r"<w:br\s*/>", "\n", xml)
    xml = re.sub(r"</w:tc>", "\t", xml)
    texto = re.sub(r"<[^>]+>", "", xml)
    for a, b2 in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
        texto = texto.replace(a, b2)
    return texto


_ERRO_PDF = "não consegui ler o PDF; envie .docx/.txt ou instale pypdf"


def _texto_pdf(b: bytes) -> str:
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(b)).pages)
    except ImportError:
        pass
    except Exception:  # noqa: BLE001 - PDF corrompido/protegido: tenta o próximo método
        pass
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(b))
    except Exception:  # noqa: BLE001
        pass
    # extração simples: textos entre parênteses dos operadores Tj/TJ de streams sem filtro (ou Flate)
    import zlib
    partes = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", b, re.S):
        dados = m.group(1)
        try:
            dados = zlib.decompress(dados)
        except Exception:  # noqa: BLE001
            pass
        for t in re.findall(rb"\(((?:\\.|[^\\()])*)\)\s*T[jJ]", dados):
            partes.append(t.decode("latin-1", errors="replace").replace("\\(", "(").replace("\\)", ")"))
    return "\n".join(partes)


def ler_texto(caminho_ou_bytes, nome: str = "") -> str:
    """Texto do contrato. `caminho_ou_bytes` = caminho do arquivo ou os bytes do upload; `nome` define o formato
    (extensão). Limite de `config.CONTRATO_LIMITE_CHARS` caracteres: se passar, o texto vem cortado e termina com
    um aviso. Levanta ValueError com mensagem legível (formato desconhecido, arquivo ilegível); nunca outro tipo."""
    if isinstance(caminho_ou_bytes, (bytes, bytearray)):
        dados = bytes(caminho_ou_bytes)
    else:
        p = Path(caminho_ou_bytes)
        nome = nome or p.name
        try:
            dados = p.read_bytes()
        except OSError as exc:
            raise ValueError(f"não consegui abrir o arquivo do contrato ({exc.__class__.__name__}).") from None
    ext = Path(nome or "").suffix.lower()
    try:
        if ext in (".txt", ".md", ".text", ""):
            texto = _decodificar(dados)
        elif ext == ".docx":
            texto = _texto_docx(dados)
        elif ext == ".pdf":
            texto = _texto_pdf(dados)
            if len(texto.strip()) < 20:
                raise ValueError(_ERRO_PDF + " (PDF escaneado ou sem texto selecionável).")
        else:
            raise ValueError(f"formato {ext or 'desconhecido'} não suportado; envie .docx, .pdf, .txt ou .md.")
    except ValueError:
        raise
    except (zipfile.BadZipFile, KeyError):
        raise ValueError("não consegui ler o .docx (arquivo corrompido ou não é Word); envie .txt ou .pdf.") from None
    except Exception:  # noqa: BLE001
        raise ValueError("não consegui ler o arquivo do contrato; envie .docx ou .txt.") from None
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    cortado, aviso = _limitar(texto)
    return cortado + (f"\n\n[{aviso}]" if aviso else "")


# ---------------------------------------------------------------- normalização e conferência
def _norm(t) -> str:
    return " ".join(sem_acento(str(t or "")).split())


_RE_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def _numeros(texto: str) -> set[Decimal]:
    """Todos os números do texto (vírgula ou ponto decimal; milhar com ponto/vírgula também lido sem separador)."""
    out = set()
    for m in _RE_NUM.findall(texto or ""):
        for cand in {m.replace(",", "."), m.replace(".", "").replace(",", "."), m.replace(",", "")}:
            try:
                out.add(Decimal(cand).normalize())
            except InvalidOperation:
                pass
    return out


def _dec(v) -> Decimal | None:
    try:
        return Decimal(str(v).strip().replace("%", "").replace(",", ".")).normalize()
    except InvalidOperation:
        return None


MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]


def _data_no_texto(iso: str, texto_norm: str) -> bool:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return False
    a, mes, d = m.group(1), int(m.group(2)), int(m.group(3))
    if not 1 <= mes <= 12 or not 1 <= d <= 31:
        return False
    formas = [f"{d:02d}/{mes:02d}/{a}", f"{d}/{mes}/{a}", f"{a}-{mes:02d}-{d:02d}", f"{d:02d}.{mes:02d}.{a}",
              f"{d} de {MESES[mes - 1]} de {a}", f"{d:02d} de {MESES[mes - 1]} de {a}",
              f"{d}o de {MESES[mes - 1]} de {a}", f"{d}º de {MESES[mes - 1]} de {a}"]
    return any(f in texto_norm for f in formas)


def _data_valida(iso, texto_norm, onde, ajustes) -> str:
    iso = str(iso or "").strip()
    if not iso:
        return ""
    if not _data_no_texto(iso, texto_norm):
        ajustes.append(f"{onde} '{iso}' descartada: a data não aparece no contrato")
        return ""
    return iso


def _evidencia_ok(ev, texto_norm) -> bool:
    n = _norm(ev)
    return len(n) >= MIN_EVIDENCIA and n in texto_norm


# ---------------------------------------------------------------- guarda-corpos
def _fmt_pct(v: Decimal) -> str:
    return format(v, "f").replace(".", ",")


def validar(bruto: dict, texto: str, cliente: dict | None = None, contexto: dict | None = None) -> dict:
    """Aplica os guarda-corpos à resposta do modelo e devolve o resultado final (sem rede)."""
    contexto = dict(contexto or {})
    assinatura = contexto.get("assinatura") or ASSINATURA_PADRAO
    cliente = cliente or {}
    bruto = bruto if isinstance(bruto, dict) else {}
    tn = _norm(texto)
    nums = _numeros(texto)
    ajustes: list[str] = []
    duvidas = [" ".join(str(d).split()) for d in (bruto.get("duvidas") or []) if str(d).strip()]

    # taxas
    taxas, vistos = [], set()
    for t in bruto.get("taxas") or []:
        if not isinstance(t, dict):
            continue
        faixa, ev = str(t.get("faixa") or ""), t.get("evidencia")
        if faixa not in FAIXAS:
            ajustes.append(f"taxa removida: faixa '{faixa}' fora da lista permitida")
            continue
        v = _dec(t.get("valor"))
        if v is None or v < 0 or v > 100:
            ajustes.append(f"taxa {faixa} removida: valor '{t.get('valor')}' inválido")
            continue
        if v not in nums:
            ajustes.append(f"taxa {faixa} removida: o valor {t.get('valor')} não aparece no contrato")
            continue
        if not _evidencia_ok(ev, tn):
            ajustes.append(f"taxa {faixa} removida: a evidência não é um trecho literal do contrato")
            continue
        if faixa in vistos:
            ajustes.append(f"taxa {faixa} repetida removida (mantida a primeira)")
            continue
        vistos.add(faixa)
        taxas.append({"faixa": faixa, "valor": format(v, "f"), "evidencia": " ".join(str(ev).split())})

    # condições especiais
    condicoes = []
    for c in bruto.get("condicoes_especiais") or []:
        if not isinstance(c, dict):
            continue
        tipo = str(c.get("tipo") or "")
        if tipo not in TIPOS_CONDICAO:
            ajustes.append(f"condição removida: tipo '{tipo}' fora da lista permitida")
            continue
        if not _evidencia_ok(c.get("evidencia"), tn):
            ajustes.append(f"condição {tipo} removida: a evidência não é um trecho literal do contrato")
            continue
        faixas = []
        for f in c.get("faixas") or []:
            if f in FAIXAS:
                faixas.append(f)
            else:
                ajustes.append(f"faixa '{f}' removida de uma condição {tipo}: fora da lista permitida")
        valor = str(c.get("valor") or "").strip()
        if valor:
            v = _dec(valor)
            if v is None or v not in nums:
                ajustes.append(f"condição {tipo} removida: o valor {valor} não aparece no contrato")
                continue
            valor = format(v, "f")
        if tipo == "TAXA_ESPECIAL" and not (valor and faixas):
            ajustes.append("condição TAXA_ESPECIAL removida: falta valor ou faixa")
            continue
        condicoes.append({
            "tipo": tipo, "descricao": " ".join(str(c.get("descricao") or "").split()), "faixas": faixas,
            "valor": valor, "inicio": _data_valida(c.get("inicio"), tn, "data de início", ajustes),
            "fim": _data_valida(c.get("fim"), tn, "data de fim", ajustes),
            "evidencia": " ".join(str(c.get("evidencia")).split())})

    # regras de negócio
    regras = []
    for r in bruto.get("regras_negocio") or []:
        if not isinstance(r, dict):
            continue
        assunto = str(r.get("assunto") or "")
        if assunto not in ASSUNTOS:
            ajustes.append(f"regra removida: assunto '{assunto}' fora da lista permitida")
            continue
        if not _evidencia_ok(r.get("evidencia"), tn):
            ajustes.append(f"regra de {assunto} removida: a evidência não é um trecho literal do contrato")
            continue
        regras.append({"assunto": assunto, "texto": " ".join(str(r.get("texto") or "").split()),
                       "evidencia": " ".join(str(r.get("evidencia")).split())})

    # partes
    p = bruto.get("partes") if isinstance(bruto.get("partes"), dict) else {}
    cnpj_c = re.sub(r"\D", "", str(p.get("cnpj") or ""))
    if cnpj_c and cnpj_c not in re.sub(r"\D", "", texto):
        ajustes.append(f"CNPJ {cnpj_c} da parte descartado: não aparece no contrato")
        cnpj_c = ""
    lojista = " ".join(str(p.get("lojista") or "").split())
    if lojista and _norm(lojista) not in tn:
        ajustes.append(f"nome do lojista '{lojista}' descartado: não aparece no contrato")
        lojista = ""
    cnpj_cli = re.sub(r"\D", "", str(cliente.get("cnpj") or ""))
    if cnpj_c and cnpj_cli and cnpj_c != cnpj_cli:
        duvidas.append(f"O CNPJ do contrato ({cnpj_c}) é diferente do CNPJ do cliente no fechamento ({cnpj_cli}). "
                       "Confirme que é o contrato do cliente certo.")
    vi = _data_valida(bruto.get("vigencia_inicio"), tn, "vigência inicial", ajustes)
    vf = _data_valida(bruto.get("vigencia_fim"), tn, "vigência final", ajustes)

    # "não parece contrato": nada extraído e nenhuma dúvida da IA sobre o conteúdo
    if not taxas and not condicoes and not regras:
        duvidas.append("O texto enviado não parece conter taxas nem cláusulas de um contrato (nada pôde ser "
                       "extraído com evidência). Confira se o arquivo é o contrato correto e se o texto foi lido por inteiro.")
        return _resultado(duvidas=duvidas, ajustes=ajustes, partes={"lojista": lojista, "cnpj": cnpj_c})

    # ações sugeridas
    pcts_ok = {_dec(t["valor"]) for t in taxas} | {_dec(c["valor"]) for c in condicoes if c["valor"]}
    pcts_ok.discard(None)
    reais_ok = set()
    for it in taxas + condicoes + regras:
        reais_ok.update(ia_acoes.valores_reais(json.dumps(it, ensure_ascii=False)))
    acoes = []
    for a in bruto.get("acoes_sugeridas") or []:
        if not isinstance(a, dict):
            continue
        destino = str(a.get("destino") or "")
        if destino not in DESTINOS:
            ajustes.append(f"ação para '{destino or '(sem destino)'}' removida: destino fora dos permitidos")
            continue
        assunto = _padrao_br(" ".join(str(a.get("assunto") or "").split()))
        corpo = _padrao_br(str(a.get("corpo") or "").strip())
        motivo = _padrao_br(" ".join(str(a.get("motivo") or "").split()))
        if not assunto or not corpo:
            ajustes.append(f"ação para {destino} removida: assunto ou corpo vazio")
            continue
        if assinatura and assinatura not in corpo:
            corpo = f"{corpo}\n\n{assinatura}"
        problema = ia_acoes._problema_texto(assunto + "\n" + corpo, reais_ok, pcts=pcts_ok)
        if problema:
            ajustes.append(f"ação para {destino} removida: {problema}")
            continue
        if len(corpo) > config.CONTRATO_MAX_CORPO:
            ajustes.append(f"ação para {destino} removida: corpo com {len(corpo)} caracteres "
                           f"(máx. {config.CONTRATO_MAX_CORPO})")
            continue
        if len(assunto) > MAX_ASSUNTO:
            assunto = assunto[:MAX_ASSUNTO - 1].rstrip() + "…"
            ajustes.append(f"assunto da ação para {destino} cortado em {MAX_ASSUNTO} caracteres")
        acoes.append({"destino": destino, "motivo": motivo, "assunto": assunto, "corpo": corpo})

    return _resultado(partes={"lojista": lojista, "cnpj": cnpj_c}, vigencia_inicio=vi, vigencia_fim=vf, taxas=taxas,
                      condicoes_especiais=condicoes, regras_negocio=regras, acoes_sugeridas=acoes,
                      duvidas=duvidas, ajustes=ajustes)


_RE_PCT_PONTO = re.compile(r"(\d+)\.(\d+)(\s*%)")
_RE_REAIS_PONTO = re.compile(r"R\$\s*(\d+)\.(\d{1,2})(?!\d)")


def _padrao_br(texto: str) -> str:
    """Números no padrão brasileiro: 1.59% -> 1,59%; R$ 15396.77 -> R$ 15.396,77 (a comparação do guarda-corpo é numérica)."""
    texto = _RE_PCT_PONTO.sub(lambda m: f"{m.group(1)},{m.group(2)}{m.group(3)}", str(texto or ""))

    def reais(m):
        v = Decimal(f"{m.group(1)}.{m.group(2)}")
        return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return _RE_REAIS_PONTO.sub(reais, texto)


def _resultado(**kw) -> dict:
    base = {"partes": {"lojista": "", "cnpj": ""}, "vigencia_inicio": "", "vigencia_fim": "", "taxas": [],
            "condicoes_especiais": [], "regras_negocio": [], "acoes_sugeridas": [], "duvidas": [],
            "aviso": AVISO, "modelo": ia.MODELO, "versao_prompt": VERSAO_PROMPT, "ajustes": [], "erro": ""}
    base.update(kw)
    return base


# ---------------------------------------------------------------- prompt e execução
def versao_prompt() -> str:
    m = re.search(r"versao:\s*([\w.\-]+)", ia._ler_prompt("contrato.md"))
    return m.group(1) if m else VERSAO_PROMPT


def montar_system() -> str:
    return ia._ler_prompt("contexto_tarvo.md").strip() + "\n\n---\n\n" + ia._ler_prompt("contrato.md").strip()


def montar_mensagem(texto: str, cliente: dict, contexto: dict) -> str:
    contexto = dict(contexto or {})
    contexto.setdefault("empresa", ia_acoes.EMPRESA_PADRAO)
    contexto.setdefault("assinatura", ASSINATURA_PADRAO)
    dados = {
        "cliente": {k: cliente.get(k) for k in ("nome", "cnpj", "ec_orbe", "origem") if cliente.get(k)},
        "contexto": {k: v for k, v in contexto.items() if k in ("competencia", "empresa", "assinatura", "contatos")},
        "destinos_permitidos": DESTINOS,
        "contrato": texto,
    }
    return ("Contrato do cliente novo para extrair (JSON):\n\n" + json.dumps(dados, ensure_ascii=False, indent=2)
            + "\n\nResponda no formato pedido, só com o que está escrito no contrato.")


def extrair(texto: str, cliente: dict, contexto: dict | None = None, *, cliente_ia=None, raiz: Path | None = None) -> dict:
    """Extrai taxas, condições, regras e ações do contrato. Nunca levanta exceção por falta de chave, biblioteca ou
    erro da API: o resultado traz `erro` legível. `cliente_ia` = cliente com `gerar(system, mensagem)` (injetável nos
    testes); sem ele, usa o provedor configurado em `src.ia`."""
    cliente, contexto = dict(cliente or {}), dict(contexto or {})
    texto = str(texto or "")
    if len(texto.strip()) < 20:
        return _resultado(duvidas=["O contrato está vazio ou quase vazio; envie o arquivo de novo."],
                          erro="")
    texto, aviso_trunc = _limitar(texto)
    if cliente_ia is None:
        cliente_ia, motivo = ia_acoes.criar_cliente(SCHEMA_SAIDA, "contrato_extracao", raiz)
        if cliente_ia is None:
            return _resultado(erro=f"IA indisponível: {motivo}")
    cliente_ia = ia._como_cliente(cliente_ia)
    modelo = getattr(cliente_ia, "modelo", ia.MODELO)
    try:
        bruto, modelo_resposta = cliente_ia.gerar(montar_system(), montar_mensagem(texto, cliente, contexto))
    except Exception as exc:  # noqa: BLE001
        return _resultado(erro=f"IA indisponível: {ia._mensagem_erro(exc)}", modelo=modelo)
    if not isinstance(bruto, dict):
        return _resultado(erro="IA indisponível: resposta da IA não é um JSON válido.", modelo=modelo)
    r = validar(bruto, texto, cliente, contexto)
    r["modelo"] = modelo_resposta or modelo
    if aviso_trunc:
        r["ajustes"].insert(0, aviso_trunc)
    return r


# ---------------------------------------------------------------- proposta para o cadastro
def _linha_da_faixa(faixa: str) -> str:
    return "REMESSA" if faixa == cadastro.FAIXA_REMESSA else "CHECKOUT"


def para_cadastro(extracao: dict, cliente: dict, aprovado_por: str, usuario: str, pasta_cadastro) -> dict:
    """Converte a extração em condições do cadastro, SEM gravar: cada taxa vira TAXA_ESPECIAL (uma por faixa, linha
    CHECKOUT ou REMESSA, vigência do contrato, fonte 'contrato <arquivo>') e cada ISENCAO extraída vira ISENCAO.
    Exige `aprovado_por` (quem do Comercial aprovou; a IA nunca preenche). Valida com `cadastro.validar`.
    Devolve {"condicoes": [dict no schema do cadastro], "erros": [mensagens]}. O servidor grava com
    `cadastro.adicionar_varias` quando a analista confirma."""
    erros: list[str] = []
    aprovado_por = (aprovado_por or "").strip()
    if not aprovado_por:
        erros.append("Informe quem aprovou as condições (aprovado_por): taxa especial e isenção exigem aprovação do Comercial.")
    cnpj = re.sub(r"\D", "", str((cliente or {}).get("cnpj") or ""))
    ec = re.sub(r"\D", "", str((cliente or {}).get("ec_orbe") or ""))
    if not (cnpj or ec):
        erros.append("Informe o CNPJ ou o EC Orbe do cliente.")
    nome = str((cliente or {}).get("nome") or (extracao.get("partes") or {}).get("lojista") or "").strip()
    arquivo = str((cliente or {}).get("contrato_arquivo") or (extracao or {}).get("arquivo") or "").strip()
    fonte = f"contrato {arquivo}".strip()
    vi, vf = extracao.get("vigencia_inicio") or "", extracao.get("vigencia_fim") or ""
    hoje = _hoje()
    base = {"cnpj": cnpj, "ec_orbe": ec, "lojista": nome, "aprovado_por": aprovado_por, "data_registro": hoje,
            "fonte": fonte}

    condicoes = []
    for t in extracao.get("taxas") or []:
        if not vi:
            erros.append(f"Taxa {t['faixa']}: a vigência inicial do contrato não foi identificada; informe antes de confirmar.")
            continue
        condicoes.append({**base, "tipo": "TAXA_ESPECIAL", "linha_negocio": _linha_da_faixa(t["faixa"]),
                          "campo": t["faixa"], "valor": t["valor"], "vigencia_inicio": vi, "vigencia_fim": vf,
                          "observacao": f"Taxa do contrato (extraída pela IA, confirmada pela analista). Evidência: {t['evidencia']}"[:400]})
    for c in extracao.get("condicoes_especiais") or []:
        ini = c.get("inicio") or vi
        if c["tipo"] == "ISENCAO":
            if not ini:
                erros.append("Isenção sem data de início (nem vigência do contrato); informe antes de confirmar.")
                continue
            faixas = c.get("faixas") or []
            grupos = ([("CHECKOUT", "todas")] if not faixas else
                      [(lin, ",".join(f for f in faixas if _linha_da_faixa(f) == lin))
                       for lin in ("CHECKOUT", "REMESSA") if any(_linha_da_faixa(f) == lin for f in faixas)])
            for lin, campo in grupos:
                condicoes.append({**base, "tipo": "ISENCAO", "linha_negocio": lin, "campo": campo, "valor": "",
                                  "vigencia_inicio": ini, "vigencia_fim": c.get("fim") or "",
                                  "observacao": f"{c.get('descricao') or 'Isenção do contrato'}. Evidência: {c['evidencia']}"[:400]})
        elif c["tipo"] == "TAXA_ESPECIAL":
            if not ini:
                erros.append("Taxa especial sem data de início (nem vigência do contrato); informe antes de confirmar.")
                continue
            for f in c.get("faixas") or []:
                condicoes.append({**base, "tipo": "TAXA_ESPECIAL", "linha_negocio": _linha_da_faixa(f), "campo": f,
                                  "valor": c["valor"], "vigencia_inicio": ini, "vigencia_fim": c.get("fim") or vf,
                                  "observacao": f"{c.get('descricao') or 'Taxa especial do contrato'}. Evidência: {c['evidencia']}"[:400]})
    if not condicoes and not erros:
        erros.append("A extração não tem taxa nem isenção para virar condição do cadastro.")
    if condicoes and aprovado_por:
        erros.extend(str(e) for e in cadastro.validar(condicoes, pasta_cadastro))
    return {"condicoes": condicoes, "erros": erros}


def _hoje() -> str:
    from datetime import date
    return date.today().isoformat()
