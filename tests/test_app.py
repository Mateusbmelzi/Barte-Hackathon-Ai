"""Interface web (app/): sobe o servidor numa thread, envia os 6 arquivos, roda e baixa."""
import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

import pytest

from app import servidor
from src.leitores import achatar, descobrir_arquivos


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
    for p in achatar(arquivos):
        e = _json(url + "/api/enviar", "POST", p.read_bytes(), {"X-Nome-Arquivo": quote(p.name)})
    assert e["pronto"]
    assert {x["chave"]: x["nome"] for x in e["esperados"]} == {k: (", ".join(q.name for q in p) if isinstance(p, list) else p.name)
                                                      for k, p in arquivos.items()}

    e = _json(url + "/api/rodar", "POST", b"")
    assert e["erro"] is None, e["erro"]
    r = e["resultado"]
    assert r["competencia"] == "09/2026"
    assert r["checkout"]["valor"] == "R$ 203.735,34"  # inclui 06_orbe_ajustes_tardios
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


# ------------------------------------------------ investigação de divergências (cartão 4)
import csv as _csv  # noqa: E402
import time  # noqa: E402
from types import SimpleNamespace  # noqa: E402


class ClienteIAFalso:
    """Imita client.messages.create sem rede; o grupo em `falhar` levanta erro (erro só naquele grupo)."""

    def __init__(self, falhar=()):
        self.falhar = set(falhar)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        texto = kw["messages"][0]["content"]
        g = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])["id_grupo"]
        if g in self.falhar:
            raise RuntimeError("falha simulada")
        resp = {"id_grupo": g, "resumo": f"Resumo {g}.", "conferir": ["Conferir o e-mail do Comercial."],
                "falar_com": "Orbe", "dado_faltante": "data do aviso ao parceiro",
                "hipoteses": [{"causa": f"Causa A de {g}", "fatos_citados": ["F1", "F2"], "fatos_contrarios": ["F4"],
                               "confianca": "alta"},
                              {"causa": f"Causa B de {g}", "fatos_citados": ["F3"], "fatos_contrarios": [],
                               "confianca": "baixa"},
                              {"causa": "Sem fato", "fatos_citados": [], "fatos_contrarios": [], "confianca": "alta"}]}
        return SimpleNamespace(model="modelo-falso-1", stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(resp, ensure_ascii=False))])


def _servidor(tmp_path, **kw):
    srv = servidor.criar_servidor(porta=0, pasta_execucoes=tmp_path / "execucoes", **kw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _rodar(url, raiz):
    for p in achatar(descobrir_arquivos(raiz)):
        _json(url + "/api/enviar", "POST", p.read_bytes(), {"X-Nome-Arquivo": quote(p.name)})
    e = _json(url + "/api/rodar", "POST", b"")
    assert e["erro"] is None, e["erro"]
    return e


def _decidir(url, **corpo):
    return _json(url + "/api/ia/decidir", "POST", json.dumps(corpo).encode("utf-8"), {"Content-Type": "application/json"})


def test_investigacao_com_ia_falsa(raiz, tmp_path):
    srv, url = _servidor(tmp_path, cliente_ia=ClienteIAFalso(falhar={"G04"}))
    try:
        e = _rodar(url, raiz)
        inv = e["investigacao"]
        assert inv["ia_disponivel"] and inv["ia_estado"] == "parado" and inv["ia"] is None
        assert [g["id_grupo"] for g in inv["dossie"]["grupos"]] == ["G01", "G02", "G03", "G04"]

        e = _json(url + "/api/ia/gerar", "POST", b"")
        for _ in range(100):
            if e["investigacao"]["ia_estado"] == "pronto":
                break
            time.sleep(0.1)
            e = _json(url + "/api/estado")
        inv = e["investigacao"]
        assert inv["ia_estado"] == "pronto"
        por = {g["id_grupo"]: g for g in inv["ia"]["grupos"]}
        assert [h["causa"] for h in por["G01"]["hipoteses"]] == ["Causa A de G01", "Causa B de G01"]
        assert por["G01"]["hipoteses_descartadas"] == 1 and por["G01"]["modelo_resposta"] == "modelo-falso-1"
        h1 = por["G01"]["hipoteses"][0]
        assert h1["fatos_contrarios"] == ["F4"] and h1["confianca"] == "media"      # rebaixada por ia.validar
        assert any("rebaixada" in a["ajuste"] for a in por["G01"]["ajustes"])
        pagina = _req(url + "/").decode("utf-8")
        assert "Contra: " in pagina and "fatos_contrarios" in pagina and "Ajustes do programa" in pagina
        assert por["G04"]["erro"] and not por["G04"]["hipoteses"]          # erro só no grupo dele
        assert not por["G02"]["erro"]
        pasta = Path(e["pasta"])
        assert json.loads((pasta / "investigacao_ia.json").read_text(encoding="utf-8"))["grupos"][0]["id_grupo"] == "G01"

        # sem nome não decide
        with pytest.raises(urllib.error.HTTPError) as exc:
            _decidir(url, id_grupo="G01", hipotese_n=1, decisao="ACEITA", analista=" ")
        assert exc.value.code == 400
        _decidir(url, id_grupo="G01", hipotese_n=1, decisao="ACEITA", analista="Helena")
        _decidir(url, id_grupo="G02", hipotese_n=2, decisao="RECUSADA", comentario="Contrato não mudou (S06).",
                 analista="Helena")
        e = _decidir(url, id_grupo="G01", hipotese_n=1, decisao="RECUSADA", comentario="mudei de ideia",
                     analista="Helena")                                     # atualiza, não duplica
        assert len(e["investigacao"]["decisoes"]) == 2

        baixado = _req(url + "/api/baixar-decisoes").decode("utf-8")
        assert baixado == (pasta / "decisoes_investigacao.csv").read_text(encoding="utf-8")
        linhas = list(_csv.DictReader(io.StringIO(baixado), delimiter=";"))
        assert list(linhas[0]) == servidor.COLUNAS_DECISOES
        assert [(l["id_grupo"], l["hipotese_n"], l["decisao"], l["comentario"]) for l in linhas] == [
            ("G01", "1", "RECUSADA", "mudei de ideia"), ("G02", "2", "RECUSADA", "Contrato não mudou (S06).")]
        assert linhas[1]["causa"] == "Causa B de G02" and linhas[1]["lojista"] == "Rota Global Intercâmbio Ltda"
        assert linhas[0]["analista"] == "Helena" and linhas[0]["modelo_resposta"] == "modelo-falso-1"
        assert linhas[0]["versao_prompt"] and "T" in linhas[0]["data_hora"]
        # nada disso entra em saida/
        assert sorted(p.name for p in (pasta / "saida").iterdir() if p.is_file()) == sorted(n for n, _ in servidor.SAIDAS)
        assert sorted(p.name for p in (pasta / "saida" / "investigacao").iterdir()) == ["dossie.json", "dossie.md"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_investigacao_sem_chave_botao_desabilitado(raiz, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    srv, url = _servidor(tmp_path, raiz_ia=tmp_path)            # pasta sem .env
    try:
        inv = _rodar(url, raiz)["investigacao"]
        assert len(inv["dossie"]["grupos"]) == 4                # o dossiê aparece mesmo sem IA
        assert inv["ia_disponivel"] is False and ".env" in inv["ia_motivo"] and "README" in inv["ia_motivo"]
        with pytest.raises(urllib.error.HTTPError) as exc:
            _req(url + "/api/ia/gerar", "POST", b"")
        assert exc.value.code == 409
        pagina = _req(url + "/").decode("utf-8")
        assert 'id="gerarIA"' in pagina and "Investigação de divergências" in pagina
    finally:
        srv.shutdown()
        srv.server_close()


# ------------------------------------------------ porta ocupada (bug: dois servidores na mesma porta no Windows)
import socket  # noqa: E402


def test_porta_ocupada_escolhe_outra(tmp_path):
    # O ocupante imita a versão antiga do app (http.server com SO_REUSEADDR). No Windows, com a classe antiga
    # o novo servidor fazia bind na MESMA porta sem erro; agora tem de recusar e ir para a próxima.
    ocupante = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ocupante.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ocupante.bind(("127.0.0.1", 0))
    ocupante.listen(1)
    porta = ocupante.getsockname()[1]
    try:
        srv = servidor.criar_servidor(porta=porta, pasta_execucoes=tmp_path / "execucoes", tentativas=10)
        try:
            assert srv.server_address[1] != porta
            assert porta < srv.server_address[1] < porta + 10
        finally:
            srv.server_close()
    finally:
        ocupante.close()


def test_segundo_servidor_do_app_nao_divide_a_porta(tmp_path):
    srv1, url1 = _servidor(tmp_path / "a")
    porta1 = srv1.server_address[1]
    try:
        assert servidor.tela_existente(porta1)                 # detecta a tela já aberta
        srv2 = servidor.criar_servidor(porta=porta1, pasta_execucoes=tmp_path / "b", tentativas=10)
        try:
            porta2 = srv2.server_address[1]
            assert porta2 != porta1
            url, linhas = servidor.mensagens_inicio(porta2, porta1, havia_tela=True)
            texto = "\n".join(linhas)
            assert f"Já existe uma tela aberta em http://127.0.0.1:{porta1}".lower() in texto.lower()
            assert f"abrindo esta em :{porta2}" in texto and url.endswith(f":{porta2}/")
        finally:
            srv2.server_close()
    finally:
        srv1.shutdown()
        srv1.server_close()
    assert not servidor.tela_existente(porta1, timeout=0.5)    # porta livre: nenhuma tela


def test_varios_arquivos_orbe(url, raiz):
    """A Orbe pode mandar arquivos de ajuste: todos entram, o botão habilita com >=1 Orbe + os outros 5."""
    arq = descobrir_arquivos(raiz)
    for k, v in arq.items():
        if k != "orbe":
            e = _json(url + "/api/enviar", "POST", v.read_bytes(), {"X-Nome-Arquivo": quote(v.name)})
    assert not e["pronto"]                                   # falta a Orbe
    corpo = lambda n: b"id_transacao;x\r\n" + n
    e = _json(url + "/api/enviar", "POST", corpo(b"1;a"), {"X-Nome-Arquivo": quote("orbe_b_ajustes.csv")})
    assert e["pronto"]                                       # 1 Orbe basta
    e = _json(url + "/api/enviar", "POST", corpo(b"2;b"), {"X-Nome-Arquivo": quote("orbe_a.csv")})
    orbe = next(x for x in e["esperados"] if x["chave"] == "orbe")
    assert orbe["nomes"] == ["orbe_a.csv", "orbe_b_ajustes.csv"] and e["pronto"]
    e = _json(url + "/api/enviar", "POST", corpo(b"3;c"), {"X-Nome-Arquivo": quote("orbe_a.csv")})  # mesmo nome substitui
    assert next(x for x in e["esperados"] if x["chave"] == "orbe")["nomes"] == ["orbe_a.csv", "orbe_b_ajustes.csv"]
