"""Cadastro de condições comerciais por cliente (arquivo nosso, versionado, fora da planilha do cliente).

A planilha de taxas do cliente (02_...xlsx) NUNCA é alterada. O cálculo lê a planilha e, por cima, aplica as
condições VIGENTES deste cadastro (isenções, taxas especiais, de-para de EC, bloqueios, notas de pendência).
Regras GERAIS (tolerância, 50%, spread padrão, arredondamento) continuam em src/config.py.

Arquivos (pasta de cadastro, padrão `cadastro/` na raiz do projeto), UTF-8, separador `;`, datas AAAA-MM-DD,
decimal com ponto:
  condicoes_comerciais.csv  - id_condicao;tipo;cnpj;ec_orbe;lojista;linha_negocio;campo;valor;vigencia_inicio;
                              vigencia_fim;aprovado_por;data_registro;fonte;observacao
  historico_alteracoes.csv  - data_hora;usuario;acao;id_condicao;resumo      (acao = CRIAR | ENCERRAR)
O cadastro só cresce: condição errada ou vencida é ENCERRADA (preenche vigencia_fim), nunca apagada.

TIPOS
  ISENCAO               taxa zero. `campo` = faixas separadas por "," ou "todas". Exige aprovado_por.
  TAXA_ESPECIAL         `campo` = UMA faixa; `valor` = taxa em % (2.19 = 2,19%). Exige aprovado_por.
                        Substitui a taxa da planilha naquela faixa e período.
  DE_PARA_EC            liga `ec_orbe` ao `cnpj` da planilha (EC da Orbe que não consta na planilha).
  BLOQUEIO_FATURAMENTO  lojista (ec_orbe e/ou cnpj) não é faturado até confirmar contrato; `observacao` = motivo.
  NOTA_PENDENCIA        texto extra (`observacao`) no motivo das pendências de divergência do lojista.

FAIXAS (campo) - são os nomes que o código já usa internamente:
  CHECKOUT: DEBITO, CREDITO A VISTA, PARC_2_6, PARC_7_12, PIX, ANTECIPACAO   (taxa em %, como na planilha)
  REMESSA : SPREAD_REMESSA                                                    (valor em %; no cálculo vira fração)
  `ROTULO_FAIXA` traz o nome legível de cada uma (para telas).
LINHA DE NEGÓCIO: CHECKOUT | REMESSA | TODAS.  vigencia_fim vazia = em aberto (inclusive).

Seleção por lojista (`vigentes`): cnpj e ec_orbe são alternativas (OU): a condição vale se o cnpj dela é o pedido
OU o ec_orbe dela é o pedido. Se nenhum for pedido, não filtra por lojista.
Precedência em `taxa_efetiva`: ISENCAO vigente vence TAXA_ESPECIAL vigente, que vence a planilha.
"""
import csv
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ARQ_CONDICOES = "condicoes_comerciais.csv"
ARQ_HISTORICO = "historico_alteracoes.csv"

COLUNAS = ["id_condicao", "tipo", "cnpj", "ec_orbe", "lojista", "linha_negocio", "campo", "valor",
           "vigencia_inicio", "vigencia_fim", "aprovado_por", "data_registro", "fonte", "observacao"]
COLUNAS_HISTORICO = ["data_hora", "usuario", "acao", "id_condicao", "resumo"]

TIPOS = ["ISENCAO", "TAXA_ESPECIAL", "DE_PARA_EC", "BLOQUEIO_FATURAMENTO", "NOTA_PENDENCIA"]
LINHAS = ["CHECKOUT", "REMESSA", "TODAS"]
FAIXAS_CHECKOUT = ["DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX", "ANTECIPACAO"]
FAIXA_REMESSA = "SPREAD_REMESSA"
FAIXAS = FAIXAS_CHECKOUT + [FAIXA_REMESSA]
ROTULO_FAIXA = {"DEBITO": "Débito", "CREDITO A VISTA": "Crédito à vista", "PARC_2_6": "Crédito parcelado 2-6x",
                "PARC_7_12": "Crédito parcelado 7-12x", "PIX": "PIX", "ANTECIPACAO": "Antecipação",
                "SPREAD_REMESSA": "Spread de remessa"}
ROTULO_TIPO = {"ISENCAO": "isenção", "TAXA_ESPECIAL": "taxa especial", "DE_PARA_EC": "de-para de EC",
               "BLOQUEIO_FATURAMENTO": "bloqueio de faturamento", "NOTA_PENDENCIA": "nota de pendência"}
EXIGEM_APROVACAO = {"ISENCAO", "TAXA_ESPECIAL"}
ACOES = ["CRIAR", "ENCERRAR"]


class CadastroAusente(FileNotFoundError):
    """A pasta ou o arquivo de condições não existe."""


class CadastroInvalido(ValueError):
    """O cadastro existe mas está malformado, ou a condição pedida não passa na validação (mensagem em português)."""


# ---------------------------------------------------------------- utilidades
def _data(txt, onde):
    try:
        return datetime.strptime(txt.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise CadastroInvalido(f"{onde}: data '{txt}' inválida (use AAAA-MM-DD).") from None


def _data_ou_none(txt, onde):
    return _data(txt, onde) if (txt or "").strip() else None


def _so_digitos(txt):
    return re.sub(r"\D", "", txt or "")


def _faixas_do_campo(campo):
    """Lista de faixas do campo; 'todas' (qualquer caixa) devolve ['TODAS']."""
    itens = [p.strip().upper() for p in (campo or "").split(",") if p.strip()]
    return itens


def _faixas_validas(campo, tipo, linha, onde):
    itens = _faixas_do_campo(campo)
    if not itens:
        raise CadastroInvalido(f"{onde}: o campo (faixa) é obrigatório. Faixas válidas: {', '.join(FAIXAS)}"
                               + (" ou 'todas'." if tipo == "ISENCAO" else "."))
    if itens == ["TODAS"]:
        if tipo != "ISENCAO":
            raise CadastroInvalido(f"{onde}: 'todas' só vale para ISENCAO; informe uma faixa ({', '.join(FAIXAS)}).")
        return itens
    for f in itens:
        if f not in FAIXAS:
            raise CadastroInvalido(f"{onde}: faixa '{f}' desconhecida. Faixas válidas: {', '.join(FAIXAS)}.")
        if linha != "TODAS" and (f == FAIXA_REMESSA) != (linha == "REMESSA"):
            raise CadastroInvalido(f"{onde}: a faixa {f} não pertence à linha de negócio {linha}.")
    if tipo == "TAXA_ESPECIAL" and len(itens) != 1:
        raise CadastroInvalido(f"{onde}: TAXA_ESPECIAL aceita UMA faixa por condição (campo '{campo}').")
    return itens


def _validar(c, onde):
    """Valida e normaliza UMA condição (dict com todas as COLUNAS, textos). Devolve o dict normalizado."""
    c = {k: (c.get(k) or "").strip() for k in COLUNAS}
    tipo = c["tipo"].upper()
    if tipo not in TIPOS:
        raise CadastroInvalido(f"{onde}: tipo '{c['tipo']}' inválido. Tipos válidos: {', '.join(TIPOS)}.")
    c["tipo"] = tipo
    c["cnpj"] = _so_digitos(c["cnpj"])
    c["ec_orbe"] = _so_digitos(c["ec_orbe"])
    if c["cnpj"] and len(c["cnpj"]) != 14:
        raise CadastroInvalido(f"{onde}: CNPJ '{c['cnpj']}' deve ter 14 dígitos.")
    linha = c["linha_negocio"].upper()
    if linha not in LINHAS:
        raise CadastroInvalido(f"{onde}: linha_negocio '{c['linha_negocio']}' inválida. Use CHECKOUT, REMESSA ou TODAS.")
    c["linha_negocio"] = linha
    ini = _data(c["vigencia_inicio"], f"{onde}: vigencia_inicio") if c["vigencia_inicio"] else None
    if ini is None:
        raise CadastroInvalido(f"{onde}: a vigência inicial é obrigatória (AAAA-MM-DD).")
    fim = _data_ou_none(c["vigencia_fim"], f"{onde}: vigencia_fim")
    if fim is not None and fim < ini:
        raise CadastroInvalido(f"{onde}: a vigência termina ({fim}) antes de começar ({ini}).")
    if c["data_registro"]:
        _data(c["data_registro"], f"{onde}: data_registro")
    if tipo in EXIGEM_APROVACAO and not c["aprovado_por"]:
        raise CadastroInvalido(f"{onde}: {ROTULO_TIPO[tipo]} exige aprovado_por (quem do Comercial aprovou).")
    if tipo in ("ISENCAO", "TAXA_ESPECIAL"):
        if not (c["cnpj"] or c["ec_orbe"]):
            raise CadastroInvalido(f"{onde}: informe o CNPJ ou o EC Orbe do lojista.")
        c["campo"] = ",".join(_faixas_validas(c["campo"], tipo, linha, onde))
        if c["campo"] == "TODAS":
            c["campo"] = "todas"
    if tipo == "TAXA_ESPECIAL":
        try:
            v = Decimal(c["valor"])
        except InvalidOperation:
            raise CadastroInvalido(f"{onde}: valor '{c['valor']}' inválido; informe a taxa em % com ponto (ex.: 2.19).") from None
        if v < 0 or v > 100:
            raise CadastroInvalido(f"{onde}: valor {c['valor']} fora do intervalo 0 a 100 (%).")
    elif c["valor"]:
        try:
            Decimal(c["valor"])
        except InvalidOperation:
            raise CadastroInvalido(f"{onde}: valor '{c['valor']}' inválido; use número com ponto.") from None
    if tipo == "DE_PARA_EC" and not (c["ec_orbe"] and c["cnpj"]):
        raise CadastroInvalido(f"{onde}: DE_PARA_EC exige ec_orbe e cnpj (liga o EC da Orbe ao CNPJ da planilha).")
    if tipo == "BLOQUEIO_FATURAMENTO":
        if not (c["cnpj"] or c["ec_orbe"]):
            raise CadastroInvalido(f"{onde}: informe o CNPJ ou o EC Orbe do lojista bloqueado.")
        if not c["observacao"]:
            raise CadastroInvalido(f"{onde}: BLOQUEIO_FATURAMENTO exige o motivo em observacao.")
    if tipo == "NOTA_PENDENCIA":
        if not c["cnpj"]:
            raise CadastroInvalido(f"{onde}: NOTA_PENDENCIA exige o CNPJ do lojista.")
        if not c["observacao"]:
            raise CadastroInvalido(f"{onde}: NOTA_PENDENCIA exige o texto em observacao.")
    return c


def _caminhos(pasta):
    pasta = Path(pasta)
    return pasta, pasta / ARQ_CONDICOES, pasta / ARQ_HISTORICO


def _escrever_csv(caminho, colunas, linhas):
    """Grava via arquivo temporário + troca, para nunca deixar o cadastro pela metade."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(colunas)
        for l in linhas:
            w.writerow([l.get(c, "") for c in colunas])
    os.replace(tmp, caminho)


def _ler_historico(caminho):
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _historico(pasta, usuario, acao, id_condicao, resumo, agora=None):
    _, _, hist = _caminhos(pasta)
    linhas = _ler_historico(hist)
    linhas.append({"data_hora": (agora or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"), "usuario": usuario,
                   "acao": acao, "id_condicao": id_condicao, "resumo": resumo})
    _escrever_csv(hist, COLUNAS_HISTORICO, linhas)


def _resumo(c):
    quem = c["lojista"] or c["cnpj"] or c["ec_orbe"]
    partes = [ROTULO_TIPO[c["tipo"]], quem, c["linha_negocio"]]
    if c["campo"]:
        partes.append(c["campo"])
    if c["valor"]:
        partes.append(f"{c['valor']}%")
    periodo = f"{c['vigencia_inicio']} a {c['vigencia_fim'] or 'em aberto'}"
    return " | ".join(partes) + f" | {periodo}"


# ---------------------------------------------------------------- leitura
def ler(pasta_cadastro):
    """Lê e valida o cadastro. Lista de dicts (todas as COLUNAS, como texto), na ordem do arquivo.
    CadastroAusente se a pasta/arquivo não existe; CadastroInvalido (mensagem em português, com a linha) se malformado."""
    pasta, arq, _ = _caminhos(pasta_cadastro)
    if not arq.exists():
        raise CadastroAusente(f"Cadastro de condições comerciais não encontrado: {arq}")
    try:
        texto = arq.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise CadastroInvalido(f"{arq.name}: o arquivo não está em UTF-8.") from None
    leitor = csv.reader(texto.splitlines(), delimiter=";")
    try:
        cab = [h.strip() for h in next(leitor)]
    except StopIteration:
        raise CadastroInvalido(f"{arq.name}: arquivo vazio (falta o cabeçalho {';'.join(COLUNAS)}).") from None
    if cab != COLUNAS:
        faltam = [c for c in COLUNAS if c not in cab]
        extras = [c for c in cab if c not in COLUNAS]
        det = (f" Faltam: {', '.join(faltam)}." if faltam else "") + (f" Colunas desconhecidas: {', '.join(extras)}." if extras else "")
        raise CadastroInvalido(f"{arq.name}: cabeçalho diferente do esperado ({';'.join(COLUNAS)}).{det}"
                               + ("" if faltam or extras else " As colunas estão fora de ordem."))
    out, ids = [], set()
    for n, linha in enumerate(leitor, start=2):
        if not any(x.strip() for x in linha):
            continue
        onde = f"{arq.name}, linha {n}"
        if len(linha) != len(COLUNAS):
            raise CadastroInvalido(f"{onde}: {len(linha)} colunas, esperado {len(COLUNAS)} "
                                   "(texto com ';' precisa estar entre aspas).")
        c = _validar(dict(zip(COLUNAS, linha)), onde)
        if not c["id_condicao"]:
            raise CadastroInvalido(f"{onde}: id_condicao vazio.")
        if c["id_condicao"] in ids:
            raise CadastroInvalido(f"{onde}: id_condicao {c['id_condicao']} repetido.")
        ids.add(c["id_condicao"])
        out.append(c)
    criadas = [h["id_condicao"] for h in _ler_historico(_caminhos(pasta)[2]) if h.get("acao") == "CRIAR"]
    faltam = sorted({i for i in criadas if i not in ids})
    if faltam:       # arquivo truncado/editado à mão: o histórico lembra condições que não estão mais no cadastro
        raise CadastroInvalido(f"O cadastro parece incompleto: faltam {', '.join(faltam)}, registradas no histórico "
                               f"({ARQ_HISTORICO}) como criadas mas ausentes de {arq.name}. Restaurar o arquivo "
                               "(ex.: do git) antes de fechar o mês.")
    return out


# ---------------------------------------------------------------- consulta
def _vale_na_data(c, data):
    if data is None:
        return True
    ini = _data(c["vigencia_inicio"], c["id_condicao"])
    fim = _data_ou_none(c["vigencia_fim"], c["id_condicao"])
    return ini <= data and (fim is None or data <= fim)


def _do_lojista(c, cnpj, ec):
    if cnpj is None and ec is None:
        return True
    return bool((cnpj and c["cnpj"] == _so_digitos(cnpj)) or (ec and c["ec_orbe"] == _so_digitos(ec)))


def vigentes(condicoes, data, *, cnpj=None, ec=None, linha=None, tipo=None):
    """Condições vigentes em `data` (date; None = ignora a vigência), filtradas por lojista (cnpj OU ec), linha de
    negócio (uma condição TODAS vale para qualquer linha) e tipo. Mantém a ordem do cadastro."""
    out = []
    for c in condicoes or []:
        if tipo and c["tipo"] != tipo:
            continue
        if linha and c["linha_negocio"] not in (linha, "TODAS"):
            continue
        if not _do_lojista(c, cnpj, ec) or not _vale_na_data(c, data):
            continue
        out.append(c)
    return out


def do_lojista(condicoes, tipo, *, cnpj=None, ec=None, linha=None):
    """Como `vigentes` mas SEM filtrar pela data (para textos e para saber que o lojista tem a condição)."""
    return vigentes(condicoes, None, cnpj=cnpj, ec=ec, linha=linha, tipo=tipo)


def periodo(c):
    """(início, fim|None) da condição como datas."""
    return _data(c["vigencia_inicio"], c["id_condicao"]), _data_ou_none(c["vigencia_fim"], c["id_condicao"])


def rotulo(c):
    """Como o texto do fechamento cita a condição: a referência histórica CCnn da observação (ex.: CC01), senão o id."""
    m = re.search(r"\bCC\d{2}\b", c.get("observacao") or "")
    return m.group(0) if m else c["id_condicao"]


def referencia_fonte(c):
    """Primeira referência da coluna fonte (ex.: 'S07/S47' -> 'S07'); vazio se não houver."""
    return (c.get("fonte") or "").split("/")[0].strip()


def cnpj_do_ec(condicoes, ec, data):
    """DE_PARA_EC vigente: CNPJ ligado ao EC Orbe (ou None)."""
    for c in vigentes(condicoes, data, ec=ec, tipo="DE_PARA_EC"):
        return c["cnpj"]
    return None


def bloqueio(condicoes, ec, data=None, cnpj=None):
    """BLOQUEIO_FATURAMENTO do EC (ou do CNPJ), vigente em `data` (sem data, a mais recente) ou None."""
    achadas = vigentes(condicoes, data, ec=ec or "", cnpj=cnpj or "", tipo="BLOQUEIO_FATURAMENTO")
    return achadas[-1] if achadas else None


def notas_pendencia(condicoes, cnpj, linha, data=None):
    """Textos de NOTA_PENDENCIA do lojista na linha (vigentes em `data`; sem data, todas)."""
    return [c["observacao"] for c in vigentes(condicoes, data, cnpj=cnpj, linha=linha, tipo="NOTA_PENDENCIA")]


def _faixas_da_condicao(c):
    itens = _faixas_do_campo(c["campo"])
    if itens == ["TODAS"]:
        if c["linha_negocio"] == "REMESSA":
            return [FAIXA_REMESSA]
        return list(FAIXAS_CHECKOUT) if c["linha_negocio"] == "CHECKOUT" else list(FAIXAS)
    return itens


def condicao_aplicada(planilha_linha, condicoes, data, faixa, ec=None):
    """A condição do cadastro que muda a taxa nessa faixa e data (ISENCAO antes de TAXA_ESPECIAL), ou None.
    planilha_linha: contrato da planilha (usa 'cnpj' e, se `ec` não vier, 'ec')."""
    linha = "REMESSA" if faixa == FAIXA_REMESSA else "CHECKOUT"
    cnpj = (planilha_linha or {}).get("cnpj")
    ec = ec if ec is not None else (planilha_linha or {}).get("ec")
    for tipo in ("ISENCAO", "TAXA_ESPECIAL"):
        for c in vigentes(condicoes, data, cnpj=cnpj or "", ec=ec or "", linha=linha, tipo=tipo):
            if not (cnpj or ec):
                continue
            if faixa in _faixas_da_condicao(c):
                return c
    return None


def taxa_efetiva(planilha_linha, condicoes, data, faixa, ec=None):
    """(valor, origem_texto): a taxa que vale na `faixa` em `data`.
    Sem condição vigente: o valor da planilha (None se a célula está em branco) e 'planilha linha N'.
    Com condição: zero (ISENCAO) ou o valor da TAXA_ESPECIAL e 'cadastro C001 (ISENCAO, aprovado por Comercial)'.
    Unidade: % para as faixas de checkout; fração para SPREAD_REMESSA (como em planilha_linha['spread'])."""
    c = condicao_aplicada(planilha_linha, condicoes, data, faixa, ec)
    if c is None:
        if faixa == FAIXA_REMESSA:
            valor = planilha_linha.get("spread")
        else:
            valor = planilha_linha["taxas"].get(faixa)
        return valor, f"planilha linha {planilha_linha.get('linha')}"
    if c["tipo"] == "ISENCAO":
        valor = Decimal("0")
    else:
        valor = Decimal(c["valor"])
        if faixa == FAIXA_REMESSA:
            valor = valor / Decimal("100")
    return valor, f"cadastro {c['id_condicao']} ({c['tipo']}, aprovado por {c['aprovado_por']})"


# ---------------------------------------------------------------- escrita
def _proximo_id(condicoes):
    n = 0
    for c in condicoes:
        m = re.fullmatch(r"C(\d+)", c["id_condicao"])
        if m:
            n = max(n, int(m.group(1)))
    return f"C{n + 1:03d}"


def _sobrepoe(a, b):
    ia, fa = periodo(a)
    ib, fb = periodo(b)
    return (fb is None or ia <= fb) and (fa is None or ib <= fa)


def _conflito(c, existentes, contratos=None):
    """Mensagem de erro se `c` (já validada) conflita com o cadastro/planilha; None se está tudo certo."""
    if c["cnpj"] and c["ec_orbe"]:
        conhecidos = {o["cnpj"] for o in existentes if o["ec_orbe"] == c["ec_orbe"] and o["cnpj"]}
        conhecidos |= {x["cnpj"] for x in (contratos or []) if x.get("ec") == c["ec_orbe"] and not x.get("riscado")}
        if conhecidos and c["cnpj"] not in conhecidos:
            return (f"O EC Orbe {c['ec_orbe']} já está ligado ao CNPJ {', '.join(sorted(conhecidos))} "
                    f"(cadastro ou planilha), não ao {c['cnpj']}. Confira o EC e o CNPJ informados.")
    for o in existentes:
        if o["tipo"] != c["tipo"] or not _sobrepoe(o, c):
            continue
        if c["tipo"] == "DE_PARA_EC":
            cruza = o["ec_orbe"] == c["ec_orbe"]
        elif c["tipo"] == "BLOQUEIO_FATURAMENTO":
            cruza = _do_lojista(o, c["cnpj"] or None, c["ec_orbe"] or None)
        elif c["tipo"] in ("TAXA_ESPECIAL", "ISENCAO"):
            cruza = (_do_lojista(o, c["cnpj"] or None, c["ec_orbe"] or None)
                     and set(_faixas_da_condicao(o)) & set(_faixas_da_condicao(c)))
        else:
            cruza = False
        if cruza:
            return (f"Já existe a condição {o['id_condicao']} ({ROTULO_TIPO[o['tipo']]}) para o mesmo lojista"
                    f"{' e faixa ' + o['campo'] if o['campo'] else ''} em período que se sobrepõe. "
                    f"Encerre {o['id_condicao']} antes de registrar a nova.")
    return None


def validar(condicao, pasta, contratos=None, hoje=None):
    """Dry-run de `adicionar_varias`: mesma validação (campos, aprovação, sobreposição com o cadastro e com as outras
    condições da lista, EC x CNPJ), SEM gravar nada. `condicao` = um dict ou uma lista de dicts. Devolve a lista de
    mensagens de erro em português (vazia = pode gravar). Não exige usuario nem que a pasta exista."""
    condicoes = [condicao] if isinstance(condicao, dict) else list(condicao)
    pasta, arq, _ = _caminhos(pasta)
    try:
        atuais = ler(pasta) if arq.exists() else []
    except CadastroInvalido as e:
        return [f"O cadastro atual está malformado: {e}"]
    erros, novas = [], []
    for n, cond in enumerate(condicoes, start=1):
        onde = "Condição nova" if len(condicoes) == 1 else f"Condição nova {n} de {len(condicoes)}"
        c = {k: str(v).strip() if v is not None else "" for k, v in dict(cond).items() if k in COLUNAS}
        c["id_condicao"] = _proximo_id(atuais + novas)
        c["data_registro"] = (hoje or date.today()).isoformat()
        try:
            c = _validar(c, onde)
            erro = _conflito(c, atuais + novas, contratos)
        except CadastroInvalido as e:
            erros.append(str(e))
            continue
        if erro:
            erros.append(f"{onde}: {erro}")
            continue
        novas.append(c)
    return erros


def adicionar_varias(pasta, condicoes, usuario, hoje=None, contratos=None):
    """Valida TODAS as condições (também entre si e contra o cadastro) antes de gravar qualquer uma: ou entram todas, ou
    nenhuma (CadastroInvalido diz qual falhou). Gera ids sequenciais, grava uma vez e anota um CRIAR por condição.
    `contratos` (opcional) = linhas da planilha, para conferir que o EC informado pertence ao CNPJ. Devolve as gravadas."""
    usuario = (usuario or "").strip()
    if not usuario:
        raise CadastroInvalido("Informe quem está registrando a condição (usuario).")
    pasta, arq, _ = _caminhos(pasta)
    atuais = ler(pasta) if arq.exists() else []
    novas = []
    for n, condicao in enumerate(condicoes, start=1):
        onde = "Condição nova" if len(condicoes) == 1 else f"Condição nova {n} de {len(condicoes)}"
        c = {k: str(v).strip() if v is not None else "" for k, v in dict(condicao).items() if k in COLUNAS}
        c["id_condicao"] = _proximo_id(atuais + novas)
        c["data_registro"] = (hoje or date.today()).isoformat()
        c = _validar(c, onde)
        erro = _conflito(c, atuais + novas, contratos)
        if erro:
            raise CadastroInvalido(f"{onde}: {erro}")
        novas.append(c)
    if not novas:
        return []
    _escrever_csv(arq, COLUNAS, atuais + novas)
    _, _, hist = _caminhos(pasta)
    linhas = _ler_historico(hist)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas += [{"data_hora": agora, "usuario": usuario, "acao": "CRIAR", "id_condicao": c["id_condicao"],
                "resumo": _resumo(c)} for c in novas]
    _escrever_csv(hist, COLUNAS_HISTORICO, linhas)
    return novas


def adicionar(pasta, condicao, usuario, hoje=None, contratos=None):
    """Valida e grava uma condição nova (cria a pasta/arquivos se for a primeira vez). Gera o id C### e a data de
    registro, e anota CRIAR no histórico. Recusa sobreposição (mesmo lojista e faixa, período que se cruza) de
    ISENCAO, TAXA_ESPECIAL, DE_PARA_EC e BLOQUEIO, e EC ligado a outro CNPJ. Devolve a condição gravada."""
    return adicionar_varias(pasta, [condicao], usuario, hoje, contratos)[0]


def encerrar(pasta, id_condicao, data_fim, usuario):
    """Preenche a vigencia_fim da condição (ou a antecipa, se já tinha fim; não apaga) e anota ENCERRAR no histórico. Devolve a condição alterada."""
    usuario = (usuario or "").strip()
    if not usuario:
        raise CadastroInvalido("Informe quem está encerrando a condição (usuario).")
    pasta, arq, _ = _caminhos(pasta)
    atuais = ler(pasta)
    alvo = next((c for c in atuais if c["id_condicao"] == id_condicao), None)
    if alvo is None:
        raise CadastroInvalido(f"Condição {id_condicao} não encontrada no cadastro.")
    fim = data_fim if isinstance(data_fim, date) else _data(str(data_fim), "Data de encerramento")
    if alvo["vigencia_fim"] and fim >= _data(alvo["vigencia_fim"], id_condicao):
        raise CadastroInvalido(f"A condição {id_condicao} já termina em {alvo['vigencia_fim']}; "
                               "só é possível antecipar o fim, não adiá-lo (registre uma condição nova).")
    ini, _ = periodo(alvo)
    if fim < ini:
        raise CadastroInvalido(f"A data de encerramento ({fim}) é anterior ao início da vigência ({ini}).")
    alvo["vigencia_fim"] = fim.isoformat()
    _escrever_csv(arq, COLUNAS, atuais)
    _historico(pasta, usuario, "ENCERRAR", id_condicao, f"vigência encerrada em {fim.isoformat()} | " + _resumo(alvo))
    return alvo


def ler_historico(pasta_cadastro):
    """Linhas do historico_alteracoes.csv (lista de dicts), vazia se ainda não existe."""
    return _ler_historico(_caminhos(pasta_cadastro)[2])
