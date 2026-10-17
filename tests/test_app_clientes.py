"""Aba Clientes (app/): lista, ficha, nova condição e encerramento pela API. Usa uma CÓPIA do cadastro em tmp_path
e confere que a planilha de taxas do cliente não é tocada."""
import csv
import hashlib
import json
import shutil
import threading
import urllib.error
import urllib.request
from datetime import date

import pytest

from app import servidor
from src import cadastro

CASA = "00520815000100"     # Casa do Estudante: isenção de checkout (C001)
ATLAS = "39566044000119"    # Atlas Idiomas: bloqueio de faturamento (C005)
BRIDGE = "22224579000109"   # duas linhas na planilha; a vigente em 17/10 é a de 15/09
MUNDO = "17217888000111"    # Mundo Aberto: spread 1,20% na planilha, nota de pendência


@pytest.fixture()
def ctx(tmp_path, raiz):
    pasta = tmp_path / "cadastro"
    shutil.copytree(raiz / "cadastro", pasta)
    srv = servidor.criar_servidor(porta=0, pasta_execucoes=tmp_path / "execucoes", pasta_cadastro=pasta,
                                  raiz_planilha=raiz, hoje=date(2026, 10, 17))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", pasta, raiz
    srv.shutdown()
    srv.server_close()


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def _post(url, corpo):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _taxas(ficha):
    return {t["faixa"]: t for t in ficha["taxas"]}


def _novo(**kw):
    base = {"chave": BRIDGE, "tipo": "TAXA_ESPECIAL", "linha_negocio": "CHECKOUT", "faixas": ["PIX"], "valor": "0,75",
            "vigencia_inicio": "2026-10-01", "vigencia_fim": "", "aprovado_por": "Comercial", "fonte": "e-mail do Comercial",
            "observacao": "teste", "usuario": "Ana"}
    base.update(kw)
    return base


def test_pagina_tem_abas(ctx):
    url, _, _ = ctx
    with urllib.request.urlopen(url + "/") as r:
        html = r.read().decode()
    assert 'id="tabFech"' in html and 'id="tabCli"' in html and "Clientes" in html


def test_lista_de_clientes_com_selos(ctx):
    url, _, _ = ctx
    d = _get(url + "/api/clientes")
    por = {c["chave"]: c for c in d["clientes"]}
    assert len(por) >= 25
    assert [s["codigo"] for s in por[CASA]["selos"]] == ["isencao"]
    assert {s["codigo"] for s in por[ATLAS]["selos"]} == {"bloqueado", "sem_contrato"}   # só no cadastro, não está na planilha vigente
    assert por[CASA]["cnpj"] == "00.520.815/0001-00" and por[CASA]["ecs"] == ["1018325654"]
    assert any(s["codigo"] == "pendencia" for s in por[MUNDO]["selos"])
    assert [c["nome"].lower() for c in d["clientes"]] == sorted(c["nome"].lower() for c in d["clientes"])


def test_ficha_da_casa_mostra_isencao_e_taxas_zero(ctx):
    url, _, _ = ctx
    f = _get(url + "/api/clientes/" + CASA)
    assert f["identificacao"]["cnpj"] == "00.520.815/0001-00"
    assert f["identificacao"]["ecs"] == ["1018325654"]
    assert f["identificacao"]["razao_social_planilha"].startswith("Casa do Estudante")
    t = _taxas(f)
    for faixa in ("DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX", "ANTECIPACAO"):
        assert t[faixa]["valor"] == "0,00%", faixa
        assert t[faixa]["origem"].startswith("cadastro C001")
    assert t["SPREAD_REMESSA"]["valor"] == "1,50%" and t["SPREAD_REMESSA"]["origem"].startswith("planilha linha 13")
    c1 = next(c for c in f["condicoes"] if c["id"] == "C001")
    assert c1["status"] == "ativa" and c1["aprovado_por"] == "Comercial" and c1["fim"] == "31/12/2026" and c1["fonte"] == "S07/S47"
    assert any("isenção" in x for x in f["faturamento"]) and any("nota única" in x for x in f["faturamento"])
    assert {"R52", "Isenção C001"} <= {r["id"] for r in f["regras"]}
    assert f["mes"] is None            # nenhum fechamento rodado na sessão


def test_ficha_da_atlas_mostra_bloqueio(ctx):
    url, _, _ = ctx
    f = _get(url + "/api/clientes/" + ATLAS)
    assert {s["codigo"] for s in f["selos"]} == {"bloqueado", "sem_contrato"}
    assert f["identificacao"]["razao_social_planilha"] is None
    assert all(t["valor"] == "—" for t in f["taxas"])
    assert "Bloqueado" in f["faturamento"][0] and "R15" in f["faturamento"][0]
    assert [r["id"] for r in f["regras"]] == ["R15", "R54", "R59"]
    assert any(c["tipo"] == "BLOQUEIO_FATURAMENTO" and c["status"] == "ativa" for c in f["condicoes"])


def test_ficha_inexistente_404(ctx):
    url, _, _ = ctx
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(url + "/api/clientes/11111111111111")
    assert e.value.code == 404


def test_criar_taxa_especial_grava_linha_e_historico(ctx):
    url, pasta, _ = ctx
    antes = _taxas(_get(url + "/api/clientes/" + BRIDGE))["PIX"]["valor"]
    cod, r = _post(url + "/api/condicoes", _novo())
    assert cod == 200, r
    novo_id = r["ids"][0]
    assert "Rode o fechamento de novo para aplicar." in r["aviso"] and novo_id in r["aviso"]
    linhas = cadastro.ler(pasta)
    gravada = next(c for c in linhas if c["id_condicao"] == novo_id)
    assert (gravada["tipo"], gravada["campo"], gravada["valor"], gravada["cnpj"], gravada["aprovado_por"]) == \
        ("TAXA_ESPECIAL", "PIX", "0.75", BRIDGE, "Comercial")
    hist = cadastro.ler_historico(pasta)
    assert hist[-1]["acao"] == "CRIAR" and hist[-1]["usuario"] == "Ana" and hist[-1]["id_condicao"] == novo_id
    # a ficha devolvida já mostra a taxa nova e de onde ela vem
    t = _taxas(r["ficha"])["PIX"]
    assert t["valor"] == "0,75%" and novo_id in t["origem"] and t["valor"] != antes
    assert any(c["id"] == novo_id and c["status"] == "ativa" for c in r["ficha"]["condicoes"])


def test_criar_isencao_com_todas_as_faixas_de_checkout(ctx):
    url, pasta, _ = ctx
    faixas = ["DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX", "ANTECIPACAO"]
    cod, r = _post(url + "/api/condicoes", _novo(tipo="ISENCAO", faixas=faixas, valor=""))
    assert cod == 200, r
    g = next(c for c in cadastro.ler(pasta) if c["id_condicao"] == r["ids"][0])
    assert g["tipo"] == "ISENCAO" and g["campo"] == "todas" and g["linha_negocio"] == "CHECKOUT"
    assert {s["codigo"] for s in r["ficha"]["selos"]} == {"isencao"}


def test_encerrar_preenche_vigencia_fim(ctx):
    url, pasta, _ = ctx
    cod, r = _post(url + "/api/condicoes/C001/encerrar", {"data_fim": "2026-10-31", "usuario": "Ana"})
    assert cod == 200, r
    assert "Rode o fechamento de novo para aplicar." in r["aviso"]
    c1 = next(c for c in cadastro.ler(pasta) if c["id_condicao"] == "C001")
    assert c1["vigencia_fim"] == "2026-10-31"
    assert cadastro.ler_historico(pasta)[-1]["acao"] == "ENCERRAR"
    # a ficha devolvida continua com a isenção ativa até 31/10 e a condição aparece com o novo fim
    assert next(c for c in r["ficha"]["condicoes"] if c["id"] == "C001")["fim"] == "31/10/2026"
    # adiar o fim não pode (o cadastro só deixa antecipar): erro legível
    cod, r = _post(url + "/api/condicoes/C001/encerrar", {"data_fim": "2026-11-30", "usuario": "Ana"})
    assert cod == 400 and "já termina em" in r["erro"]
    # antecipar o fim para antes de hoje tira a isenção das taxas efetivas
    cod, r = _post(url + "/api/condicoes/C001/encerrar", {"data_fim": "2026-09-30", "usuario": "Ana"})
    assert cod == 200 and _taxas(r["ficha"])["DEBITO"]["valor"] == "1,49%"
    assert "isencao" not in {s["codigo"] for s in r["ficha"]["selos"]}


def test_encerrar_valida_nome_e_data(ctx):
    url, pasta, _ = ctx
    cod, r = _post(url + "/api/condicoes/C001/encerrar", {"data_fim": "2026-10-31", "usuario": ""})
    assert cod == 400 and "Seu nome" in r["erro"]
    cod, r = _post(url + "/api/condicoes/C001/encerrar", {"data_fim": "ontem", "usuario": "Ana"})
    assert cod == 400 and "data válida" in r["erro"]
    cod, r = _post(url + "/api/condicoes/C999/encerrar", {"data_fim": "2026-10-31", "usuario": "Ana"})
    assert cod == 400 and "não encontrada" in r["erro"]
    assert next(c for c in cadastro.ler(pasta) if c["id_condicao"] == "C001")["vigencia_fim"] == "2026-12-31"


def test_taxa_sem_aprovado_por_da_erro_legivel_e_nao_grava(ctx):
    url, pasta, _ = ctx
    antes = (pasta / "condicoes_comerciais.csv").read_bytes()
    cod, r = _post(url + "/api/condicoes", _novo(aprovado_por=""))
    assert cod == 400
    assert "quem aprovou" in r["erro"] and "Comercial" in r["erro"] and "Traceback" not in r["erro"]
    cod, r = _post(url + "/api/condicoes", _novo(tipo="ISENCAO", aprovado_por="", valor=""))
    assert cod == 400 and "quem aprovou" in r["erro"]
    assert (pasta / "condicoes_comerciais.csv").read_bytes() == antes


@pytest.mark.parametrize("ajuste,trecho", [
    ({"usuario": ""}, "Seu nome"),
    ({"valor": "abc"}, "valor da taxa"),
    ({"valor": "150"}, "entre 0 e 100"),
    ({"faixas": []}, "pelo menos uma faixa"),
    ({"vigencia_inicio": ""}, "data válida"),
    ({"vigencia_fim": "2026-09-01"}, "antes do início"),
    ({"tipo": "XPTO"}, "tipo"),
    ({"faixas": ["SPREAD_REMESSA"]}, "linha de negócio"),
    ({"tipo": "BLOQUEIO_FATURAMENTO", "observacao": ""}, "motivo"),
    ({"chave": "99999999999999"}, "não encontrado"),
])
def test_validacoes_da_nova_condicao(ctx, ajuste, trecho):
    url, pasta, _ = ctx
    antes = (pasta / "condicoes_comerciais.csv").read_bytes()
    cod, r = _post(url + "/api/condicoes", _novo(**ajuste))
    assert cod == 400 and trecho in r["erro"], r
    assert (pasta / "condicoes_comerciais.csv").read_bytes() == antes


def test_recusa_do_cadastro_chega_legivel(ctx):
    """Duas taxas especiais na mesma faixa e período: o cadastro recusa e a tela mostra o porquê."""
    url, _, _ = ctx
    assert _post(url + "/api/condicoes", _novo())[0] == 200
    cod, r = _post(url + "/api/condicoes", _novo(valor="0,5"))
    assert cod == 400 and "Encerre" in r["erro"]


def test_planilha_do_cliente_nao_e_alterada(ctx):
    url, _, raiz = ctx
    planilha = next(raiz.glob("*taxas*.xlsx"))
    antes = hashlib.sha256(planilha.read_bytes()).hexdigest()
    _post(url + "/api/condicoes", _novo())
    _post(url + "/api/condicoes/C001/encerrar", {"data_fim": "2026-10-31", "usuario": "Ana"})
    assert hashlib.sha256(planilha.read_bytes()).hexdigest() == antes


def test_historico_e_cadastro_bem_formados_apos_gravar(ctx):
    url, pasta, _ = ctx
    _post(url + "/api/condicoes", _novo())
    with open(pasta / "condicoes_comerciais.csv", encoding="utf-8", newline="") as f:
        assert next(csv.reader(f, delimiter=";")) == cadastro.COLUNAS


def test_ficha_com_resumo_do_mes_depois_de_rodar(ctx, raiz):
    """Roda o fechamento pela API (arquivos reais) e confere o resumo do mês na ficha da Casa e da Atlas."""
    from urllib.parse import quote
    from src.leitores import achatar, descobrir_arquivos
    url, _, _ = ctx
    for p in achatar(descobrir_arquivos(raiz)):
        req = urllib.request.Request(url + "/api/enviar", data=p.read_bytes(), method="POST", headers={"X-Nome-Arquivo": quote(p.name)})
        urllib.request.urlopen(req, timeout=120).read()
    req = urllib.request.Request(url + "/api/rodar", data=b"", method="POST")
    assert json.loads(urllib.request.urlopen(req, timeout=300).read())["erro"] is None
    casa = _get(url + "/api/clientes/" + CASA)
    assert casa["mes"]["competencia"] == "09/2026" and casa["mes"]["devolver_lojista"] == "R$ 15.396,77"
    assert casa["mes"]["divergencia_linhas"] > 0 and casa["identificacao"]["nomes_orbe"]
    assert any(p["tipo"].startswith("ISENCAO") or "CASA" in p["motivo"].upper() or "Casa" in p["motivo"] for p in casa["mes"]["pendencias"])
    atlas = _get(url + "/api/clientes/" + ATLAS)
    assert any(p["tipo"] == "LOJISTA_SEM_CONTRATO" for p in atlas["mes"]["pendencias"])
    assert atlas["mes"]["comissao_checkout"] is None


def test_varias_faixas_e_atomico(ctx):
    """Uma faixa inválida entre várias: erro legível e NADA gravado (nem a faixa válida)."""
    url, pasta, _ = ctx
    antes = {n: (pasta / n).read_bytes() for n in ("condicoes_comerciais.csv", "historico_alteracoes.csv")}
    # PIX é gravável; uma 2ª taxa especial igual em PIX no mesmo pedido não passa na sobreposição
    faixas = ["PIX", "DEBITO"]
    assert _post(url + "/api/condicoes", _novo(faixas=["DEBITO"], valor="1"))[0] == 200
    antes = {n: (pasta / n).read_bytes() for n in antes}
    cod, r = _post(url + "/api/condicoes", _novo(faixas=faixas, valor="2"))
    assert cod == 400 and "Encerre" in r["erro"]
    assert {n: (pasta / n).read_bytes() for n in antes} == antes
    assert [c["campo"] for c in cadastro.ler(pasta) if c["id_condicao"] > "C006"] == ["DEBITO"]


def test_texto_da_isencao_vem_da_condicao(ctx):
    url, _, _ = ctx
    r = _post(url + "/api/condicoes", _novo(tipo="ISENCAO", faixas=["PIX"], valor="", aprovado_por="Helena (Financeiro)",
                                            fonte="e-mail X"))[1]
    textos = [x["texto"] for x in r["ficha"]["regras"] if x["id"].startswith("Isenção")]
    assert any("Pix" in t and "Helena (Financeiro)" in t and "e-mail X" in t and "Bridge" in t for t in textos)
    casa = _get(url + "/api/clientes/" + CASA)
    assert not any("Casa" in x["texto"] and x["id"] == "R72" for x in casa["regras"])
    assert any("Casa do Estudante" in x["texto"] and "31/12/2026" in x["texto"] for x in casa["regras"])


def test_data_de_referencia_das_taxas(ctx):
    url, _, _ = ctx
    f = _get(url + "/api/clientes/" + CASA + "?data=2026-08-15")     # antes da isenção
    assert f["data_referencia"] == "2026-08-15" and f["data_hoje"] == "2026-10-17"
    assert _taxas(f)["DEBITO"]["valor"] == "1,49%" and _taxas(f)["DEBITO"]["origem"].startswith("planilha")
    assert f["selos"] == [] and f["data_competencia"] is None
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(url + "/api/clientes/" + CASA + "?data=xx")
    assert e.value.code == 400
