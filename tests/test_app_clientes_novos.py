"""Cliente novo na tela: flag no estado, upload do contrato, análise (IA com stub), revisão, confirmar/descartar e fluxo sem IA.
Tudo em tmp_path (o cadastro é uma cópia); a IA nunca é chamada de verdade."""
import json
import shutil
import threading
import time
import urllib.error
import urllib.request
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import servidor
from src import cadastro, clientes_novos, contatos
from src import ia_contrato as ia_real

ATLAS = "39566044000119"
EC_ATLAS = "1076801732"
TEXTO = "CONTRATO FICTICIO. Pix: 0,95%. Isencao de 01/10/2026 a 31/12/2026. Vigencia a partir de 01/10/2026."


def _extracao_falsa():
    return {"partes": {"lojista": "Atlas", "cnpj": ATLAS}, "vigencia_inicio": "2026-10-01", "vigencia_fim": "2028-09-30",
            "taxas": [{"faixa": "PIX", "valor": "0,95", "evidencia": "Pix: 0,95%"},
                      {"faixa": "DEBITO", "valor": "1,59", "evidencia": "Debito: 1,59%"}],
            "condicoes_especiais": [], "regras_negocio": [{"assunto": "Repasse", "texto": "Dias 10 e 24.", "evidencia": "dias 10 e 24"}],
            "acoes_sugeridas": [{"destino": "ORBE", "motivo": "Avisar a Orbe sobre a taxa negociada.", "assunto": "Taxa negociada Atlas",
                                 "corpo": "Olá,\nA Atlas tem Pix a 0,95%.\nAbraço"}],
            "duvidas": ["O contrato não diz se a taxa vale para estornos."], "aviso": "Extração da IA — revise antes de confirmar.",
            "modelo": "falso", "versao_prompt": "t", "ajustes": [], "erro": ""}


def _stub(disponivel=True, extracao=None):
    chamadas = []

    def extrair(texto, cliente, contexto=None, *, cliente_ia=None, raiz=None):
        chamadas.append(cliente)
        return extracao if extracao is not None else _extracao_falsa()

    return SimpleNamespace(ler_texto=lambda b, nome="": b.decode("utf-8") if isinstance(b, bytes) else str(b), extrair=extrair,
                           para_cadastro=ia_real.para_cadastro, disponivel=lambda raiz=None: (disponivel, "" if disponivel else "Chave não configurada."),
                           chamadas=chamadas)


@pytest.fixture()
def ctx(tmp_path, raiz, resultado, monkeypatch):
    pasta = tmp_path / "cadastro"
    shutil.copytree(raiz / "cadastro", pasta, ignore=shutil.ignore_patterns("contratos"))
    for c in contatos.para("LOJISTA", ATLAS, pasta):          # a cópia parte sem contato do lojista novo
        contatos.remover(pasta, c["id_contato"], "teste")
    srv = servidor.criar_servidor(porta=0, pasta_meses=tmp_path / "meses", pasta_cadastro=pasta)
    srv.estado.r = resultado                       # como se o fechamento tivesse rodado (traz r["clientes_novos"])
    monkeypatch.setattr(servidor, "ia_contrato", _stub())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield SimpleNamespace(url=f"http://127.0.0.1:{srv.server_address[1]}", pasta=pasta, estado=srv.estado, mp=monkeypatch)
    srv.shutdown()
    srv.server_close()


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(url, corpo):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _upload(ctx, nome="contrato.txt", conteudo=TEXTO.encode(), usuario="Helena"):
    req = urllib.request.Request(f"{ctx.url}/api/novos/{ATLAS}/analisar", data=conteudo, method="POST",
                                 headers={"X-Nome-Arquivo": nome, "X-Usuario": usuario})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _esperar_analise(ctx):
    for _ in range(100):
        st, d = _get(f"{ctx.url}/api/novos/{ATLAS}")
        if d["analise"] or d["erro_analise"]:
            return d
        time.sleep(0.05)
    raise AssertionError("a análise não terminou")


def _condicoes_atlas(ctx):
    return [c for c in cadastro.ler(ctx.pasta) if c["cnpj"] == ATLAS and c["tipo"] == "TAXA_ESPECIAL"]


# ------------------------------------------------ a flag chega à tela
def test_estado_traz_clientes_novos_e_lista_de_clientes(ctx):
    st, e = _get(ctx.url + "/api/estado")
    novos = {i["chave"]: i for i in e["clientes_novos"]["itens"]}
    a = novos[ATLAS]
    assert a["status"] == "CONTRATO_PENDENTE" and a["no_fechamento"] and a["ec_orbe"] == EC_ATLAS and a["qtd_transacoes"] > 0
    assert a["status_texto"].startswith("NOVO") and a["contratos"] == []
    assert "disponivel" in e["clientes_novos"]["ia"]
    lista = _get(ctx.url + "/api/clientes")[1]["clientes"]
    atlas = next(c for c in lista if c["chave"] == ATLAS)
    assert "novo" in [s["codigo"] for s in atlas["selos"]]
    ficha = _get(f"{ctx.url}/api/clientes/{ATLAS}")[1]
    assert ficha["novo"]["status"] == "CONTRATO_PENDENTE" and ficha["novo"]["contratos"] == []


def test_cliente_novo_fora_da_planilha_entra_na_lista(ctx, resultado):
    ctx.estado.r = {**resultado, "clientes_novos": [{"cnpj": "", "ec_orbe": "9999999999", "nome": "LOJA NOVA FICTICIA", "origem": "ORBE",
                                                       "qtd_transacoes": 3, "valor_bruto": "1500.00", "motivo": "novo", "status": "CONTRATO_PENDENTE"}]}
    lista = _get(ctx.url + "/api/clientes")[1]["clientes"]
    loja = next(c for c in lista if c["nome"] == "LOJA NOVA FICTICIA")
    assert loja["chave"] == "EC9999999999" and loja["selos"][0]["codigo"] == "novo" and loja["ecs"] == ["9999999999"]


# ------------------------------------------------ upload + análise
def test_upload_analisa_guarda_contrato_e_persiste_estado(ctx):
    st, r = _upload(ctx)
    assert st == 200 and r["estado"] == "analisando"
    d = _esperar_analise(ctx)
    assert d["status"] == "CONTRATO_ANALISADO" and d["analise"]["arquivo"] == "contrato.txt"
    assert (ctx.pasta / "contratos" / ATLAS / "contrato.txt").read_bytes() == TEXTO.encode()
    ext = d["analise"]["extracao"]
    assert [t["faixa"] for t in ext["taxas"]] == ["PIX", "DEBITO"] and ext["duvidas"]
    acao = ext["acoes_sugeridas"][0]
    assert acao["destino"] == "ORBE" and acao["papel"] == "ORBE" and "@" in acao["email"]        # e-mail vem dos contatos
    assert d["contratos"][0]["nome"] == "contrato.txt"
    assert next(c for c in clientes_novos.ler(ctx.pasta) if c["cnpj"] == ATLAS)["status"] == "CONTRATO_ANALISADO"
    assert _condicoes_atlas(ctx) == []                                                          # analisar nunca grava no cadastro
    # reabrir o popup mostra a análise guardada (mesmo depois de um novo estado)
    e = _get(ctx.url + "/api/estado")[1]
    assert next(i for i in e["clientes_novos"]["itens"] if i["chave"] == ATLAS)["status"] == "CONTRATO_ANALISADO"
    assert _upload(ctx)[0] == 200 and len(list((ctx.pasta / "contratos" / ATLAS).glob("contrato*"))) == 1   # mesmo conteúdo: não duplica


def test_upload_nao_sobrescreve_arquivo_diferente_de_mesmo_nome(ctx):
    _upload(ctx)
    _esperar_analise(ctx)
    _post(f"{ctx.url}/api/novos/{ATLAS}/descartar", {"usuario": "Helena"})
    assert _upload(ctx, conteudo=(TEXTO + " Revisado.").encode())[0] == 200
    nomes = sorted(p.name for p in (ctx.pasta / "contratos" / ATLAS).glob("contrato*"))
    assert nomes == ["contrato.txt", "contrato_v2.txt"]


def test_upload_valida_nome_formato_e_arquivo(ctx):
    st, r = _upload(ctx, usuario="")
    assert st == 400 and "Seu nome" in r["erro"]
    st, r = _upload(ctx, nome="contrato.exe")
    assert st == 400 and ".pdf" in r["erro"]
    st, r = _upload(ctx, conteudo=b"")
    assert st == 400
    assert _get(f"{ctx.url}/api/novos/999")[0] == 404


def test_erro_da_ia_aparece_e_nao_marca_analisado(ctx):
    ctx.mp.setattr(servidor, "ia_contrato", _stub(extracao={**_extracao_falsa(), "erro": "IA indisponível: sem chave"}))
    assert _upload(ctx)[0] == 200
    d = _esperar_analise(ctx)
    assert d["analise"] is None and "sem chave" in d["erro_analise"] and d["status"] == "CONTRATO_PENDENTE"


# ------------------------------------------------ confirmar
def test_confirmar_sem_aprovado_por_e_400_e_nada_grava(ctx):
    _upload(ctx)
    _esperar_analise(ctx)
    antes = len(cadastro.ler(ctx.pasta))
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {"usuario": "Helena"})
    assert st == 400 and "aprovou" in r["erro"]
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {"usuario": "Helena", "aprovado_por": "A IA"})
    assert st == 400
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {"aprovado_por": "Comercial"})
    assert st == 400 and "Seu nome" in r["erro"]
    assert len(cadastro.ler(ctx.pasta)) == antes
    assert _get(f"{ctx.url}/api/novos/{ATLAS}")[1]["status"] == "CONTRATO_ANALISADO"


def test_confirmar_grava_condicoes_marca_confirmado_e_cria_contato(ctx):
    _upload(ctx)
    d = _esperar_analise(ctx)
    antes = len(cadastro.ler(ctx.pasta))
    # a analista desmarca o débito e corrige o Pix de 0,95 para 0,90
    corpo = {"usuario": "Helena", "aprovado_por": "Comercial", "taxas": [{"idx": 0, "valor": "0,90"}], "condicoes": [],
             "email_lojista": "financeiro@atlas.example.com"}
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", corpo)
    assert st == 200, r
    assert len(r["ids"]) == 1 and "Rode o fechamento de novo" in r["aviso"]
    novas = _condicoes_atlas(ctx)
    assert len(cadastro.ler(ctx.pasta)) == antes + 1
    pix = next(c for c in novas if c["campo"] == "PIX")
    assert Decimal(str(pix["valor"]).replace(",", ".")) == Decimal("0.90") and pix["aprovado_por"] == "Comercial"
    assert not any(c["campo"] == "DEBITO" for c in novas)
    assert d["analise"]["extracao"]["taxas"][0]["valor"] == "0,95"                               # a extração original fica guardada
    assert next(c for c in clientes_novos.ler(ctx.pasta) if c["cnpj"] == ATLAS)["status"] == "CONFIRMADO"
    assert r["cliente"]["status"] == "CONFIRMADO" and r["cliente"]["analise"]["aprovado_por"] == "Comercial"
    assert [c["email"] for c in contatos.para("LOJISTA", ATLAS, ctx.pasta)] == ["financeiro@atlas.example.com"]
    # confirmar duas vezes não grava de novo
    assert _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", corpo)[0] == 400
    assert len(cadastro.ler(ctx.pasta)) == antes + 1


def test_confirmar_sem_email_do_lojista_avisa_para_completar_nos_contatos(ctx):
    _upload(ctx)
    _esperar_analise(ctx)
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {"usuario": "Helena", "aprovado_por": "Helena (Financeiro)"})
    assert st == 200, r
    assert any("aba Contatos" in a for a in r["avisos"])
    assert contatos.para("LOJISTA", ATLAS, ctx.pasta) == []


def test_confirmar_com_contato_do_lojista_ja_cadastrado_nao_duplica(ctx):
    contatos.adicionar(ctx.pasta, {"papel": "LOJISTA", "cnpj": ATLAS, "nome": "Atlas", "email": "ja@atlas.example.com"}, "teste")
    _upload(ctx)
    _esperar_analise(ctx)
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {"usuario": "Helena", "aprovado_por": "Comercial", "email_lojista": "outro@atlas.example.com"})
    assert st == 200, r
    assert not any("Contatos" in a for a in r["avisos"])
    assert [c["email"] for c in contatos.para("LOJISTA", ATLAS, ctx.pasta)] == ["ja@atlas.example.com"]


def test_selecao_invalida_ou_valor_invalido_e_400(ctx):
    _upload(ctx)
    _esperar_analise(ctx)
    antes = len(cadastro.ler(ctx.pasta))
    base = {"usuario": "Helena", "aprovado_por": "Comercial"}
    assert _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {**base, "taxas": [{"idx": 7}]})[0] == 400
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {**base, "taxas": [{"idx": 0, "valor": "abc"}]})
    assert st == 400 and "inválido" in r["erro"]
    assert _post(f"{ctx.url}/api/novos/{ATLAS}/confirmar", {**base, "taxas": [{"idx": 0, "valor": "250"}]})[0] == 400
    assert len(cadastro.ler(ctx.pasta)) == antes


# ------------------------------------------------ descartar e e-mail
def test_descartar_nao_grava_e_volta_a_pendente(ctx):
    _upload(ctx)
    _esperar_analise(ctx)
    antes = len(cadastro.ler(ctx.pasta))
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/descartar", {"usuario": "Helena"})
    assert st == 200 and r["cliente"]["analise"] is None and r["cliente"]["status"] == "CONTRATO_PENDENTE"
    assert len(cadastro.ler(ctx.pasta)) == antes
    assert next(c for c in clientes_novos.ler(ctx.pasta) if c["cnpj"] == ATLAS)["status"] == "CONTRATO_PENDENTE"
    assert list((ctx.pasta / "contratos" / ATLAS).glob("analise_descartada_*.json"))              # a análise antiga fica guardada
    assert (ctx.pasta / "contratos" / ATLAS / "contrato.txt").exists()                           # o contrato também
    assert _post(f"{ctx.url}/api/novos/{ATLAS}/descartar", {})[0] == 400


def test_preparar_email_gera_mailto_com_crlf_e_registra(ctx):
    _upload(ctx)
    d = _esperar_analise(ctx)
    a = d["analise"]["extracao"]["acoes_sugeridas"][0]
    st, r = _post(f"{ctx.url}/api/novos/{ATLAS}/email", {"usuario": "Helena", "idx": a["idx"], "para": a["email"], "assunto": a["assunto"], "corpo": a["corpo"]})
    assert st == 200 and r["mailto"].startswith("mailto:") and "%0D%0A" in r["mailto"] and "Taxa%20negociada" in r["mailto"]
    assert r["cliente"]["analise"]["extracao"]["acoes_sugeridas"][0]["preparada"] is True
    assert _post(f"{ctx.url}/api/novos/{ATLAS}/email", {"usuario": "Helena", "para": "sem-arroba", "assunto": "x"})[0] == 400
    assert _post(f"{ctx.url}/api/novos/{ATLAS}/email", {"para": a["email"], "assunto": "x"})[0] == 400


# ------------------------------------------------ sem IA
def test_sem_ia_guarda_contrato_e_oferece_cadastro_manual(ctx):
    ctx.mp.setattr(servidor, "ia_contrato", _stub(disponivel=False))
    e = _get(ctx.url + "/api/estado")[1]
    assert e["clientes_novos"]["ia"]["disponivel"] is False and "Chave" in e["clientes_novos"]["ia"]["motivo"]
    st, r = _upload(ctx)
    assert st == 200 and r["estado"] == "sem_ia" and "manualmente" in r["aviso"]
    assert (ctx.pasta / "contratos" / ATLAS / "contrato.txt").exists()
    d = _get(f"{ctx.url}/api/novos/{ATLAS}")[1]
    assert d["analise"] is None and d["status"] == "CONTRATO_PENDENTE" and d["contratos"][0]["nome"] == "contrato.txt"
    # o cadastro manual (formulário "+ Nova condição") continua funcionando para o cliente novo
    st, r = _post(ctx.url + "/api/condicoes", {"chave": ATLAS, "tipo": "TAXA_ESPECIAL", "linha_negocio": "CHECKOUT", "faixas": ["PIX"], "valor": "0,95",
                                                "vigencia_inicio": "2026-10-01", "aprovado_por": "Comercial", "usuario": "Helena"})
    assert st == 200, r


def test_modulo_de_ia_ausente_nao_derruba_a_tela(ctx):
    ctx.mp.setattr(servidor, "ia_contrato", None)
    e = _get(ctx.url + "/api/estado")[1]
    assert e["clientes_novos"]["ia"]["disponivel"] is False
    assert _upload(ctx)[1]["estado"] == "sem_ia"
