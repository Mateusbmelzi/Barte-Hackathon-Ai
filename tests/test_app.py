"""Interface web (app/): sobe o servidor numa thread, envia os 6 arquivos, roda e baixa."""
import io
import json
import threading
import urllib.request
import zipfile
from urllib.parse import quote

import pytest

from app import servidor
from src.leitores import descobrir_arquivos


@pytest.fixture()
def url(tmp_path):
    srv = servidor.criar_servidor(porta=0, pasta_execucoes=tmp_path / "execucoes")
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _req(url, metodo="GET", corpo=None, cab=None):
    r = urllib.request.Request(url, data=corpo, method=metodo, headers=cab or {})
    with urllib.request.urlopen(r, timeout=120) as resp:
        return resp.read()


def _json(*a, **k):
    return json.loads(_req(*a, **k))


def test_reconhecer_usa_padroes_de_src():
    assert servidor.reconhecer("01_ORBE_relatorio.csv") == "orbe"
    assert servidor.reconhecer("qualquer.ofx") == "meridiano"
    assert servidor.reconhecer("foto.png") is None


def test_fluxo_completo(url, raiz, tmp_path):
    e = _json(url + "/api/estado")
    assert not e["pronto"] and all("nome" not in x for x in e["esperados"])
    assert b"Fechamento mensal" in _req(url + "/")

    # arquivo estranho é recusado
    e = _json(url + "/api/enviar", "POST", b"x", {"X-Nome-Arquivo": quote("foto.png")})
    assert e["envio"]["reconhecido"] is None

    arquivos = descobrir_arquivos(raiz)
    for p in arquivos.values():
        e = _json(url + "/api/enviar", "POST", p.read_bytes(), {"X-Nome-Arquivo": quote(p.name)})
    assert e["pronto"]
    assert {x["chave"]: x["nome"] for x in e["esperados"]} == {k: p.name for k, p in arquivos.items()}

    e = _json(url + "/api/rodar", "POST", b"")
    assert e["erro"] is None, e["erro"]
    r = e["resultado"]
    assert r["competencia"] == "09/2026"
    assert r["checkout"]["valor"] == "R$ 207.039,73"
    assert r["remessa"]["valor"] == "R$ 39.543,45"
    assert r["pendencias"]["quantidade"] == 18
    assert len(e["saidas"]) == 6 and e["previa_pendencias"]["total"] == 18

    # grava em execucoes/<ts>/entrada e /saida, dentro da pasta pedida
    assert e["pasta"].startswith(str(tmp_path / "execucoes"))

    baixado = _req(url + "/api/baixar/comissoes_por_lojista.csv")
    assert baixado == (raiz / "saida" / "comissoes_por_lojista.csv").read_bytes()

    z = zipfile.ZipFile(io.BytesIO(_req(url + "/api/baixar-tudo")))
    assert sorted(z.namelist()) == sorted(n for n, _ in servidor.SAIDAS)

    e = _json(url + "/api/limpar", "POST", b"")
    assert not e["pronto"] and e["resultado"] is None


def test_erro_legivel(url):
    """Arquivo reconhecido pelo nome mas com conteúdo inválido: erro curto, sem stack trace."""
    for nome in ("a_orbe.csv", "b_taxas.xlsx", "c.eml", "d_plano_de_contas.csv", "e_aurora.csv", "f.ofx"):
        e = _json(url + "/api/enviar", "POST", b"lixo", {"X-Nome-Arquivo": quote(nome)})
    e = _json(url + "/api/rodar", "POST", b"")
    assert e["resultado"] is None and e["erro"]["titulo"]
    assert "Traceback" not in e["erro"]["detalhe"]


def test_baixar_nome_invalido(url):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _req(url + "/api/baixar/..%2F..%2Fsrc%2Fconfig.py")
    assert exc.value.code == 404
