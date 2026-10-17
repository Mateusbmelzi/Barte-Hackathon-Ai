"""Fila de trabalho na tela (PLANO_03): itens, e-mail (mailto), envio, baixa, declínio, reabertura, planilhas da
execução e assistente de cadastro. IA sempre com stubs; tudo em tmp_path (o cadastro é uma cópia)."""
import csv
import json
import shutil
import threading
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, quote, unquote, urlsplit

import pytest

from app import servidor
from src import cadastro
from src.leitores import achatar, descobrir_arquivos


# ------------------------------------------------ stubs de IA (só aqui, nunca em src/)
class ClienteIAFalso:
    """Cliente da API para ia.investigar (mesmo formato dos outros testes da tela)."""

    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        texto = kw["messages"][0]["content"]
        g = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])["id_grupo"]
        resp = {"id_grupo": g, "resumo": f"Resumo {g}.", "conferir": [], "falar_com": "Orbe", "dado_faltante": "",
                "hipoteses": [{"causa_categoria": "REAJUSTE_SEM_CONTRATO", "causa": "Reajuste", "explicacao": "A Orbe subiu a taxa.",
                               "evidencias": [{"texto": "Diferença igual", "ref": "F1"}], "fatos_citados": ["F1"],
                               "fatos_contrarios": [], "confianca": "alta"}]}
        return SimpleNamespace(model="falso", stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(resp, ensure_ascii=False))])


def _acoes_stub():
    def disponivel(raiz=None):
        return True, ""

    def sugerir_todos(itens, contexto, *, cliente=None, pasta=None, raiz=None, **_):
        out = []
        for i in itens:
            papel = i["destinos_permitidos"][0]
            out.append({"chave": i["chave"], "acao_resumo": f"Pedir retorno do(a) {papel} sobre {i['tipo']}.",
                        "destinos": [papel], "prazo_sugerido": "5 dias úteis", "valores_citados": [], "erro": None,
                        "emails": [{"papel": papel, "assunto": f"Assunto & teste: {i['tipo']}",
                                    "corpo": "Olá,\nSegue o pedido (conforme aprovação da Helena).\nAbraço"}]})
        return out

    return SimpleNamespace(disponivel=disponivel, sugerir_todos=sugerir_todos)


CONDICAO = {"id_condicao": "", "tipo": "TAXA_ESPECIAL", "cnpj": "22224579000109", "ec_orbe": "", "lojista": "Escola Bridge de Idiomas Ltda",
            "linha_negocio": "CHECKOUT", "campo": "PIX", "valor": "0.75", "vigencia_inicio": "2026-10-01", "vigencia_fim": "",
            "aprovado_por": "Comercial", "data_registro": "", "fonte": "Assistente de cadastro (IA)", "observacao": "teste"}


def _cadastro_stub(chamadas):
    def propor(texto, lojistas, condicoes_vigentes, pasta_cadastro=None, **_):
        chamadas.append(texto)
        return {"condicoes": [dict(CONDICAO)], "resumo": "Pix de Bridge a 0,75% desde 01/10.", "erros": [], "duvidas": "",
                "antes_depois": [{"faixa": "Pix", "antes": "0,99%", "depois": "0,75%", "origem": "cadastro NOVA"}]}
    return SimpleNamespace(propor=propor)


# ------------------------------------------------ HTTP
def _get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read())


def _post(url, corpo=None, bruto=None):
    dados = bruto if bruto is not None else json.dumps(corpo or {}).encode()
    req = urllib.request.Request(url, data=dados, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _csv(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _subir(tmp_path, raiz, monkeypatch, acoes=True, ia_auto=True, hoje=date(2026, 10, 17)):
    pasta = tmp_path / "cadastro"
    shutil.copytree(raiz / "cadastro", pasta)
    monkeypatch.setattr(servidor, "ia_acoes", _acoes_stub() if acoes else None)
    srv = servidor.criar_servidor(porta=0, pasta_meses=tmp_path / "meses", pasta_cadastro=pasta, raiz_planilha=raiz, hoje=hoje,
                                  cliente_ia=ClienteIAFalso() if ia_auto else None, ia_auto=ia_auto)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}", pasta


def _rodar(url, raiz):
    for p in achatar(descobrir_arquivos(raiz)):
        urllib.request.urlopen(urllib.request.Request(url + "/api/enviar", data=p.read_bytes(), method="POST",
                                                      headers={"X-Nome-Arquivo": quote(p.name)}), timeout=120).read()
    e = _post(url + "/api/rodar")[1]
    assert e["erro"] is None, e["erro"]
    return e


def _esperar_ia(url):
    for _ in range(200):
        f = _get(url + "/api/fila")
        if not f["ia"]["analisando"]:
            return f
        time.sleep(0.1)
    raise AssertionError("a IA não terminou")


@pytest.fixture()
def tela(tmp_path, raiz, monkeypatch):
    srv, url, pasta = _subir(tmp_path, raiz, monkeypatch)
    e = _rodar(url, raiz)
    f = _esperar_ia(url)
    yield SimpleNamespace(url=url, e=e, f=f, exec=Path(e["pasta"]), mes=tmp_path / "meses" / e["mes"], cadastro=pasta)
    srv.shutdown()
    srv.server_close()


def _item(tela, **filtro):
    f = _get(tela.url + "/api/fila")
    for i in f["itens"]:
        if all(i[k] == v for k, v in filtro.items()):
            return i
    raise AssertionError(f"item não encontrado: {filtro}")


def _corpo_email(item, **kw):
    base = {"chave": item["chave"], "usuario": "Ana", "para": "alguem@exemplo.com.br", "assunto": "Pedido & conferência",
            "corpo": "Olá,\nPor favor conferir R$ 1.234,56 (ref. ação 100%).\nObrigada"}
    base.update(kw)
    return base


# ------------------------------------------------ itens
def test_pagina_tem_as_quatro_abas(tela):
    html = urllib.request.urlopen(tela.url + "/").read().decode()
    for t in ('id="tabFech"', 'id="tabFila"', 'id="tabCli"', 'id="tabCont"', "Fila de trabalho", "Contatos", "IA analisando…"):
        assert t in html, t


def test_todas_as_pendencias_aparecem_na_fila(tela):
    pend = _csv(tela.exec / "saida" / "pendencias.csv")
    itens = [i for i in tela.f["itens"] if i["tipo_item"] == "PENDENCIA"]
    assert len(itens) == len(pend) == tela.e["resultado"]["pendencias"]["quantidade"] > 5
    assert {i["id_saida"] for i in itens} == {p["id_saida"] for p in pend}      # nenhuma filtrada por tipo
    assert all(i["status"] == "ABERTA" and i["aba"] == "pendencias" for i in itens)
    assert tela.f["contadores"]["pendencias"] == len(pend)
    assert tela.f["contadores"]["divergencias"] == len([i for i in tela.f["itens"] if i["tipo_item"] == "DIVERGENCIA"]) > 0


def test_item_traz_objetivo_sugestao_e_contatos(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    assert i["objetivo"] and i["valor"] and i["quem_decide"] and i["titulo"]
    assert i["sugestao"]["acao_resumo"].startswith("Pedir retorno do(a) COMERCIAL")
    assert [c["papel"] for c in i["contatos"]] == ["COMERCIAL"]
    assert "@" in i["contatos"][0]["email"]                      # vem de cadastro/contatos.csv
    assert tela.f["ia"]["disponivel"] is True and tela.f["ia"]["sugestoes"] == "pronto"
    # a sugestão da IA ficou no log, sem mudar o status
    linhas = _csv(tela.mes / "fila_log.csv")
    assert any(l["acao"] == "SUGESTAO_IA" and l["status_novo"] == "" and l["usuario"] == "IA" for l in linhas)
    assert (tela.f["itens"][0]["status"]) == "ABERTA"


def test_divergencia_tem_grupo_e_ia_investigou_sozinha(tela):
    d = _item(tela, tipo_item="DIVERGENCIA")
    assert d["id_grupo"] and d["chave"].startswith("DIV|")
    inv = _get(tela.url + "/api/estado")["investigacao"]
    assert inv["ia_estado"] == "pronto" and inv["ia"]["grupos"]                  # ia.investigar rodou sem clicar
    assert (tela.exec / "investigacao_ia.json").exists()


def test_sem_ia_a_fila_funciona_so_com_o_playbook(tmp_path, raiz, monkeypatch):
    srv, url, _ = _subir(tmp_path, raiz, monkeypatch, acoes=False, ia_auto=True)
    try:
        _rodar(url, raiz)
        f = _get(url + "/api/fila")
        assert f["ia"]["disponivel"] is False and f["ia"]["analisando"] is False
        assert f["itens"] and all(i["sugestao"] is None and i["objetivo"] for i in f["itens"])
        assert all(i["contatos"] for i in f["itens"])                           # destinos do playbook
    finally:
        srv.shutdown(); srv.server_close()


# ------------------------------------------------ e-mail
def test_preparar_email_gera_mailto_correto_e_loga(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    corpo = _corpo_email(i, para="a@exemplo.com.br; b@exemplo.com.br")
    st, r = _post(tela.url + "/api/fila/email", corpo)
    assert st == 200 and r["mailto"].startswith("mailto:a@exemplo.com.br,b@exemplo.com.br?")
    q = parse_qs(urlsplit(r["mailto"]).query)
    assert q["subject"] == [corpo["assunto"]] and q["body"] == [corpo["corpo"].replace("\n", "\r\n")]   # & e quebra CRLF sobrevivem
    assert "%0D%0A" in r["mailto"] and "%0A" not in r["mailto"].replace("%0D%0A", "")   # nenhuma quebra solta (só CRLF)
    assert "%26" in r["mailto"] and " " not in r["mailto"]
    assert unquote(urlsplit(r["mailto"]).path) == "a@exemplo.com.br,b@exemplo.com.br"
    linhas = [l for l in _csv(tela.mes / "fila_log.csv") if l["acao"] == "EMAIL_PREPARADO" and l["chave"] == i["chave"]]
    assert len(linhas) == 1 and linhas[0]["usuario"] == "Ana" and linhas[0]["status_novo"] == ""
    assert "Pedido & conferência" in linhas[0]["detalhe"]
    assert _item(tela, chave=i["chave"])["status"] == "ABERTA"                        # preparar não muda o status


def test_email_exige_nome_destinatario_valido_e_assunto(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    for ajuste, trecho in (({"usuario": ""}, "nome"), ({"para": ""}, "destinat"), ({"para": "sem-arroba"}, "inválido"),
                           ({"assunto": ""}, "assunto")):
        st, r = _post(tela.url + "/api/fila/email", _corpo_email(i, **ajuste))
        assert st == 400 and trecho in r["erro"].lower(), (ajuste, r)
    assert not [l for l in _csv(tela.mes / "fila_log.csv") if l["acao"] == "EMAIL_PREPARADO"]


def test_marcar_enviado_move_para_acompanhamento_e_atualiza_a_planilha(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    corpo = _corpo_email(i)
    assert _post(tela.url + "/api/fila/email", corpo)[0] == 200
    st, r = _post(tela.url + "/api/fila/enviado", corpo)
    assert st == 200 and r["status"] == "EM_ACOMPANHAMENTO"
    novo = _item(tela, chave=i["chave"])
    assert novo["status"] == "EM_ACOMPANHAMENTO" and novo["aba"] == "acompanhamento"
    assert r["fila"]["contadores"]["acompanhamento"] == 2
    log = [l for l in _csv(tela.mes / "fila_log.csv") if l["acao"] == "EMAIL_ENVIADO" and l["chave"] == i["chave"]]
    assert log[0]["status_novo"] == "EM_ACOMPANHAMENTO" and corpo["corpo"] in log[0]["detalhe"] and corpo["assunto"] in log[0]["detalhe"]
    linha = next(p for p in _csv(tela.exec / "saida" / "pendencias.csv") if p["id_saida"] == i["id_saida"])
    assert (linha["status"], linha["ultima_acao"], linha["responsavel"]) == ("EM_ACOMPANHAMENTO", "EMAIL_ENVIADO", "Ana")
    assert linha["data_ultima_acao"]
    outras = [p for p in _csv(tela.exec / "saida" / "pendencias.csv") if p["id_saida"] != i["id_saida"]]
    assert outras and all(p["status"] == "ABERTA" for p in outras)               # só o item mexido mudou
    assert list(_csv(tela.exec / "saida" / "pendencias.csv")[0])[:6] == ["id_saida", "tipo", "ref_origem", "valor_brl", "motivo", "quem_decide"]


# ------------------------------------------------ baixa, declínio, reabertura
def test_baixa_exige_comentario(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    for comentario in ("", "   "):
        st, r = _post(tela.url + "/api/fila/baixa", {"chave": i["chave"], "usuario": "Ana", "comentario": comentario})
        assert st == 400 and "comentário" in r["erro"].lower()
    assert _item(tela, chave=i["chave"])["status"] == "ABERTA"
    st, _ = _post(tela.url + "/api/fila/baixa", {"chave": i["chave"], "usuario": "", "comentario": "ok"})
    assert st == 400                                                                    # nome obrigatório


def test_baixa_move_para_encerradas_e_a_planilha_guarda_o_comentario(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    st, r = _post(tela.url + "/api/fila/baixa", {"chave": i["chave"], "usuario": "Ana", "comentario": "Devolvido em 20/10"})
    assert st == 200 and r["fila"]["contadores"]["encerradas"] == 2
    assert _item(tela, chave=i["chave"])["aba"] == "encerradas"
    linha = next(p for p in _csv(tela.exec / "saida" / "pendencias.csv") if p["id_saida"] == i["id_saida"])
    assert (linha["status"], linha["comentario"], linha["ultima_acao"]) == ("BAIXADA", "Devolvido em 20/10", "BAIXA")
    st, r = _post(tela.url + "/api/fila/email", _corpo_email(i))                         # encerrado: reabrir antes de agir
    assert st == 400 and "reabra" in r["erro"].lower()


def test_declinar_pendencia_e_recusado_e_divergencia_vira_declinada(tela):
    p = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    st, r = _post(tela.url + "/api/fila/declinar", {"chave": p["chave"], "usuario": "Ana", "comentario": "x"})
    assert st == 400 and "divergência" in r["erro"].lower()
    assert _item(tela, chave=p["chave"])["status"] == "ABERTA"
    d = _item(tela, tipo_item="DIVERGENCIA")
    st, _ = _post(tela.url + "/api/fila/declinar", {"chave": d["chave"], "usuario": "Ana", "comentario": ""})
    assert st == 400
    st, _ = _post(tela.url + "/api/fila/declinar", {"chave": d["chave"], "usuario": "Ana", "comentario": "Valor irrelevante"})
    assert st == 200 and _item(tela, chave=d["chave"])["status"] == "DECLINADA"
    linhas = _csv(tela.exec / "saida" / "divergencias_taxa.csv")
    cnpj, nat, contra = d["cnpj"], d["natureza"], d["contraparte"]
    do_grupo = [l for l in linhas if l["cnpj"] == cnpj and l["natureza"] == nat
                and ("ORBE" if l["linha_negocio"] == "CHECKOUT" else "PONTE") == contra]
    assert do_grupo and all(l["status"] == "DECLINADA" for l in do_grupo)
    assert any(l["status"] == "ABERTA" for l in linhas)


def test_reabrir_volta_para_aberta(tela):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    assert _post(tela.url + "/api/fila/reabrir", {"chave": i["chave"], "usuario": "Ana"})[0] == 400      # já aberta
    _post(tela.url + "/api/fila/baixa", {"chave": i["chave"], "usuario": "Ana", "comentario": "feito"})
    st, r = _post(tela.url + "/api/fila/reabrir", {"chave": i["chave"], "usuario": "Bia", "comentario": "faltou um valor"})
    assert st == 200 and _item(tela, chave=i["chave"])["status"] == "ABERTA"
    linha = next(p for p in _csv(tela.exec / "saida" / "pendencias.csv") if p["id_saida"] == i["id_saida"])
    assert (linha["status"], linha["ultima_acao"], linha["responsavel"]) == ("ABERTA", "REABERTA", "Bia")
    hist = _get(tela.url + "/api/fila/historico?chave=" + quote(i["chave"], safe=""))["linhas"]
    assert [l["acao"] for l in hist if l["acao"] != "SUGESTAO_IA"] == ["BAIXA", "REABERTA"]
    st, r = _post(tela.url + "/api/fila/baixa", {"chave": "PEN|NAO_EXISTE|x", "usuario": "Ana", "comentario": "x"})
    assert st == 400 and "não encontrado" in r["erro"].lower()


def test_status_sobrevive_a_novo_fechamento_do_mes(tela, raiz):
    i = _item(tela, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    _post(tela.url + "/api/fila/baixa", {"chave": i["chave"], "usuario": "Ana", "comentario": "feito"})
    e = _post(tela.url + "/api/rodar")[1]
    _esperar_ia(tela.url)
    nova = Path(e["pasta"])
    assert nova != tela.exec
    linha = next(p for p in _csv(nova / "saida" / "pendencias.csv") if p["tipo"] == i["tipo"] and p["ref_origem"] == i["ref_origem"])
    assert linha["status"] == "BAIXADA" and linha["responsavel"] == "Ana"
    assert _item(tela, chave=i["chave"])["aba"] == "encerradas"


# ------------------------------------------------ assistente de cadastro
@pytest.fixture()
def assistente(tmp_path, raiz, monkeypatch):
    chamadas = []
    monkeypatch.setattr(servidor, "ia_cadastro", _cadastro_stub(chamadas))
    srv, url, pasta = _subir(tmp_path, raiz, monkeypatch, acoes=False, ia_auto=False)
    yield SimpleNamespace(url=url, pasta=pasta, chamadas=chamadas)
    srv.shutdown()
    srv.server_close()


def _bytes(pasta):
    return {n: (pasta / n).read_bytes() for n in ("condicoes_comerciais.csv", "historico_alteracoes.csv")}


def test_assistente_propor_nao_grava(assistente):
    antes = _bytes(assistente.pasta)
    st, p = _post(assistente.url + "/api/cadastro/propor", {"texto": "Bridge: Pix a 0,75% desde 01/10, aprovado pelo Comercial"})
    assert st == 200 and p["condicoes"][0]["campo"] == "PIX" and p["antes_depois"][0]["depois"] == "0,75%" and p["token"]
    assert assistente.chamadas and _bytes(assistente.pasta) == antes
    assert _post(assistente.url + "/api/cadastro/propor", {"texto": "  "})[0] == 400


def test_assistente_confirmar_grava_so_com_nome_e_proposta(assistente):
    _, p = _post(assistente.url + "/api/cadastro/propor", {"texto": "Bridge: Pix a 0,75%"})
    antes = _bytes(assistente.pasta)
    assert _post(assistente.url + "/api/cadastro/confirmar", {"token": p["token"], "usuario": ""})[0] == 400
    assert _post(assistente.url + "/api/cadastro/confirmar", {"token": "inventado", "usuario": "Ana"})[0] == 400
    assert _bytes(assistente.pasta) == antes
    st, r = _post(assistente.url + "/api/cadastro/confirmar", {"token": p["token"], "usuario": "Ana"})
    assert st == 200 and len(r["ids"]) == 1
    novas = [c for c in cadastro.ler(assistente.pasta) if c["id_condicao"] == r["ids"][0]]
    assert novas and novas[0]["campo"] == "PIX" and novas[0]["valor"] == "0.75"
    assert any(h["usuario"] == "Ana" and h["acao"] == "CRIAR" for h in cadastro.ler_historico(assistente.pasta))
    assert _post(assistente.url + "/api/cadastro/confirmar", {"token": p["token"], "usuario": "Ana"})[0] == 400   # token gasto


# ------------------------------------------------ itens vinculados (pendência de divergência <-> grupo DIV)
@pytest.fixture()
def vinculada(tmp_path, raiz, monkeypatch):
    original = servidor.fila_mod.itens

    def com_vinculo(resultado, log=None):
        itens = original(resultado, log)
        div = next(i for i in itens if i["tipo_item"] == "DIVERGENCIA" and i["natureza"] == "ISENCAO_NAO_INFORMADA")
        for i in itens:
            i.setdefault("vinculado_a", None)
            if i["tipo"] == "DEVOLUCAO_LOJISTA_ISENCAO":
                i["vinculado_a"] = div["chave"]
        return itens
    monkeypatch.setattr(servidor.fila_mod, "itens", com_vinculo)
    srv, url, pasta = _subir(tmp_path, raiz, monkeypatch)
    e = _rodar(url, raiz)
    f = _esperar_ia(url)
    yield SimpleNamespace(url=url, e=e, f=f, exec=Path(e["pasta"]), mes=tmp_path / "meses" / e["mes"])
    srv.shutdown()
    srv.server_close()


def test_sugestao_unica_no_div_e_selo_na_pendencia(vinculada):
    t = vinculada
    pen = _item(t, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    div = _item(t, chave=pen["vinculado_a"])
    assert pen["sugestao"] == div["sugestao"] and div["sugestao"]
    assert pen["mesmo_caso"]["chave"] == div["chave"] and pen["mesmo_caso"]["titulo"]
    chaves_sug = [l["chave"] for l in _csv(t.mes / "fila_log.csv") if l["acao"] == "SUGESTAO_IA"]
    assert pen["chave"] not in chaves_sug and div["chave"] in chaves_sug      # a IA gerou uma vez só


def test_acao_registra_nas_duas_chaves_e_declinar_baixa_a_pendencia(vinculada):
    t = vinculada
    pen = _item(t, tipo="DEVOLUCAO_LOJISTA_ISENCAO")
    div = _item(t, chave=pen["vinculado_a"])
    st, _ = _post(t.url + "/api/fila/declinar", {"chave": div["chave"], "usuario": "Ana", "comentario": "Sem relevância"})
    assert st == 200
    assert _item(t, chave=div["chave"])["status"] == "DECLINADA" and _item(t, chave=pen["chave"])["status"] == "BAIXADA"
    log = [l for l in _csv(t.mes / "fila_log.csv") if l["acao"] in ("DECLINADA", "BAIXA")]
    assert {(l["chave"], l["acao"], l["detalhe"]) for l in log} == {(div["chave"], "DECLINADA", "Sem relevância"),
                                                                    (pen["chave"], "BAIXA", "Sem relevância")}
    st, _ = _post(t.url + "/api/fila/reabrir", {"chave": pen["chave"], "usuario": "Ana"})
    assert st == 200 and _item(t, chave=div["chave"])["status"] == "ABERTA" == _item(t, chave=pen["chave"])["status"]
    assert _post(t.url + "/api/fila/enviado", _corpo_email(pen))[0] == 200
    assert _item(t, chave=pen["chave"])["status"] == _item(t, chave=div["chave"])["status"] == "EM_ACOMPANHAMENTO"
    assert _post(t.url + "/api/fila/declinar", {"chave": pen["chave"], "usuario": "Ana", "comentario": "x"})[0] == 400
