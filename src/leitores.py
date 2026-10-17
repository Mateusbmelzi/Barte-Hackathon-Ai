"""Leitores: um por arquivo de origem. Leem os arquivos COMO VÊM (sem limpeza manual,
sem alterar nada no disco). Devolvem listas de dicts com Decimal para dinheiro."""
import csv
import email
import io
import re
import unicodedata
from datetime import date, datetime
from email import policy
from pathlib import Path

import openpyxl

from . import config
from .dinheiro import dec


# ---------------------------------------------------------------- utilidades
def _sem_acento(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _data_br(s):
    s = (s or "").strip()
    return datetime.strptime(s, "%d/%m/%Y").date() if s else None


def _so_digitos(s, tamanho=14):
    if s is None:
        return None
    if isinstance(s, float):
        s = int(s)
    d = re.sub(r"\D", "", str(s))
    return d.zfill(tamanho) if d else None  # CNPJ numérico perde zero à esquerda (doc §2.1)


def _decodificar(raw, preferidos):
    for enc in preferidos:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("encoding não reconhecido")


def descobrir_arquivos(pasta):
    """Acha cada fonte por padrão de nome (config.PADROES_ARQUIVOS).
    Fontes comuns: exatamente 1 arquivo (Path). Fontes em config.FONTES_MULTIPLAS (Orbe): 1 ou mais,
    devolvidas como lista de Path em ordem de nome (a Orbe pode mandar arquivos de ajuste no mês)."""
    pasta = Path(pasta)
    achados, erros = {}, []
    todos = [p for p in pasta.iterdir() if p.is_file()]
    for chave, padrao in config.PADROES_ARQUIVOS.items():
        rx = re.compile(_glob_para_regex(padrao), re.IGNORECASE)
        m = sorted((p for p in todos if rx.fullmatch(p.name)), key=lambda p: p.name.lower())
        if chave in config.FONTES_MULTIPLAS:
            if not m:
                erros.append(f"{chave}: esperado 1 ou mais arquivos '{padrao}' em {pasta}, achei nenhum")
            else:
                achados[chave] = m
        elif len(m) != 1:
            erros.append(f"{chave}: esperado 1 arquivo '{padrao}' em {pasta}, achei {[p.name for p in m]}")
        else:
            achados[chave] = m[0]
    if erros:
        raise FileNotFoundError("\n".join(erros))
    return achados


def achatar(arquivos):
    """Resultado de descobrir_arquivos -> lista simples de Path (as fontes múltiplas viram vários itens)."""
    return [p for v in arquivos.values() for p in (v if isinstance(v, list) else [v])]


def _glob_para_regex(padrao):
    return "".join(".*" if c == "*" else re.escape(c) for c in padrao)


# ---------------------------------------------------------------- 01 Orbe
def ler_orbe(caminho):
    texto = _decodificar(Path(caminho).read_bytes(), ["utf-8-sig", "cp1252"])
    linhas = []
    leitor = csv.DictReader(io.StringIO(texto, newline=""), delimiter=";")
    for n, r in enumerate(leitor, start=2):  # linha física (1 = cabeçalho)
        if not (r.get("id_transacao") or "").strip():
            continue
        parc = (r["qtd_parcelas"] or "").strip()
        linhas.append({
            "id": r["id_transacao"].strip(),
            "linha": n,
            "arquivo": Path(caminho).name,
            "data": _data_br(r["data_movimento"]),
            "ec": r["cod_estabelecimento"].strip(),
            "nome": r["nome_estabelecimento"].strip(),
            "tipo": r["tipo_lancamento"].strip().upper(),
            "modalidade": (r["modalidade"] or "").strip().upper(),
            "parcelas": int(parc) if parc else None,
            "bandeira": (r["bandeira"] or "").strip(),
            "bruto": dec(r["valor_bruto"]),
            "taxa_aplicada": dec(r["taxa_aplicada_pct"]),
            "valor_taxa": dec(r["valor_taxa"]),
            "liquido": dec(r["valor_liquido"]),
            "id_ref": (r["id_referencia"] or "").strip() or None,
            "data_orig": _data_br(r["data_venda_original"]),
        })
    return linhas


_CAMPOS_DUP = ("data", "ec", "tipo", "modalidade", "parcelas", "bruto", "taxa_aplicada", "valor_taxa", "liquido", "id_ref")


def ler_orbe_varios(caminhos):
    """Lê 1 ou N arquivos Orbe (em ordem de nome), concatena e remove repetições de id_transacao.
    Cada linha leva 'arquivo' (nome) e 'linha' (linha física nele). Devolve (linhas, duplicadas):
    a 1ª ocorrência do id vale; as demais (entre arquivos ou no mesmo) vão para 'duplicadas' com
    'original' (a linha mantida) e 'identica' (mesmos valores?). Nunca contam em dobro."""
    if isinstance(caminhos, (str, Path)):
        caminhos = [caminhos]
    vistos, linhas, duplicadas = {}, [], []
    for c in sorted(map(Path, caminhos), key=lambda p: p.name.lower()):
        for l in ler_orbe(c):
            o = vistos.get(l["id"])
            if o is None:
                vistos[l["id"]] = l
                linhas.append(l)
            else:
                duplicadas.append({**l, "original": o,
                                   "identica": all(l[k] == o[k] for k in _CAMPOS_DUP)})
    return linhas, duplicadas


# ---------------------------------------------------------------- 02 planilha de taxas
_COLS_TAXAS = {
    "lojista": "lojista", "cnpj": "cnpj", "ec orbe": "ec",
    "debito": "DEBITO", "credito a vista": "CREDITO A VISTA", "cred. 2-6x": "PARC_2_6",
    "cred. 7-12x": "PARC_7_12", "pix": "PIX", "antecipacao": "ANTECIPACAO",
    "spread remessa": "spread", "vigencia": "vigencia", "obs": "obs",
}
FAIXAS = ["DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX", "ANTECIPACAO"]


def _pct(v):
    """Taxa da planilha -> Decimal em % (2.69). Aceita fração (0,0269) ou texto '2,69%'."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if isinstance(v, (int, float)):
        return dec(v) * 100
    m = re.fullmatch(r"\s*([\d.,]+)\s*%?\s*", str(v))
    if not m:
        raise ValueError(f"taxa não numérica: {v!r}")
    x = dec(m.group(1))
    return x if "%" in str(v) or x >= 1 else x * 100


def _spread(v):
    """Spread contratado como fração. Branco/'padrão' -> None (= padrão, CC03)."""
    if v is None or (isinstance(v, str) and _sem_acento(v) in ("", "padrao")):
        return None
    return _pct(v) / 100


def _vigencia(v):
    """Texto de vigência -> (inicio, fim, ok). H05: formato não reconhecido -> ok=False."""
    if isinstance(v, datetime):
        return v.date(), None, True
    s = _sem_acento(v or "")
    m = re.fullmatch(r"(?:a partir de\s*)?(\d{2}/\d{2}/\d{4})", s)
    if m:
        return _data_br(m.group(1)), None, True
    m = re.fullmatch(r"ate\s*(\d{2}/\d{2}/\d{4})", s)
    if m:
        return None, _data_br(m.group(1)), True
    return None, None, False


def ler_taxas(caminho):
    wb = openpyxl.load_workbook(caminho, data_only=True)
    abas = [n for n in wb.sheetnames if "vigente" in _sem_acento(n)]
    if len(abas) != 1:
        raise ValueError(f"planilha de taxas: esperada 1 aba 'vigentes', achei {wb.sheetnames}")
    ws = wb[abas[0]]
    cab_linha, mapa = None, {}
    for row in ws.iter_rows():
        if row[0].value and _sem_acento(row[0].value) == "lojista":
            cab_linha = row[0].row
            for c in row:
                if c.value is not None and _sem_acento(c.value) in _COLS_TAXAS:
                    mapa[_COLS_TAXAS[_sem_acento(c.value)]] = c.column
            break
    if cab_linha is None:
        raise ValueError("planilha de taxas: cabeçalho 'Lojista' não encontrado")
    contratos = []
    for r in range(cab_linha + 1, ws.max_row + 1):
        lojista = ws.cell(r, mapa["lojista"]).value
        cnpj = ws.cell(r, mapa["cnpj"]).value
        if not lojista or cnpj is None:
            continue  # linhas de nota de rodapé ("* spread em branco = padrão")
        val = lambda k: ws.cell(r, mapa[k]).value
        ec = val("ec")
        inicio, fim, ok = _vigencia(val("vigencia"))
        contratos.append({
            "linha": r,
            "lojista": str(lojista).strip(),
            "cnpj": _so_digitos(cnpj),
            "ec": str(int(ec)) if isinstance(ec, (int, float)) else (str(ec).strip() if ec else None),
            "taxas": {f: _pct(val(f)) for f in FAIXAS},
            "spread": _spread(val("spread")),
            "spread_bruto": val("spread"),
            "vigencia_texto": val("vigencia"),
            "inicio": inicio, "fim": fim, "vigencia_ok": ok,
            "obs": val("obs"),
            "riscado": bool(ws.cell(r, mapa["lojista"]).font.strike),  # linha riscada = inativa
        })
    return contratos


_COLS_ANTIGAS = {"lojista": "lojista", "cnpj": "cnpj", "debito": ["DEBITO"], "credito a vista": ["CREDITO A VISTA"],
                 "cred. parcelado": ["PARC_2_6", "PARC_7_12"], "pix": ["PIX"]}


def ler_taxas_antigas(caminho):
    """Abas que NÃO são a vigente (ex.: 'ANTIGO 2025 - nao usar'). Usadas só como FATO no dossiê de
    investigação (taxa aplicada coincide com tabela antiga?), nunca para calcular comissão.
    'Créd. parcelado' vale para as duas faixas de parcelas."""
    wb = openpyxl.load_workbook(caminho, data_only=True)
    out = []
    for nome in wb.sheetnames:
        if "vigente" in _sem_acento(nome):
            continue
        ws = wb[nome]
        mapa = None
        for row in ws.iter_rows():
            if mapa is None:
                if row[0].value and _sem_acento(row[0].value) == "lojista":
                    mapa = {_sem_acento(c.value): c.column for c in row
                            if c.value is not None and _sem_acento(c.value) in _COLS_ANTIGAS}
                continue
            val = {k: ws.cell(row[0].row, c).value for k, c in mapa.items()}
            if not val.get("lojista") or val.get("cnpj") is None:
                continue
            taxas = {}
            for k, faixas in _COLS_ANTIGAS.items():
                if isinstance(faixas, list) and k in val:
                    for f in faixas:
                        taxas[f] = _pct(val[k])
            out.append({"aba": nome, "linha": row[0].row, "lojista": str(val["lojista"]).strip(),
                        "cnpj": _so_digitos(val["cnpj"]), "taxas": taxas})
    return out


# ---------------------------------------------------------------- 03 e-mail Ponte (anexo em memória)
_COLS_PONTE = {
    "no operacao": "op", "data contratacao": "data", "data liquidacao": "data_liq",
    "cnpj cliente": "cnpj", "cliente": "cliente", "moeda": "moeda", "valor me": "valor_me",
    "taxa cliente": "taxa_cliente", "ptax ref.": "ptax", "valor r$": "valor_brl",
    "spread r$": "spread_brl", "spread %": "spread_pct", "spread estimado r$ (d-1)": "spread_estimado",
    "iof r$": "iof", "status compliance": "status", "observacao": "obs",
}
_NUM_PONTE = ["valor_me", "taxa_cliente", "ptax", "valor_brl", "spread_brl", "spread_pct", "spread_estimado", "iof"]


def ler_ponte(caminho):
    """Lê o .eml, extrai o anexo .xlsx em memória e devolve (operações, metadados)."""
    with open(caminho, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    anexo = None
    for parte in msg.iter_attachments():
        nome = parte.get_filename() or ""
        if nome.lower().endswith(".xlsx"):
            anexo = (nome, parte.get_payload(decode=True))
            break
    if anexo is None:
        raise ValueError("e-mail da Ponte sem anexo .xlsx")
    corpo = msg.get_body(("plain",))
    texto = corpo.get_content() if corpo else ""
    m = re.search(r"creditado em (\d{2}/\d{2}/\d{4})", texto)
    meta = {
        "anexo": anexo[0],
        "assunto": str(msg["subject"]),
        "data_repasse": _data_br(m.group(1)) if m else None,
    }
    wb = openpyxl.load_workbook(io.BytesIO(anexo[1]), data_only=True)
    ws = wb[wb.sheetnames[0]] if "Operações" not in wb.sheetnames else wb["Operações"]
    cab, mapa = None, {}
    for row in ws.iter_rows():
        if row[0].value and _sem_acento(row[0].value).replace("º", "o") in ("no operacao", "n operacao"):
            cab = row[0].row
            for c in row:
                k = _sem_acento(c.value).replace("º", "o") if c.value else None
                if k in _COLS_PONTE:
                    mapa[_COLS_PONTE[k]] = c.column
            break
    if cab is None:
        raise ValueError("relatório Ponte: cabeçalho 'Nº Operação' não encontrado")
    ops = []
    for r in range(cab + 1, ws.max_row + 1):
        d = ws.cell(r, mapa["data"]).value
        op = ws.cell(r, mapa["op"]).value
        if not op or not isinstance(d, datetime):
            continue  # linhas vazias e rodapé ("Total de operações:")
        o = {k: ws.cell(r, c).value for k, c in mapa.items()}
        o["op"] = str(op).strip()
        o["linha_excel"] = r
        o["data"] = d.date()
        o["data_liq"] = o["data_liq"].date() if isinstance(o.get("data_liq"), datetime) else None
        o["cnpj"] = _so_digitos(o["cnpj"])
        for k in _NUM_PONTE:
            o[k] = dec(o[k])
        o["obs"] = o.get("obs") or ""
        ops.append(o)
    return ops, meta


# ---------------------------------------------------------------- 04 plano de contas
def ler_plano(caminho):
    texto = _decodificar(Path(caminho).read_bytes(), ["utf-8-sig", "cp1252"])
    plano = {}
    for r in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        cod = (r.get("COD_CONTA") or "").strip()
        if cod:
            plano[cod] = {
                "descricao": r["DESCRICAO"].strip(),
                "tipo": r["TIPO"].strip(),
                "aceita": r["ACEITA_LANCTO"].strip().upper() == "S",
            }
    return plano


# ---------------------------------------------------------------- 05a Aurora (CSV)
def ler_aurora(caminho):
    """ref_origem = 'L' + número da linha física do arquivo (1ª linha = L1)."""
    texto = _decodificar(Path(caminho).read_bytes(), ["utf-8-sig", "cp1252"])
    movs, saldo_ini, saldo_fim = [], None, None
    for n, bruta in enumerate(texto.split("\n"), start=1):
        campos = bruta.rstrip("\r").split(";")
        campos += [""] * (5 - len(campos))
        data_s, desc, doc, valor_s, saldo_s = (c.strip() for c in campos[:5])
        desc_n = _sem_acento(desc)
        if desc_n == "saldo anterior":
            saldo_ini = dec(saldo_s)
        elif desc_n == "saldo final":
            saldo_fim = dec(saldo_s)
        elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", data_s) and valor_s:
            movs.append({
                "ref": f"L{n}", "linha": n, "data": _data_br(data_s), "descricao": desc,
                "documento": doc, "valor": dec(valor_s), "saldo": dec(saldo_s),
            })
    return movs, {"saldo_anterior": saldo_ini, "saldo_final": saldo_fim}


# ---------------------------------------------------------------- 05b Meridiano (OFX SGML)
def ler_meridiano(caminho):
    raw = Path(caminho).read_bytes()
    m = re.search(rb"CHARSET:(\d+)", raw)
    enc = f"cp{m.group(1).decode()}" if m else "cp1252"
    texto = raw.decode(enc)
    movs = []
    for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, re.S):
        t = dict(re.findall(r"<([A-Z0-9.]+)>([^\r\n<]*)", bloco))
        movs.append({
            "ref": t["FITID"].strip(), "data": datetime.strptime(t["DTPOSTED"][:8], "%Y%m%d").date(),
            "tipo": t.get("TRNTYPE", "").strip(), "valor": dec(t["TRNAMT"].strip()),
            "checknum": t.get("CHECKNUM", "").strip(), "descricao": t.get("MEMO", "").strip(),
        })
    lb = re.search(r"<LEDGERBAL>\s*<BALAMT>([^\r\n<]+)", texto)
    return movs, {"saldo_final": dec(lb.group(1).strip()) if lb else None}


def ler_tudo(pasta):
    arq = descobrir_arquivos(pasta)
    ponte, meta_ponte = ler_ponte(arq["ponte"])
    aurora, meta_aurora = ler_aurora(arq["aurora"])
    meridiano, meta_mer = ler_meridiano(arq["meridiano"])
    orbe, orbe_dup = ler_orbe_varios(arq["orbe"])
    arquivos = {k: v.name for k, v in arq.items() if k != "orbe"}
    arquivos["orbe"] = ", ".join(p.name for p in arq["orbe"])
    return {
        "arquivos": arquivos,
        "arquivos_orbe": [p.name for p in arq["orbe"]],
        "orbe": orbe, "orbe_duplicadas": orbe_dup,
        "contratos": ler_taxas(arq["taxas"]),
        "ponte": ponte, "meta_ponte": meta_ponte,
        "plano": ler_plano(arq["plano"]),
        "aurora": aurora, "meta_aurora": meta_aurora,
        "meridiano": meridiano, "meta_meridiano": meta_mer,
    }
