"""Aba Contatos (app/): CRUD pela API sobre cadastro/contatos.csv (cópia em tmp_path)."""
import csv
import json
import shutil
import threading
import urllib.error
import urllib.request

import pytest

from app import servidor


@pytest.fixture()
def ctx(tmp_path, raiz):
    pasta = tmp_path / "cadastro"
    shutil.copytree(raiz / "cadastro", pasta)
    srv = servidor.criar_servidor(porta=0, pasta_meses=tmp_path / "meses", pasta_cadastro=pasta)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", pasta
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


NOVO = {"papel": "COMERCIAL", "nome": "Carla Nova", "email": "carla@exemplo.com.br", "observacao": "teste"}


def test_lista_traz_papeis_e_contatos(ctx):
    url, pasta = ctx
    d = _get(url + "/api/contatos")
    assert len(d["contatos"]) >= 8 and {"LOJISTA", "ORBE", "PONTE", "COMERCIAL"} <= {p["codigo"] for p in d["papeis"]}
    assert all(set(c) == {"id_contato", "papel", "cnpj", "nome", "email", "observacao"} for c in d["contatos"])
    assert [p["rotulo"] for p in d["papeis"] if p["codigo"] == "PONTE"] == ["Ponte Câmbio"]


def test_adicionar_editar_e_remover(ctx):
    url, pasta = ctx
    n0 = len(_get(url + "/api/contatos")["contatos"])
    st, r = _post(url + "/api/contatos", NOVO)
    assert st == 200 and r["contato"]["id_contato"]
    id_ = r["contato"]["id_contato"]
    assert len(_get(url + "/api/contatos")["contatos"]) == n0 + 1
    st, r = _post(url + "/api/contatos", {**NOVO, "id_contato": id_, "nome": "Carla Editada", "email": "carla2@exemplo.com.br"})
    assert st == 200
    c = next(c for c in _get(url + "/api/contatos")["contatos"] if c["id_contato"] == id_)
    assert (c["nome"], c["email"]) == ("Carla Editada", "carla2@exemplo.com.br")
    with open(pasta / "contatos.csv", encoding="utf-8", newline="") as f:
        assert id_ in [l["id_contato"] for l in csv.DictReader(f, delimiter=";")]
    st, _ = _post(url + "/api/contatos/remover", {"id_contato": id_, "usuario": "Ana"})
    assert st == 200 and len(_get(url + "/api/contatos")["contatos"]) == n0
    assert (pasta / "contatos_removidos.csv").exists()                       # remover não apaga: guarda o histórico
    assert _post(url + "/api/contatos/remover", {"id_contato": id_})[0] == 400


def test_validacoes_legiveis(ctx):
    url, _ = ctx
    n0 = len(_get(url + "/api/contatos")["contatos"])
    casos = [({"email": "sem-arroba"}, "e-mail"), ({"email": ""}, "e-mail"), ({"nome": ""}, "nome"), ({"papel": "XPTO"}, "papel"),
             ({"papel": "LOJISTA", "cnpj": "123"}, "cnpj"), ({"cnpj": "22224579000109"}, "cnpj")]
    for ajuste, trecho in casos:
        st, r = _post(url + "/api/contatos", {**NOVO, **ajuste})
        assert st == 400 and trecho in r["erro"].lower(), (ajuste, r)
    assert len(_get(url + "/api/contatos")["contatos"]) == n0


def test_lojista_e_gravado_com_cnpj_so_digitos(ctx):
    url, _ = ctx
    st, r = _post(url + "/api/contatos", {"papel": "LOJISTA", "cnpj": "22.224.579/0001-09", "nome": "Financeiro Bridge 2",
                                          "email": "fin2@exemplo.com.br", "observacao": ""})
    assert st == 200 and r["contato"]["cnpj"] == "22224579000109"
