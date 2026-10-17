"""Interface web local do fechamento mensal (só biblioteca padrão).

Escuta apenas em 127.0.0.1. Não calcula nada: recebe os arquivos, chama
src.fechamento.executar() e devolve o resumo e os CSVs gerados.

Cada execução grava em execucoes/<AAAA-MM-DD_HHMMSS>/entrada e /saida.
"""
import csv
import io
import json
import re
import threading
import traceback
import webbrowser
import zipfile
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from src import config, fechamento
from src.dinheiro import fmt_br, soma
from src.leitores import _glob_para_regex

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = Path(__file__).resolve().parent / "pagina.html"
TAMANHO_MAXIMO = 200 * 1024 * 1024  # 200 MB por arquivo

ROTULOS = {
    "orbe": "Relatório Orbe",
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
    }


def _mensagem_erro(e):
    """Erro legível: tipo + mensagem, sem stack trace."""
    msg = str(e).strip() or e.__class__.__name__
    dicas = {
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


class Estado:
    """Uma execução em andamento por vez (uso local, uma analista)."""

    def __init__(self, pasta_execucoes):
        self.pasta_execucoes = Path(pasta_execucoes)
        self.lock = threading.Lock()
        self.recomecar()

    def recomecar(self):
        self.pasta = None
        self.arquivos = {}  # chave -> {"nome", "tamanho"}
        self.resultado = None
        self.erro = None

    def _garantir_pasta(self):
        if self.pasta is None:
            base = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            pasta, i = self.pasta_execucoes / base, 1
            while pasta.exists():
                i += 1
                pasta = self.pasta_execucoes / f"{base}_{i}"
            (pasta / "entrada").mkdir(parents=True)
            self.pasta = pasta
        return self.pasta

    def receber(self, nome, conteudo):
        nome = _nome_seguro(nome)
        chave = reconhecer(nome) if nome else None
        if chave is None:
            return {"nome": nome, "reconhecido": None}
        entrada = self._garantir_pasta() / "entrada"
        anterior = self.arquivos.get(chave)
        if anterior and anterior["nome"] != nome:
            (entrada / anterior["nome"]).unlink(missing_ok=True)
        (entrada / nome).write_bytes(conteudo)
        self.arquivos[chave] = {"nome": nome, "tamanho": len(conteudo)}
        self.resultado, self.erro = None, None  # entrada mudou: resultado antigo não vale
        return {"nome": nome, "reconhecido": chave}

    def rodar(self):
        if len(self.arquivos) != len(config.PADROES_ARQUIVOS):
            self.erro = {"titulo": "Faltam arquivos.", "detalhe": "Envie os 6 arquivos antes de rodar."}
            return
        saida = self.pasta / "saida"
        try:
            r = fechamento.executar(self.pasta / "entrada", saida)
            self.resultado = resumo_dict(r)
            self.erro = None
        except Exception as e:  # noqa: BLE001 - mostrado à analista de forma legível
            traceback.print_exc()
            self.resultado, self.erro = None, _mensagem_erro(e)

    def saidas(self):
        if not self.resultado:
            return []
        pasta = self.pasta / "saida"
        return [{"nome": n, "descricao": d, "linhas": _contar_linhas(pasta / n)}
                for n, d in SAIDAS if (pasta / n).exists()]

    def json(self):
        d = {
            "esperados": [{"chave": k, "rotulo": ROTULOS.get(k, k), "padrao": p,
                           **(self.arquivos.get(k) or {})}
                          for k, p in config.PADROES_ARQUIVOS.items()],
            "pronto": len(self.arquivos) == len(config.PADROES_ARQUIVOS),
            "pasta": str(self.pasta) if self.pasta else None,
            "resultado": self.resultado,
            "erro": self.erro,
            "saidas": self.saidas(),
        }
        if self.resultado and (self.pasta / "saida" / "pendencias.csv").exists():
            d["previa_pendencias"] = _previa(self.pasta / "saida" / "pendencias.csv")
        return d


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
                with estado.lock:
                    r = estado.receber(nome, corpo)
                    d = estado.json()
                d["envio"] = r
                self._json(d)
            elif caminho == "/api/rodar":
                with estado.lock:
                    estado.rodar()
                    self._json(estado.json())
            elif caminho == "/api/limpar":
                with estado.lock:
                    estado.recomecar()
                    self._json(estado.json())
            else:
                self._json({"erro": "não encontrado"}, 404)

    return Handler


def criar_servidor(porta=8765, pasta_execucoes=RAIZ / "execucoes", tentativas=20):
    """Cria o servidor em 127.0.0.1. Se a porta estiver ocupada, tenta as seguintes. porta=0 = qualquer livre."""
    estado = Estado(pasta_execucoes)
    handler = criar_handler(estado)
    ultimo = None
    for p in ([0] if porta == 0 else range(porta, porta + tentativas)):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), handler)
            srv.daemon_threads = True
            srv.estado = estado
            return srv
        except OSError as e:
            ultimo = e
    raise OSError(f"nenhuma porta livre entre {porta} e {porta + tentativas - 1}: {ultimo}")


def main(abrir_navegador=True):
    srv = criar_servidor()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print("Fechamento mensal - Tarvo")
    print(f"A tela está aberta em: {url}")
    print("Se o navegador não abrir sozinho, copie o endereço acima.")
    print("Para encerrar, feche esta janela (ou Ctrl+C).")
    if abrir_navegador:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
