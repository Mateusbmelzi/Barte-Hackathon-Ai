"""Interface web local do fechamento mensal (só biblioteca padrão).

Escuta apenas em 127.0.0.1. Não calcula nada: recebe os arquivos, chama
src.fechamento.executar() e devolve o resumo e os CSVs gerados.

Pasta do mês persistente: meses/<AAAA-MM>/entrada (nunca sobrescreve: nome repetido vira _v2, conteúdo idêntico
não é salvo de novo, "remover" move para _removidos). Cada fechamento grava em
meses/<AAAA-MM>/execucoes/<AAAA-MM-DD_HHMMSS>/saida e a mais recente é a mostrada.
Investigação de divergências (PLANO_IA_01 Fase 3): o dossiê vem de saida/investigacao/; as hipóteses
da IA (src/ia.py) e as decisões da analista ficam na pasta da execução (investigacao_ia.json e
decisoes_investigacao.csv), nunca em saida/.
"""
import csv
import hashlib
import io
import json
import os
import re
import socket
import threading
import traceback
import urllib.request
import webbrowser
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from src import config, fechamento, ia, leitores
from src.dinheiro import fmt_br, soma
from src.leitores import _glob_para_regex

try:                                  # cadastro de condições comerciais (Dev A). Sem ele a aba Clientes só lê a planilha.
    from src import cadastro
except ImportError:                   # pragma: no cover - até o módulo existir
    cadastro = None

RAIZ = Path(__file__).resolve().parent.parent
PASTA_CADASTRO = RAIZ / "cadastro"
PASTA_MESES = RAIZ / "meses"
RX_MES = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
COLUNAS_ENVIOS = ["data_hora", "arquivo_salvo", "nome_original", "tipo_reconhecido", "usuario", "acao"]
PAGINA = Path(__file__).resolve().parent / "pagina.html"
TAMANHO_MAXIMO = 200 * 1024 * 1024  # 200 MB por arquivo

ROTULOS = {
    "orbe": "Relatório(s) Orbe",
    "taxas": "Tabela de taxas",
    "ponte": "E-mail Ponte Câmbio",
    "plano": "Plano de contas",
    "aurora": "Extrato Aurora",
    "meridiano": "Extrato Meridiano",
}

SAIDAS = [
    ("pendencias.csv", "O que precisa de decisão de uma pessoa, com motivo e quem decide. Comece por aqui."),
    ("notas_a_emitir.csv", "Notas fiscais prontas: tomador, CNPJ, valor e texto da discriminação."),
    ("comissoes_por_lojista.csv", "Comissão de cada lojista no checkout e na remessa."),
    ("divergencias_taxa.csv", "Transações em que a Orbe ou a Ponte cobrou diferente do contrato."),
    ("lancamentos_classificados.csv", "Movimentos dos extratos Aurora e Meridiano com a conta contábil."),
    ("rastro.csv", "De onde vem cada número: arquivo e linha de origem."),
]
NOMES_SAIDA = {n for n, _ in SAIDAS}

COLUNAS_DECISOES = ["id_grupo", "lojista", "hipotese_n", "causa", "causa_categoria", "decisao", "comentario",
                    "analista", "data_hora", "modelo_resposta", "versao_prompt"]
DECISOES = ("CONCORDO", "DISCORDO", "VERIFICAR")
DECISOES_COM_COMENTARIO = ("DISCORDO", "VERIFICAR")      # sem justificativa a decisão não vale
INSTRUCAO_CHAVE = "Crie o arquivo .env na pasta do programa com ANTHROPIC_API_KEY=sua-chave (veja o README)."


def reconhecer(nome):
    """Qual fonte este nome de arquivo representa, pelos mesmos padrões de src (PADROES_ARQUIVOS)."""
    for chave, padrao in config.PADROES_ARQUIVOS.items():
        if re.fullmatch(_glob_para_regex(padrao), nome, re.IGNORECASE):
            return chave
    return None


def _nome_seguro(nome):
    nome = Path(nome.replace("\\", "/")).name.strip()
    nome = re.sub(r'[<>:"/|?*\x00-\x1f]', "_", nome)
    return nome if nome not in ("", ".", "..") else ""


def _contar_linhas(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return max(sum(1 for _ in csv.reader(f, delimiter=";")) - 1, 0)


def _previa(caminho, n=10):
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    cols = ["id_saida", "tipo", "valor_brl", "motivo", "quem_decide"]
    return {"total": len(linhas), "colunas": cols,
            "linhas": [[l.get(c, "") for c in cols] for l in linhas[:n]]}


def resumo_dict(r):
    """Resumo do fechamento para a tela (mesmos números do resumo da linha de comando)."""
    c, dv, n = r["comissoes"], r["divergencias"], r["notas"]

    def tot(xs, k):
        return soma(x[k] for x in xs)

    def por_linha(xs, ln):
        return [x for x in xs if x["linha_negocio"] == ln]

    chk, rem = por_linha(c, "CHECKOUT"), por_linha(c, "REMESSA")
    return {
        "competencia": r["competencia"],
        "checkout": {"valor": fmt_br(tot(chk, "comissao")), "lojistas": len(chk),
                     "transacoes": sum(x["qtd"] for x in chk)},
        "remessa": {"valor": fmt_br(tot(rem, "comissao")), "lojistas": len(rem),
                    "operacoes": sum(x["qtd"] for x in rem)},
        "notas": {"valor": fmt_br(tot(n, "valor")), "quantidade": len(n)},
        "divergencias": {
            ln.lower(): {"valor": fmt_br(tot(por_linha(dv, ln), "diferenca")), "linhas": len(por_linha(dv, ln))}
            for ln in ("CHECKOUT", "REMESSA")},
        "lancamentos": len(r["lancamentos"]),
        "pendencias": {"quantidade": len(r["pendencias"]),
                       "por_responsavel": dict(Counter(p["quem_decide"] for p in r["pendencias"]))},
        # S53: fechamento parcial (fonte ausente ou layout inesperado)
        "parcial": bool(r.get("parcial")),
        "aviso_parcial": r.get("aviso_parcial"),
        "bloqueios": [{"tipo": b["tipo"], "fonte": ROTULOS.get(b["fonte"], b["fonte"]), "arquivo": b["arquivo"]}
                      for b in r.get("bloqueios", [])],
        "bloqueado": r.get("bloqueado", {}),
        "versoes": r.get("versoes"),      # consolidação de versões por fonte (src/fechamento); None = bloco escondido
    }


def _mensagem_erro(e):
    """Erro legível: tipo + mensagem, sem stack trace."""
    msg = str(e).strip() or e.__class__.__name__
    dicas = {
        PermissionError: "Não foi possível gravar um arquivo de saída.",
        FileNotFoundError: "Algum arquivo não foi encontrado ou está repetido.",
        KeyError: "Uma coluna ou informação esperada não está no arquivo (o layout pode ter mudado).",
        ValueError: "Um arquivo tem um valor ou formato que o programa não reconhece.",
        AssertionError: "A conferência interna dos números falhou; nada foi gravado como definitivo.",
    }
    dica = next((t for k, t in dicas.items() if isinstance(e, k)), "Erro inesperado ao processar os arquivos.")
    linhas = msg.splitlines()
    if len(linhas) > 12:
        msg = "\n".join(linhas[:12] + ["(...)"])
    return {"titulo": dica, "detalhe": msg}


def mes_anterior(hoje):
    """Mês anterior ao de hoje, no formato AAAA-MM (competência padrão)."""
    ultimo = hoje.replace(day=1) - timedelta(days=1)
    return f"{ultimo:%Y-%m}"


def _hash(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def _familia(nome):
    """'x_v2.csv' e 'x.csv' são o mesmo arquivo em versões diferentes."""
    return re.sub(r"_v\d+(?=\.[^.]*$)", "", nome).lower()


def _data_br_hora(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


class Estado:
    """Uma execução em andamento por vez (uso local, uma analista).
    cliente_ia: cliente da API injetável (testes); None = ia.investigar cria o cliente real com a chave."""

    def __init__(self, pasta_meses=PASTA_MESES, cliente_ia=None, raiz_ia=None, pasta_cadastro=PASTA_CADASTRO,
                 raiz_planilha=RAIZ, hoje=None):
        self.pasta_meses = Path(pasta_meses)
        self.pasta_cadastro = Path(pasta_cadastro)   # cadastro/condicoes_comerciais.csv (nunca a planilha do cliente)
        self.raiz_planilha = Path(raiz_planilha)     # onde procurar a planilha de taxas se ainda não foi enviada
        self.hoje = hoje                              # None = data de hoje (injetável nos testes)
        self.cliente_ia = cliente_ia
        self.raiz_ia = raiz_ia
        self.lock = threading.Lock()
        self.clientes = Clientes(self)
        self.geracao = 0          # muda a cada execução: resposta da IA de execução antiga é descartada
        self.mes = mes_anterior(self.hoje or date.today())   # competência escolhida (AAAA-MM)
        self.recomecar()

    # ------------------------------------------------ pasta do mês
    def entrada(self):
        return self.pasta_meses / self.mes / "entrada"

    def meses_existentes(self):
        if not self.pasta_meses.is_dir():
            return []
        return sorted(p.name for p in self.pasta_meses.iterdir() if p.is_dir() and RX_MES.fullmatch(p.name))

    def escolher_mes(self, mes):
        mes = str(mes or "").strip()
        if not RX_MES.fullmatch(mes):
            return False, "Mês inválido: use o formato AAAA-MM (ex.: 2026-09)."
        if mes != self.mes:
            self.mes = mes
            self.recomecar()
        return True, "ok"

    def _ler_envios(self):
        f = self.entrada() / "_envios.csv"
        if not f.exists():
            return []
        with open(f, encoding="utf-8", newline="") as h:
            return list(csv.DictReader(h, delimiter=";"))

    def _registrar(self, arquivo, original, tipo, usuario, acao):
        entrada = self.entrada()
        entrada.mkdir(parents=True, exist_ok=True)
        f = entrada / "_envios.csv"
        novo = not f.exists()
        with open(f, "a", encoding="utf-8", newline="") as h:
            w = csv.writer(h, delimiter=";", lineterminator="\n")
            if novo:
                w.writerow(COLUNAS_ENVIOS)
            w.writerow([datetime.now().isoformat(timespec="seconds"), arquivo, original, tipo or "", usuario, acao])

    def versoes(self):
        """chave -> versões (mais antiga primeiro) dos arquivos ativos da pasta do mês."""
        entrada = self.entrada()
        if not entrada.is_dir():
            return {}
        envios = [e for e in self._ler_envios() if e.get("acao", "enviado") == "enviado"]
        ordem = {e["arquivo_salvo"]: (i, e) for i, e in enumerate(envios)}
        achados = []
        for p in entrada.iterdir():
            chave = reconhecer(p.name) if p.is_file() and not p.name.startswith("_") else None
            if chave is None:
                continue
            i, e = ordem.get(p.name, (-1, None))
            quando = e["data_hora"] if e else datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
            achados.append((chave, (i, p.stat().st_mtime, p.name.lower()), {
                "arquivo": p.name, "nome_original": e["nome_original"] if e else p.name, "data_hora": quando,
                "data_hora_br": _data_br_hora(quando), "usuario": e["usuario"] if e else "",
                "tamanho": p.stat().st_size}))
        por = {}
        for chave, ordenacao, v in sorted(achados, key=lambda x: x[1]):
            por.setdefault(chave, []).append(v)
        for chave, vs in por.items():
            vistos = set()
            for v in reversed(vs):       # a mais recente de cada arquivo (Orbe: de cada família) é a que vale
                fam = _familia(v["arquivo"]) if chave in config.FONTES_MULTIPLAS else chave
                v["mais_recente"] = fam not in vistos
                vistos.add(fam)
        return por

    def arquivo_recente(self, chave):
        vs = self.versoes().get(chave)
        return self.entrada() / vs[-1]["arquivo"] if vs else None

    def recomecar(self):
        self.pasta = None   # pasta da execução (saida, decisões, IA); só existe depois de rodar
        self.resultado = None
        self.r = None               # resultado completo do fechamento (a aba Clientes lê daqui o resumo do lojista)
        self.erro = None
        self._limpar_investigacao()

    def _limpar_investigacao(self):
        self.geracao += 1
        self.dossie = None
        self.ia_estado = "parado"     # parado | analisando | pronto
        self.ia_resultado = None
        self.decisoes = {}            # (id_grupo, hipotese_n) -> linha do CSV

    # ------------------------------------------------ investigação
    def ia_disponivel(self):
        if self.cliente_ia is not None:
            return True, "IA disponível (cliente de teste)."
        return ia.disponivel(self.raiz_ia)

    def gerar_hipoteses(self):
        """Chamado com o lock. Dispara a IA numa thread; devolve (ok, mensagem)."""
        if not self.dossie:
            return False, "Rode o fechamento primeiro."
        ok, motivo = self.ia_disponivel()
        if not ok:
            return False, motivo
        if self.ia_estado == "analisando":
            return False, "A IA já está analisando."
        self.ia_estado, self.ia_resultado, self.decisoes = "analisando", None, {}
        self._gravar_decisoes()
        geracao, dossie, pasta = self.geracao, self.dossie, self.pasta
        threading.Thread(target=self._rodar_ia, args=(geracao, dossie, pasta), daemon=True).start()
        return True, "analisando"

    def _rodar_ia(self, geracao, dossie, pasta):
        try:
            res = ia.investigar(dossie, cliente=self.cliente_ia, raiz=self.raiz_ia)
        except Exception as e:  # noqa: BLE001 - ia.investigar não deveria levantar; protege a tela
            traceback.print_exc()
            res = {"grupos": [{"id_grupo": g["id_grupo"], "erro": f"IA indisponível: {e}", "hipoteses": []}
                              for g in dossie["grupos"]]}
        with self.lock:
            if geracao != self.geracao:
                return                      # execução mudou enquanto a IA respondia
            self.ia_resultado, self.ia_estado = res, "pronto"
            (pasta / "investigacao_ia.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    def decidir(self, d):
        """Chamado com o lock. d = {id_grupo, hipotese_n, decisao, comentario, analista}."""
        analista = str(d.get("analista") or "").strip()
        if not analista:
            return False, "Informe seu nome antes de decidir."
        if d.get("decisao") not in DECISOES:
            return False, "Decisão inválida."
        if d["decisao"] in DECISOES_COM_COMENTARIO and not str(d.get("comentario") or "").strip():
            return False, "Escreva um comentário: para Discordo e Preciso verificar ele é obrigatório."
        if not self.ia_resultado:
            return False, "Gere as hipóteses antes de decidir."
        g = next((x for x in self.ia_resultado.get("grupos", []) if x.get("id_grupo") == d.get("id_grupo")), None)
        try:
            n = int(d.get("hipotese_n") or 1)       # o cartão decide sobre a causa principal (hipótese 1)
        except (TypeError, ValueError):
            n = 0
        if g is None or not 1 <= n <= len(g.get("hipoteses") or []):
            return False, "Hipótese não encontrada."
        self.decisoes[(g["id_grupo"], n)] = {
            "id_grupo": g["id_grupo"], "lojista": g.get("lojista") or "", "hipotese_n": n,
            "causa": g["hipoteses"][n - 1]["causa"],
            "causa_categoria": g["hipoteses"][n - 1].get("causa_categoria") or "", "decisao": d["decisao"],
            "comentario": str(d.get("comentario") or "").strip(), "analista": analista,
            "data_hora": datetime.now().isoformat(timespec="seconds"),
            "modelo_resposta": g.get("modelo_resposta") or g.get("modelo") or "",
            "versao_prompt": g.get("versao_prompt") or self.ia_resultado.get("versao_prompt") or "",
        }
        self._gravar_decisoes()
        return True, "ok"

    def csv_decisoes(self):
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";", lineterminator="\n")
        w.writerow(COLUNAS_DECISOES)
        for k in sorted(self.decisoes):
            w.writerow([self.decisoes[k][c] for c in COLUNAS_DECISOES])
        return buf.getvalue()

    def _gravar_decisoes(self):
        if self.pasta is not None:
            (self.pasta / "decisoes_investigacao.csv").write_text(self.csv_decisoes(), encoding="utf-8")

    def json_investigacao(self):
        if not self.dossie:
            return None
        ok, motivo = self.ia_disponivel()
        return {
            "dossie": self.dossie,
            "ia_disponivel": ok,
            "ia_motivo": motivo if ok else f"{motivo} {INSTRUCAO_CHAVE}",
            "ia_estado": self.ia_estado,
            "ia": self.ia_resultado,
            "rotulos_categoria": dict(getattr(ia, "ROTULO_CATEGORIA", None) or {}),
            "decisoes": [self.decisoes[k] for k in sorted(self.decisoes)],
        }

    def _invalidar(self):
        """A entrada mudou: o resultado mostrado deixa de valer (os arquivos da pasta do mês ficam)."""
        self.resultado, self.r, self.erro, self.pasta = None, None, None, None
        self._limpar_investigacao()

    def receber(self, nome, conteudo, usuario=""):
        """Guarda sem nunca sobrescrever: nome repetido vira _v2/_v3; conteúdo idêntico a um arquivo ativo não é salvo."""
        original = _nome_seguro(nome)
        chave = reconhecer(original) if original else None
        if chave is None:
            return {"nome": original, "reconhecido": None}
        entrada = self.entrada()
        entrada.mkdir(parents=True, exist_ok=True)
        h = _hash(conteudo)
        for p in sorted(entrada.iterdir()):
            if p.is_file() and not p.name.startswith("_") and _hash(p.read_bytes()) == h:
                quando = next((e["data_hora"] for e in reversed(self._ler_envios())
                               if e["arquivo_salvo"] == p.name and e.get("acao", "enviado") == "enviado"),
                              datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"))
                return {"nome": original, "reconhecido": chave, "duplicado": True, "arquivo_salvo": p.name,
                        "aviso": f"{original}: arquivo idêntico ao já enviado em {_data_br_hora(quando)} ({p.name}); não foi salvo de novo."}
        salvo, n = original, 1
        stem, ext = Path(original).stem, Path(original).suffix
        while (entrada / salvo).exists():
            n += 1
            salvo = f"{stem}_v{n}{ext}"
        (entrada / salvo).write_bytes(conteudo)
        self._registrar(salvo, original, chave, usuario, "enviado")
        self._invalidar()
        return {"nome": original, "reconhecido": chave, "arquivo_salvo": salvo, "versao": n,
                "aviso": f"{original} já existia nesta pasta: salvo como {salvo} (nova versão)." if n > 1 else None}

    def remover(self, arquivo, usuario=""):
        """Move para _removidos (nunca apaga) e registra. Devolve (ok, mensagem)."""
        nome = _nome_seguro(str(arquivo or ""))
        origem = self.entrada() / nome
        if not nome or nome.startswith("_") or not origem.is_file():
            return False, "Arquivo não encontrado nesta pasta."
        destino_dir = self.entrada() / "_removidos"
        destino_dir.mkdir(exist_ok=True)
        destino, n = destino_dir / nome, 1
        while destino.exists():
            n += 1
            destino = destino_dir / f"{Path(nome).stem}_r{n}{Path(nome).suffix}"
        origem.replace(destino)
        self._registrar(nome, nome, reconhecer(nome), usuario, "removido")
        self._invalidar()
        return True, "ok"

    def completo(self):
        """Uma fonte de cada tipo, com pelo menos 1 arquivo da Orbe (aceita N)."""
        return all(k in self.versoes() for k in config.PADROES_ARQUIVOS)

    def faltam(self):
        v = self.versoes()
        return [ROTULOS.get(k, k) for k in config.PADROES_ARQUIVOS if k not in v]

    def pronto(self):
        """S53: roda com pelo menos 1 fonte reconhecida; o que faltar vira fechamento parcial."""
        return bool(self.versoes())

    def execucoes(self):
        pasta = self.pasta_meses / self.mes / "execucoes"
        return sorted((p.name for p in pasta.iterdir() if p.is_dir()), reverse=True) if pasta.is_dir() else []

    def rodar(self):
        if not self.pronto():
            self.erro = {"titulo": "Faltam arquivos.",
                         "detalhe": "Envie pelo menos um arquivo do mês (Orbe, taxas, Ponte, plano de contas ou extratos) antes de rodar."}
            return
        base = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        raiz_exec = self.pasta_meses / self.mes / "execucoes"
        pasta, i = raiz_exec / base, 1
        while pasta.exists():
            i += 1
            pasta = raiz_exec / f"{base}_{i}"
        pasta.mkdir(parents=True)
        self._limpar_investigacao()
        self.pasta = pasta
        try:
            # as condições do cadastro (isenções, taxas especiais, bloqueios) entram no cálculo
            extra = {"cadastro": self.pasta_cadastro} if cadastro is not None else {}
            r = fechamento.executar(self.entrada(), pasta / "saida", **extra)
            self.r = r
            self.resultado = resumo_dict(r)
            self.erro = None
            self.dossie = r.get("investigacao")
        except Exception as e:  # noqa: BLE001 - mostrado à analista de forma legível
            traceback.print_exc()
            self.resultado, self.r, self.erro = None, None, _mensagem_erro(e)

    def saidas(self):
        if not self.resultado:
            return []
        pasta = self.pasta / "saida"
        return [{"nome": n, "descricao": d, "linhas": _contar_linhas(pasta / n)}
                for n, d in SAIDAS if (pasta / n).exists()]

    def _esperado(self, chave, padrao, vs):
        base = {"chave": chave, "rotulo": ROTULOS.get(chave, chave), "padrao": padrao, "versoes": vs}
        if not vs:
            return base
        if chave in config.FONTES_MULTIPLAS:
            nomes = sorted((v["arquivo"] for v in vs), key=str.lower)
            return {**base, "nome": ", ".join(nomes), "nomes": nomes, "tamanho": sum(v["tamanho"] for v in vs)}
        return {**base, "nome": vs[-1]["arquivo"], "tamanho": vs[-1]["tamanho"]}

    def json(self):
        versoes = self.versoes()
        d = {
            "mes": self.mes,
            "meses": sorted(set(self.meses_existentes()) | {self.mes}),
            "execucoes": self.execucoes(),
            "esperados": [self._esperado(k, p, versoes.get(k, [])) for k, p in config.PADROES_ARQUIVOS.items()],
            "pronto": self.pronto(),
            "completo": self.completo(),
            "faltam": self.faltam(),
            "aviso_faltam": (f"faltam: {', '.join(self.faltam())} — o fechamento será parcial"
                             if versoes and not self.completo() else None),
            "pasta": str(self.pasta) if self.pasta else None,
            "resultado": self.resultado,
            "erro": self.erro,
            "saidas": self.saidas(),
            "investigacao": self.json_investigacao(),
        }
        if self.resultado and (self.pasta / "saida" / "pendencias.csv").exists():
            d["previa_pendencias"] = _previa(self.pasta / "saida" / "pendencias.csv")
        return d


# ------------------------------------------------ aba Clientes (cadastro de condições; nunca escreve na planilha)
# Nomes de faixa = os do cadastro (src/cadastro.py) = chaves de contrato["taxas"] em src/leitores.py.
FAIXAS = [  # (nome, rótulo, linha de negócio)
    ("DEBITO", "Débito", "CHECKOUT"),
    ("CREDITO A VISTA", "Crédito à vista", "CHECKOUT"),
    ("PARC_2_6", "Crédito parcelado 2 a 6x", "CHECKOUT"),
    ("PARC_7_12", "Crédito parcelado 7 a 12x", "CHECKOUT"),
    ("PIX", "Pix", "CHECKOUT"),
    ("ANTECIPACAO", "Antecipação", "CHECKOUT"),
    ("SPREAD_REMESSA", "Spread da remessa", "REMESSA"),
]
ROTULO_FAIXA = {f[0]: f[1] for f in FAIXAS}
LINHA_DA_FAIXA = {f[0]: f[2] for f in FAIXAS}
FAIXAS_CHECKOUT = [f[0] for f in FAIXAS if f[2] == "CHECKOUT"]
TIPOS = {
    "ISENCAO": "Isenção (taxa zero)",
    "TAXA_ESPECIAL": "Taxa especial",
    "DE_PARA_EC": "De-para de EC Orbe",
    "BLOQUEIO_FATURAMENTO": "Bloqueio de faturamento",
    "NOTA_PENDENCIA": "Nota / pendência",
}
LINHAS = {"CHECKOUT": "Checkout (Orbe)", "REMESSA": "Remessa (Ponte Câmbio)", "TODAS": "Todas as linhas"}
APROVADORES = ("Comercial", "Helena (Financeiro)")
TIPOS_COM_APROVACAO = ("ISENCAO", "TAXA_ESPECIAL")
AVISO_RODAR = "Rode o fechamento de novo para aplicar."
SPREAD_PADRAO_TXT = "1,50%"

# Regras que a tela mostra na ficha (texto curto; o texto completo está em REGRAS_DE_NEGOCIO.md).
REGRAS = {
    "R10": "Comissão do checkout = valor bruto x taxa contratada (da planilha ou do cadastro), não a taxa que a Orbe descontou.",
    "R11": "Estorno abate a comissão pela taxa vigente na data da venda original.",
    "R12": "Antecipação: bruto x taxa de antecipação contratada; entra na mesma nota.",
    "R30": "Checkout: 1 nota por lojista por mês, com a comissão do mês.",
    "R31": "Saldo zero ou negativo não emite nota; negativo não transporta (vira pendência).",
    "R20": "Remessa: a Tarvo fica com 50% do spread em reais realizado, por operação.",
    "R22": "Divergência de remessa = (spread aplicado - contratado) x cotação x valor em moeda estrangeira.",
    "R32": "Remessa: 1 nota só, para a Ponte Câmbio, pelo total da participação.",
    "R15": "Sem contrato vigente: não faturar até o Comercial confirmar a taxa.",
    "R54": "Antecipação acima das vendas acumuladas de lojista novo gera alerta para Helena e Comercial.",
    "R59": "Sem contrato: o repasse ao lojista não para; só a cobrança da taxa fica suspensa.",
    "R52": "Isenção dada pelo Comercial fora do contrato: não se cobra a Orbe; a devolução ao lojista sai do bolso da Tarvo.",
    "R68": "Quem deve é decidido pelo contrato, não pelo aviso à Orbe/Ponte.",
}
CASAS_PCT = Decimal("0.01")


class ErroPedido(Exception):
    """Pedido inválido: a mensagem já é legível para a analista."""


def so_digitos(s):
    return re.sub(r"\D", "", str(s or ""))


def fmt_cnpj(c):
    c = so_digitos(c)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else (c or "—")


def _data_iso(s, campo):
    try:
        return date.fromisoformat(str(s or "").strip())
    except ValueError:
        raise ErroPedido(f"{campo}: informe uma data válida (dia/mês/ano).") from None


def _br(d):
    return f"{d:%d/%m/%Y}" if d else ""


def _data_cad(s):
    """Data de uma coluna do cadastro (AAAA-MM-DD) -> date ou None."""
    try:
        return date.fromisoformat(str(s or "").strip())
    except ValueError:
        return None


def _pct_txt(v, faixa=None):
    """Valor de taxa -> '2,69%'. O spread vem em fração (0,015) e aparece como 1,50%."""
    if v is None or str(v).strip() == "":
        return "—"
    x = Decimal(str(v))
    if faixa == "SPREAD_REMESSA":
        x *= 100
    return f"{x.quantize(CASAS_PCT):f}".replace(".", ",") + "%"


def _chave(s):
    s = str(s or "")
    return s if s.startswith("EC") else so_digitos(s)


class Clientes:
    """Monta a lista e a ficha dos lojistas e grava condições no cadastro. Lê a planilha de taxas, não escreve nela."""

    def __init__(self, estado):
        self.e = estado

    # ---------------------------------------------------------------- fontes
    def _hoje(self):
        return self.e.hoje or date.today()

    def _competencia_data(self):
        """Último dia da competência do último fechamento rodado (ex.: '09/2026' -> 2026-09-30), ou None."""
        r = self.e.r
        m = re.fullmatch(r"(\d{2})/(\d{4})", str((r or {}).get("competencia") or ""))
        if not m:
            return None
        mes, ano = int(m.group(1)), int(m.group(2))
        prox = date(ano + (mes == 12), mes % 12 + 1, 1)
        return prox - timedelta(days=1)

    def _contratos(self):
        planilha = self.e.arquivo_recente("taxas")
        if planilha is None:
            padrao = re.compile(_glob_para_regex(config.PADROES_ARQUIVOS["taxas"]), re.IGNORECASE)
            achados = sorted(p for p in self.e.raiz_planilha.glob("*.xlsx") if padrao.fullmatch(p.name))
            planilha = achados[0] if achados else None
        if not planilha or not planilha.exists():
            return []
        try:
            return leitores.ler_taxas(planilha)
        except Exception:  # noqa: BLE001 - planilha ilegível: a tela segue só com o cadastro
            return []

    def _condicoes(self):
        if cadastro is None:
            return []
        try:
            return cadastro.ler(self.e.pasta_cadastro)
        except FileNotFoundError:
            return []

    # ---------------------------------------------------------------- índice de lojistas
    def _indice(self, ref=None):
        hoje, contratos, conds = ref or self._hoje(), self._contratos(), self._condicoes()
        idx = {}

        def lojista(chave, nome=""):
            return idx.setdefault(chave, {"chave": chave, "nome": nome, "contratos": [], "ecs": set(),
                                          "orbe": set(), "ponte": set()})

        for c in contratos:
            L = lojista(c["cnpj"])
            L["contratos"].append(c)
            if c.get("ec"):
                L["ecs"].add(c["ec"])
        ec_para = {ec: ch for ch, L in idx.items() for ec in L["ecs"]}
        for c in conds:                      # o cadastro liga o EC ao CNPJ (de-para, bloqueio...)
            if c["cnpj"] and c["ec_orbe"]:
                ec_para.setdefault(c["ec_orbe"], c["cnpj"])
        for c in conds:
            ch = c["cnpj"] or ("EC" + c["ec_orbe"] if c["ec_orbe"] else "")
            if ch:
                L = lojista(ch, c["lojista"])
                if c["ec_orbe"]:
                    L["ecs"].add(c["ec_orbe"])
        r = self.e.r
        if r:
            for l in r["dados"].get("orbe", []):
                L = lojista(ec_para.get(l["ec"]) or "EC" + l["ec"], l["nome"])
                L["ecs"].add(l["ec"])
                L["orbe"].add(l["nome"])
            for o in r["dados"].get("ponte", []):
                if o.get("cnpj"):
                    lojista(o["cnpj"], o.get("cliente") or "")["ponte"].add(o.get("cliente") or "")
        for ch, L in idx.items():
            L["conds"] = [c for c in conds if c["cnpj"] == ch or (not c["cnpj"] and c["ec_orbe"] and c["ec_orbe"] in L["ecs"])]
            L["vigente"] = self._contrato_vigente(L["contratos"], hoje)
            ref = L["vigente"] or (L["contratos"][-1] if L["contratos"] else None)
            if ref:
                L["nome"] = ref["lojista"]
            if not L["nome"]:
                L["nome"] = next(iter(sorted(L["orbe"] | L["ponte"])), None) or fmt_cnpj(ch)
        return idx

    @staticmethod
    def _contrato_vigente(contratos, hoje):
        ok = [c for c in contratos if not c["riscado"] and c["vigencia_ok"]
              and (c["inicio"] is None or c["inicio"] <= hoje) and (c["fim"] is None or c["fim"] >= hoje)]
        return max(ok, key=lambda c: (c["inicio"] or date.min, c["linha"])) if ok else None

    def _achar(self, chave):
        L = self._indice().get(_chave(chave))
        if L is None:
            raise ErroPedido("Lojista não encontrado.")
        return L

    # ---------------------------------------------------------------- estado das condições
    @staticmethod
    def _status(c, hoje):
        ini, fim = _data_cad(c.get("vigencia_inicio")), _data_cad(c.get("vigencia_fim"))
        if fim and fim < hoje:
            return "encerrada"
        if ini and ini > hoje:
            return "futura"
        return "ativa"

    def _selos(self, L, hoje):
        ativos = {c["tipo"] for c in L["conds"] if self._status(c, hoje) == "ativa"}
        selos = []
        if "ISENCAO" in ativos:
            selos.append({"codigo": "isencao", "texto": "isenção ativa"})
        if "TAXA_ESPECIAL" in ativos:
            selos.append({"codigo": "taxa_especial", "texto": "taxa especial"})
        if "BLOQUEIO_FATURAMENTO" in ativos:
            selos.append({"codigo": "bloqueado", "texto": "bloqueado"})
        if not L["vigente"]:
            if L["contratos"] and all(c["riscado"] for c in L["contratos"]):
                selos.append({"codigo": "inativo", "texto": "inativo na planilha"})
            else:
                selos.append({"codigo": "sem_contrato", "texto": "sem contrato"})
        if "NOTA_PENDENCIA" in ativos:
            selos.append({"codigo": "pendencia", "texto": "com nota de pendência"})
        return selos

    # ---------------------------------------------------------------- API de leitura
    def lista(self):
        hoje = self._hoje()
        itens = [{"chave": ch, "cnpj": "" if ch.startswith("EC") else fmt_cnpj(ch), "nome": L["nome"],
                  "ecs": sorted(L["ecs"]), "selos": self._selos(L, hoje)} for ch, L in self._indice().items()]
        itens.sort(key=lambda x: x["nome"].lower())
        return {"data_referencia": hoje.isoformat(), "clientes": itens, "cadastro_disponivel": cadastro is not None}

    def _taxa(self, L, faixa, hoje):
        base = {"faixa": faixa, "rotulo": ROTULO_FAIXA[faixa]}
        c = L["vigente"]
        linha = c or {"cnpj": L["chave"] if not L["chave"].startswith("EC") else "", "ec": None,
                      "taxas": {}, "spread": None, "linha": None, "inicio": None}
        valor, origem = None, ""
        if cadastro is not None:
            valor, origem = cadastro.taxa_efetiva(linha, L["conds"], hoje, faixa, ec=next(iter(sorted(L["ecs"])), None))
        elif c:
            valor, origem = (c["spread"] if faixa == "SPREAD_REMESSA" else c["taxas"].get(faixa)), f"planilha linha {c['linha']}"
        if origem.startswith("planilha"):
            if not c:
                return {**base, "valor": "—", "origem": "sem contrato vigente na planilha"}
            origem += f", desde {_br(c['inicio'])}" if c["inicio"] else ""
            if valor is None and faixa == "SPREAD_REMESSA":
                return {**base, "valor": SPREAD_PADRAO_TXT, "origem": origem + " (célula em branco = spread padrão de 1,5%, CC03)"}
            if valor is None:
                return {**base, "valor": "—", "origem": origem + " (sem taxa nesta faixa)"}
        for cod, txt in (("ISENCAO", "isenção"), ("TAXA_ESPECIAL", "taxa especial")):
            origem = origem.replace(cod, txt)
        return {**base, "valor": _pct_txt(valor, faixa), "origem": origem}

    def _condicao_json(self, c, hoje):
        campo = c["campo"]
        campo_txt = ", ".join(ROTULO_FAIXA.get(f.strip().upper(), f.strip()) for f in campo.split(",")) if campo else ""
        if campo.lower() == "todas":
            campo_txt = "todas as faixas"
        valor = c["valor"]
        if valor and c["tipo"] == "TAXA_ESPECIAL":
            valor = valor.replace(".", ",") + "%"
        return {"id": c["id_condicao"], "tipo": c["tipo"], "tipo_texto": TIPOS.get(c["tipo"], c["tipo"]),
                "status": self._status(c, hoje), "linha_negocio": LINHAS.get(c["linha_negocio"], c["linha_negocio"]),
                "campo": campo_txt, "valor": valor,
                "inicio": _br(_data_cad(c["vigencia_inicio"])), "fim": _br(_data_cad(c["vigencia_fim"])),
                "aprovado_por": c["aprovado_por"], "fonte": c["fonte"], "observacao": c["observacao"],
                "registrado_em": _br(_data_cad(c["data_registro"]))}

    def _tem_checkout(self, L):
        return bool(L["ecs"]) or bool(L["vigente"] and any(L["vigente"]["taxas"].get(f) is not None for f in FAIXAS_CHECKOUT))

    def _faturamento(self, L, codigos):
        txt = []
        bloq = bool(codigos & {"bloqueado", "sem_contrato"})
        if bloq:
            txt.append("Bloqueado: não é faturado até o Comercial confirmar a taxa (R15). "
                       "O repasse ao lojista continua normalmente (R59); só a cobrança da taxa fica suspensa.")
        else:
            if self._tem_checkout(L):
                t = ("Checkout (Orbe): 1 nota por mês, pela taxa contratada, com o resultado de vendas, antecipações, "
                     "estornos e reversões do mês (R10, R30).")
                if "isencao" in codigos:
                    t += " Com a isenção ativa a taxa é zero, então o saldo é zero e não sai nota (R31)."
                txt.append(t)
            if L["vigente"] or L["ponte"]:
                txt.append("Remessa (Ponte Câmbio): a Tarvo ganha 50% do spread realizado; esse valor entra na nota única "
                           "da Ponte Câmbio, não numa nota do lojista (R20, R32).")
        return txt or ["Sem informação suficiente para dizer como este lojista é faturado."]

    def _regras(self, L, codigos, hoje):
        ids = []
        if codigos & {"bloqueado", "sem_contrato"}:
            return [{"id": i, "texto": REGRAS[i]} for i in ("R15", "R54", "R59")]
        if self._tem_checkout(L):
            ids += ["R10", "R11", "R12", "R30", "R31"]
        if L["vigente"] or L["ponte"]:
            ids += ["R20", "R22", "R32"]
        if "isencao" in codigos:
            ids += ["R52", "R68"]
        regras = [{"id": i, "texto": REGRAS[i]} for i in dict.fromkeys(ids)]
        for c in L["conds"]:                      # texto da isenção gerado da própria condição, não fixo
            if c["tipo"] == "ISENCAO" and self._status(c, hoje) == "ativa":
                faixas = ("todas as faixas" if c["campo"].lower() == "todas"
                          else ", ".join(ROTULO_FAIXA.get(f.strip().upper(), f.strip()) for f in c["campo"].split(",")))
                fim = _br(_data_cad(c["vigencia_fim"]))
                regras.insert(0, {"id": f"Isenção {c['id_condicao']}", "texto": (
                    f"{L['nome']}: taxa zero em {faixas} ({LINHAS.get(c['linha_negocio'], c['linha_negocio'])}), de "
                    f"{_br(_data_cad(c['vigencia_inicio']))} {'até ' + fim if fim else 'sem data de fim'}; aprovada por "
                    f"{c['aprovado_por'] or 'não informado'}" + (f" (fonte {c['fonte']})" if c["fonte"] else "") +
                    ". Vale para a venda a partir do início da vigência; na antecipação, pela data da antecipação (R72).")})
        return regras

    def _mes(self, L):
        r = self.e.r
        if not r:
            return None
        ch = L["chave"]
        com = [c for c in r["comissoes"] if c["cnpj"] == ch]
        div = [d for d in r["divergencias"] if d["cnpj"] == ch]
        grupos = [g for g in ((r.get("investigacao") or {}).get("grupos") or []) if g.get("cnpj") == ch]
        digitos = lambda t: re.sub(r"\D", "", str(t or ""))
        pend = [p for p in r["pendencias"]
                if (not ch.startswith("EC") and ch in digitos(p.get("ref_origem")))
                or str(p.get("ref_origem", "")) in {"EC " + ec for ec in L["ecs"]}
                or (not ch.startswith("EC") and ch in digitos(p.get("motivo")))]

        def total(linha):
            xs = [c["comissao"] for c in com if c["linha_negocio"] == linha]
            return fmt_br(soma(xs)) if xs else None
        return {
            "competencia": r["competencia"],
            "comissao_checkout": total("CHECKOUT"), "comissao_remessa": total("REMESSA"),
            "divergencia_linhas": len(div),
            "divergencia_valor": fmt_br(soma(d["diferenca"] for d in div)) if div else None,
            "devolver_lojista": fmt_br(soma(Decimal(g["valor_devolver_lojista_brl"]) for g in grupos)) if grupos else None,
            "recuperar_parceiro": fmt_br(soma(Decimal(g["valor_recuperar_parceiro_brl"]) for g in grupos)) if grupos else None,
            "pendencias": [{"tipo": p["tipo"], "motivo": p["motivo"], "quem_decide": p["quem_decide"],
                            "valor": fmt_br(p["valor"]) if p.get("valor") is not None else None} for p in pend],
        }

    def ficha(self, chave, data=None):
        """data = data de referência das taxas (padrão: hoje). Texto inválido vira erro legível."""
        ref = _data_iso(data, "Data de referência") if data else None
        L = self._indice(ref).get(_chave(chave))
        if L is None:
            return None
        hoje = ref or self._hoje()
        comp = self._competencia_data()
        selos = self._selos(L, hoje)
        codigos = {s["codigo"] for s in selos}
        ordem = {"ativa": 0, "futura": 1, "encerrada": 2}
        conds = sorted((self._condicao_json(c, hoje) for c in L["conds"]), key=lambda c: (ordem[c["status"]], c["id"]))
        v = L["vigente"]
        return {
            "chave": L["chave"], "selos": selos, "data_referencia": hoje.isoformat(), "data_hoje": self._hoje().isoformat(),
            "data_competencia": comp.isoformat() if comp else None,
            "competencia": (self.e.r or {}).get("competencia"),
            "identificacao": {
                "nome": L["nome"], "razao_social_planilha": v["lojista"] if v else None,
                "cnpj": None if L["chave"].startswith("EC") else fmt_cnpj(L["chave"]),
                "ecs": sorted(L["ecs"]), "nomes_orbe": sorted(L["orbe"]), "nomes_ponte": sorted(L["ponte"]),
                "linha_planilha": v["linha"] if v else None, "obs_planilha": v["obs"] if v else None,
                "fechamento_rodado": self.e.r is not None,
            },
            "taxas": [self._taxa(L, f[0], hoje) for f in FAIXAS], "condicoes": conds,
            "faturamento": self._faturamento(L, codigos), "regras": self._regras(L, codigos, hoje), "mes": self._mes(L),
        }

    # ---------------------------------------------------------------- escrita (só no cadastro)
    def _exigir_cadastro(self):
        if cadastro is None:
            raise ErroPedido("O cadastro de condições ainda não está disponível neste programa.")

    def _usuario(self, d, acao):
        u = str(d.get("usuario") or "").strip()
        if not u:
            raise ErroPedido(f'Informe seu nome (campo "Seu nome") antes de {acao}.')
        return u

    def criar(self, d):
        self._exigir_cadastro()
        usuario = self._usuario(d, "salvar")
        L = self._achar(d.get("chave"))
        tipo = d.get("tipo")
        if tipo not in TIPOS:
            raise ErroPedido("Escolha o tipo da condição.")
        linha = d.get("linha_negocio") or "TODAS"
        if linha not in LINHAS:
            raise ErroPedido("Escolha a linha de negócio.")
        aprovado = str(d.get("aprovado_por") or "").strip()
        if tipo in TIPOS_COM_APROVACAO and aprovado not in APROVADORES:
            raise ErroPedido("Informe quem aprovou (Comercial ou Helena (Financeiro)): taxa e isenção só valem com aprovação.")
        inicio = _data_iso(d.get("vigencia_inicio"), "Início da vigência")
        fim = str(d.get("vigencia_fim") or "").strip()
        if fim and _data_iso(fim, "Fim da vigência") < inicio:
            raise ErroPedido("O fim da vigência não pode ser antes do início.")
        base = {"tipo": tipo, "linha_negocio": linha, "vigencia_inicio": inicio.isoformat(), "vigencia_fim": fim,
                "aprovado_por": aprovado, "fonte": str(d.get("fonte") or "").strip(),
                "observacao": str(d.get("observacao") or "").strip(),
                "cnpj": "" if L["chave"].startswith("EC") else L["chave"],
                "ec_orbe": next(iter(sorted(L["ecs"])), ""), "lojista": L["nome"], "campo": "", "valor": ""}
        linhas = []
        if tipo in ("ISENCAO", "TAXA_ESPECIAL"):
            faixas = d.get("faixas") or []
            if not faixas or any(f not in ROTULO_FAIXA for f in faixas):
                raise ErroPedido("Marque pelo menos uma faixa (débito, crédito, Pix, antecipação ou spread).")
            linhas_f = {LINHA_DA_FAIXA[f] for f in faixas}
            if linha != "TODAS" and linhas_f != {linha}:
                raise ErroPedido("Há faixa que não pertence à linha de negócio escolhida "
                                 "(o spread é da remessa; as demais são do checkout).")
            if tipo == "ISENCAO":
                if len(linhas_f) > 1:
                    raise ErroPedido("Uma isenção vale para uma linha só: registre o checkout e a remessa separadamente.")
                todas = set(faixas) == set(FAIXAS_CHECKOUT)
                linhas.append({**base, "linha_negocio": linhas_f.pop(), "campo": "todas" if todas else ",".join(faixas)})
            else:
                txt = str(d.get("valor") or "").strip().replace(",", ".")
                try:
                    v = Decimal(txt)
                except InvalidOperation:
                    raise ErroPedido("Informe o valor da taxa em % (ex.: 2,19).") from None
                if not 0 <= v <= 100:
                    raise ErroPedido("O valor da taxa deve estar entre 0 e 100%.")
                for f in faixas:
                    linhas.append({**base, "campo": f, "valor": format(v.normalize(), "f"), "linha_negocio": LINHA_DA_FAIXA[f]})
        elif tipo == "DE_PARA_EC":
            ec = so_digitos(d.get("ec_orbe"))
            if not ec:
                raise ErroPedido("Informe o código do EC Orbe que passa a valer para este lojista.")
            if not base["cnpj"]:
                raise ErroPedido("O de-para liga o EC a um CNPJ; este lojista ainda não tem CNPJ conhecido.")
            linhas.append({**base, "ec_orbe": ec})
        elif not base["observacao"]:
            raise ErroPedido('Explique o motivo em "Observação" (quem pediu e por quê).')
        else:
            linhas.append(base)
        try:
            criadas = self._gravar_todas(linhas, usuario)
        except ValueError as e:                      # CadastroInvalido: mensagem já em português
            raise ErroPedido(str(e)) from None
        ids = [c["id_condicao"] for c in criadas]
        return {"ids": ids, "aviso": f"Condição {', '.join(ids)} registrada para {L['nome']}. {AVISO_RODAR}",
                "ficha": self.ficha(L["chave"])}

    def _gravar_todas(self, linhas, usuario):
        """Tudo ou nada: se uma faixa for recusada, nenhuma fica gravada."""
        pasta = self.e.pasta_cadastro
        if len(linhas) > 1 and hasattr(cadastro, "adicionar_varias"):
            return cadastro.adicionar_varias(pasta, linhas, usuario)
        arquivos = [pasta / n for n in ("condicoes_comerciais.csv", "historico_alteracoes.csv")]
        antes = {a: a.read_bytes() for a in arquivos if a.exists()}
        try:
            return [cadastro.adicionar(pasta, l, usuario, hoje=self._hoje()) for l in linhas]
        except Exception:
            for a in arquivos:                   # desfaz as faixas já gravadas
                if a in antes:
                    a.write_bytes(antes[a])
                else:
                    a.unlink(missing_ok=True)
            raise

    def encerrar(self, id_condicao, d):
        self._exigir_cadastro()
        usuario = self._usuario(d, "encerrar")
        fim = _data_iso(d.get("data_fim"), "Data de fim")
        alvo = next((c for c in self._condicoes() if c["id_condicao"] == id_condicao), None)
        if alvo is None:
            raise ErroPedido("Condição não encontrada.")
        try:
            cadastro.encerrar(self.e.pasta_cadastro, id_condicao, fim.isoformat(), usuario)
        except ValueError as e:
            raise ErroPedido(str(e)) from None
        chave = alvo["cnpj"] or "EC" + alvo["ec_orbe"]
        return {"ids": [id_condicao], "aviso": f"Condição {id_condicao} encerrada em {_br(fim)}. {AVISO_RODAR}",
                "ficha": self.ficha(chave)}


def criar_handler(estado):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FechamentoTarvo/1.0"

        def log_message(self, fmt, *args):  # silencioso no console da analista
            pass

        def _enviar(self, codigo, corpo, tipo, extra=None):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, obj, codigo=200):
            self._enviar(codigo, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8")

        def do_GET(self):
            caminho = self.path.split("?", 1)[0]
            if caminho in ("/", "/index.html"):
                self._enviar(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
            elif caminho == "/api/estado":
                with estado.lock:
                    self._json(estado.json())
            elif caminho.startswith("/api/baixar/"):
                nome = unquote(caminho[len("/api/baixar/"):])
                with estado.lock:
                    arq = estado.pasta / "saida" / nome if estado.resultado else None
                if nome not in NOMES_SAIDA or arq is None or not arq.exists():
                    return self._json({"erro": "arquivo não disponível"}, 404)
                self._enviar(200, arq.read_bytes(), "text/csv; charset=utf-8",
                             {"Content-Disposition": f'attachment; filename="{nome}"'})
            elif caminho == "/api/clientes":
                with estado.lock:
                    self._json(estado.clientes.lista())
            elif caminho.startswith("/api/clientes/"):
                data = parse_qs(urlsplit(self.path).query).get("data", [None])[0]
                try:
                    with estado.lock:
                        f = estado.clientes.ficha(unquote(caminho[len("/api/clientes/"):]), data)
                except ErroPedido as e:
                    return self._json({"erro": str(e)}, 400)
                self._json(f if f else {"erro": "Lojista não encontrado."}, 200 if f else 404)
            elif caminho == "/api/baixar-decisoes":
                with estado.lock:
                    if not estado.dossie:
                        return self._json({"erro": "rode o fechamento primeiro"}, 404)
                    corpo = estado.csv_decisoes().encode("utf-8")
                self._enviar(200, corpo, "text/csv; charset=utf-8",
                             {"Content-Disposition": 'attachment; filename="decisoes_investigacao.csv"'})
            elif caminho == "/api/baixar-tudo":
                with estado.lock:
                    if not estado.resultado:
                        return self._json({"erro": "rode o fechamento primeiro"}, 404)
                    pasta = estado.pasta / "saida"
                    comp = estado.resultado["competencia"].replace("/", "-")
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for n, _ in SAIDAS:
                        if (pasta / n).exists():
                            z.write(pasta / n, n)
                self._enviar(200, buf.getvalue(), "application/zip",
                             {"Content-Disposition": f'attachment; filename="fechamento_{comp}.zip"'})
            else:
                self._json({"erro": "não encontrado"}, 404)

        def do_POST(self):
            caminho = self.path.split("?", 1)[0]
            tam = int(self.headers.get("Content-Length") or 0)
            if tam > TAMANHO_MAXIMO:
                return self._json({"erro": "arquivo grande demais"}, 413)
            corpo = self.rfile.read(tam) if tam else b""
            if caminho == "/api/enviar":
                nome = unquote(self.headers.get("X-Nome-Arquivo", ""))
                usuario = unquote(self.headers.get("X-Usuario", "")).strip()
                mes = self.headers.get("X-Mes")
                with estado.lock:
                    if mes and mes != estado.mes:       # aba desatualizada: não grava no mês errado
                        return self._json({"erro": f"O mês da tela mudou para {estado.mes}; recarregue a página."}, 409)
                    r = estado.receber(nome, corpo, usuario)
                    d = estado.json()
                d["envio"] = r
                self._json(d)
            elif caminho in ("/api/mes", "/api/remover"):
                try:
                    pedido = json.loads(corpo.decode("utf-8") or "{}")
                    if not isinstance(pedido, dict):
                        raise ValueError
                except ValueError:
                    return self._json({"erro": "pedido inválido"}, 400)
                with estado.lock:
                    if caminho == "/api/mes":
                        ok, msg = estado.escolher_mes(pedido.get("mes"))
                    else:
                        ok, msg = estado.remover(pedido.get("arquivo"), str(pedido.get("usuario") or "").strip())
                    d = estado.json()
                d["aviso"] = None if ok else msg
                self._json(d, 200 if ok else 400)
            elif caminho == "/api/rodar":
                with estado.lock:
                    estado.rodar()
                    self._json(estado.json())
            elif caminho == "/api/ia/gerar":
                with estado.lock:
                    ok, msg = estado.gerar_hipoteses()
                    d = estado.json()
                d["aviso_ia"] = None if ok else msg
                self._json(d, 200 if ok else 409)
            elif caminho == "/api/ia/decidir":
                try:
                    pedido = json.loads(corpo.decode("utf-8") or "{}")
                except ValueError:
                    return self._json({"erro": "pedido inválido"}, 400)
                with estado.lock:
                    ok, msg = estado.decidir(pedido)
                    d = estado.json()
                d["aviso_ia"] = None if ok else msg
                self._json(d, 200 if ok else 400)
            elif caminho == "/api/condicoes" or (caminho.startswith("/api/condicoes/") and caminho.endswith("/encerrar")):
                try:
                    pedido = json.loads(corpo.decode("utf-8") or "{}")
                    if not isinstance(pedido, dict):
                        raise ValueError
                except ValueError:
                    return self._json({"erro": "Pedido inválido."}, 400)
                try:
                    with estado.lock:
                        if caminho == "/api/condicoes":
                            res = estado.clientes.criar(pedido)
                        else:
                            res = estado.clientes.encerrar(unquote(caminho[len("/api/condicoes/"):-len("/encerrar")]), pedido)
                except ErroPedido as e:
                    return self._json({"erro": str(e)}, 400)
                self._json(res)
            elif caminho == "/api/limpar":
                with estado.lock:
                    estado.recomecar()
                    self._json(estado.json())
            else:
                self._json({"erro": "não encontrado"}, 404)

    return Handler


PORTA_PADRAO = 8765
TITULO_TELA = "Fechamento mensal"


class ServidorExclusivo(ThreadingHTTPServer):
    """No Windows, SO_REUSEADDR (padrão do http.server) deixa dois processos escutarem a MESMA porta e o
    navegador pode falar com a versão velha. Aqui a porta é exclusiva: ocupada -> OSError -> próxima porta."""
    allow_reuse_address = os.name != "nt"     # Linux/macOS: reuse só evita TIME_WAIT, não permite bind duplo

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def tela_existente(porta, timeout=1.0):
    """Já há uma tela do fechamento respondendo nesta porta? (GET / com o título da página)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/", timeout=timeout) as r:
            return TITULO_TELA in r.read(4096).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - porta livre, outro programa, sem resposta...
        return False


def mensagens_inicio(porta_obtida, porta_pedida=PORTA_PADRAO, havia_tela=False):
    url = f"http://127.0.0.1:{porta_obtida}/"
    linhas = ["Fechamento mensal - Tarvo"]
    if havia_tela and porta_obtida != porta_pedida:
        linhas += ["", "ATENÇÃO: já existe uma tela aberta em http://127.0.0.1:%d - feche a outra janela preta; "
                   "abrindo esta em :%d" % (porta_pedida, porta_obtida), ""]
    elif porta_obtida != porta_pedida:
        linhas.append(f"(a porta {porta_pedida} está ocupada por outro programa; usando {porta_obtida})")
    linhas += [f"A tela está aberta em: {url}", "Se o navegador não abrir sozinho, copie o endereço acima.",
               "Para encerrar, feche esta janela (ou Ctrl+C)."]
    return url, linhas


def criar_servidor(porta=PORTA_PADRAO, pasta_meses=PASTA_MESES, tentativas=20, cliente_ia=None, raiz_ia=None,
                   **opcoes_estado):
    """Cria o servidor em 127.0.0.1. Se a porta estiver ocupada, tenta as seguintes. porta=0 = qualquer livre.
    cliente_ia/raiz_ia: injeção para testes (cliente falso da API; pasta onde procurar o .env)."""
    estado = Estado(pasta_meses, cliente_ia=cliente_ia, raiz_ia=raiz_ia, **opcoes_estado)
    handler = criar_handler(estado)
    ultimo = None
    for p in ([0] if porta == 0 else range(porta, porta + tentativas)):
        try:
            srv = ServidorExclusivo(("127.0.0.1", p), handler)
            srv.daemon_threads = True
            srv.estado = estado
            return srv
        except OSError as e:
            ultimo = e
    raise OSError(f"nenhuma porta livre entre {porta} e {porta + tentativas - 1}: {ultimo}")


def main(abrir_navegador=True):
    havia_tela = tela_existente(PORTA_PADRAO)
    srv = criar_servidor(PORTA_PADRAO)
    url, linhas = mensagens_inicio(srv.server_address[1], PORTA_PADRAO, havia_tela)
    print("\n".join(linhas))
    if abrir_navegador:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
