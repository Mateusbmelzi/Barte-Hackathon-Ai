"""Interface web local do fechamento mensal (só biblioteca padrão).

Escuta apenas em 127.0.0.1. Não calcula nada: recebe os arquivos, chama
src.fechamento.executar() e devolve o resumo e os CSVs gerados.

Cada execução grava em execucoes/<AAAA-MM-DD_HHMMSS>/entrada e /saida.
Investigação de divergências (PLANO_IA_01 Fase 3): o dossiê vem de saida/investigacao/; as hipóteses
da IA (src/ia.py) e as decisões da analista ficam na pasta da execução (investigacao_ia.json e
decisoes_investigacao.csv), nunca em saida/.
"""
import csv
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
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from src import config, fechamento, ia
from src.dinheiro import fmt_br, soma
from src.leitores import _glob_para_regex

RAIZ = Path(__file__).resolve().parent.parent
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

COLUNAS_DECISOES = ["id_grupo", "lojista", "hipotese_n", "causa", "decisao", "comentario", "analista",
                    "data_hora", "modelo_resposta", "versao_prompt"]
DECISOES = ("ACEITA", "RECUSADA")
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


class Estado:
    """Uma execução em andamento por vez (uso local, uma analista).
    cliente_ia: cliente da API injetável (testes); None = ia.investigar cria o cliente real com a chave."""

    def __init__(self, pasta_execucoes, cliente_ia=None, raiz_ia=None):
        self.pasta_execucoes = Path(pasta_execucoes)
        self.cliente_ia = cliente_ia
        self.raiz_ia = raiz_ia
        self.lock = threading.Lock()
        self.geracao = 0          # muda a cada execução: resposta da IA de execução antiga é descartada
        self.recomecar()

    def recomecar(self):
        self.pasta = None
        self.arquivos = {}  # chave -> {"nome", "tamanho"}
        self.resultado = None
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
        if not self.ia_resultado:
            return False, "Gere as hipóteses antes de decidir."
        g = next((x for x in self.ia_resultado.get("grupos", []) if x.get("id_grupo") == d.get("id_grupo")), None)
        try:
            n = int(d.get("hipotese_n"))
        except (TypeError, ValueError):
            n = 0
        if g is None or not 1 <= n <= len(g.get("hipoteses") or []):
            return False, "Hipótese não encontrada."
        self.decisoes[(g["id_grupo"], n)] = {
            "id_grupo": g["id_grupo"], "lojista": g.get("lojista") or "", "hipotese_n": n,
            "causa": g["hipoteses"][n - 1]["causa"], "decisao": d["decisao"],
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
            "decisoes": [self.decisoes[k] for k in sorted(self.decisoes)],
        }

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
        (entrada / nome).write_bytes(conteudo)
        if chave in config.FONTES_MULTIPLAS:
            # Orbe: vários arquivos no mês (relatório + ajustes). Mesmo nome = substitui; nome novo = soma.
            tamanhos = dict(self.arquivos.get(chave, {}).get("tamanhos", {}))
            tamanhos[nome] = len(conteudo)
            nomes = sorted(tamanhos, key=str.lower)
            self.arquivos[chave] = {"nome": ", ".join(nomes), "nomes": nomes, "tamanhos": tamanhos,
                                    "tamanho": sum(tamanhos.values())}
        else:
            anterior = self.arquivos.get(chave)
            if anterior and anterior["nome"] != nome:
                (entrada / anterior["nome"]).unlink(missing_ok=True)
            self.arquivos[chave] = {"nome": nome, "tamanho": len(conteudo)}
        self.resultado, self.erro = None, None  # entrada mudou: resultado antigo não vale
        self._limpar_investigacao()
        return {"nome": nome, "reconhecido": chave}

    def pronto(self):
        """Uma fonte de cada tipo, com pelo menos 1 arquivo da Orbe (aceita N)."""
        return all(k in self.arquivos for k in config.PADROES_ARQUIVOS)

    def rodar(self):
        if not self.pronto():
            self.erro = {"titulo": "Faltam arquivos.",
                         "detalhe": "Envie os arquivos do mês (Orbe, taxas, Ponte, plano de contas e os dois extratos) antes de rodar."}
            return
        saida = self.pasta / "saida"
        self._limpar_investigacao()
        try:
            r = fechamento.executar(self.pasta / "entrada", saida)
            self.resultado = resumo_dict(r)
            self.erro = None
            self.dossie = r.get("investigacao")
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
            "pronto": self.pronto(),
            "pasta": str(self.pasta) if self.pasta else None,
            "resultado": self.resultado,
            "erro": self.erro,
            "saidas": self.saidas(),
            "investigacao": self.json_investigacao(),
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
                with estado.lock:
                    r = estado.receber(nome, corpo)
                    d = estado.json()
                d["envio"] = r
                self._json(d)
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


def criar_servidor(porta=PORTA_PADRAO, pasta_execucoes=RAIZ / "execucoes", tentativas=20, cliente_ia=None, raiz_ia=None):
    """Cria o servidor em 127.0.0.1. Se a porta estiver ocupada, tenta as seguintes. porta=0 = qualquer livre.
    cliente_ia/raiz_ia: injeção para testes (cliente falso da API; pasta onde procurar o .env)."""
    estado = Estado(pasta_execucoes, cliente_ia=cliente_ia, raiz_ia=raiz_ia)
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
