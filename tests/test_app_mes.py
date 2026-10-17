"""Pasta do mês persistente (meses/<AAAA-MM>/): envios que nunca sobrescrevem, versões, remover e execuções."""
import csv
import json
import threading
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote

import pytest

from app import servidor
from src.leitores import achatar, descobrir_arquivos

HOJE = date(2026, 10, 5)      # mês anterior = 2026-09


def _subir(tmp_path, hoje=HOJE):
    srv = servidor.criar_servidor(porta=0, pasta_meses=tmp_path / "meses", hoje=hoje)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _parar(srv):
    srv.shutdown()
    srv.server_close()


def _req(url, metodo="GET", corpo=None, cab=None):
    r = urllib.request.Request(url, data=corpo, method=metodo, headers=cab or {})
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())


def _enviar(url, nome, conteudo, usuario="Helena"):
    return _req(url + "/api/enviar", "POST", conteudo,
                {"X-Nome-Arquivo": quote(nome), "X-Usuario": quote(usuario)})


def _fonte(e, chave):
    return next(x for x in e["esperados"] if x["chave"] == chave)


def _envios(tmp_path, mes="2026-09"):
    with open(tmp_path / "meses" / mes / "entrada" / "_envios.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def test_mes_padrao_e_persistente_entre_instancias(tmp_path):
    srv, url = _subir(tmp_path)
    try:
        e = _req(url + "/api/estado")
        assert e["mes"] == "2026-09" and e["meses"] == ["2026-09"] and not e["pronto"]
        _enviar(url, "05a_extrato_aurora.csv", b"data;valor\r\n1;2")
        _enviar(url, "extrato.ofx", b"OFX")
        assert (tmp_path / "meses" / "2026-09" / "entrada" / "05a_extrato_aurora.csv").exists()
    finally:
        _parar(srv)

    # "dia seguinte": outro processo, mesma pasta; os arquivos já enviados aparecem sem reenviar
    srv, url = _subir(tmp_path, hoje=date(2026, 10, 6))
    try:
        e = _req(url + "/api/estado")
        assert e["mes"] == "2026-09" and e["pronto"]
        assert _fonte(e, "aurora")["nome"] == "05a_extrato_aurora.csv"
        assert _fonte(e, "meridiano")["versoes"][0]["data_hora_br"]
        # outro mês: lista vazia, e o mês antigo continua na lista de meses
        e = _req(url + "/api/mes", "POST", json.dumps({"mes": "2026-10"}).encode())
        assert e["mes"] == "2026-10" and not e["pronto"] and e["meses"] == ["2026-09", "2026-10"]
        with pytest.raises(urllib.error.HTTPError) as exc:
            _req(url + "/api/mes", "POST", json.dumps({"mes": "../x"}).encode())
        assert exc.value.code == 400
    finally:
        _parar(srv)


def test_reenvio_mesmo_nome_vira_v2_e_registra(tmp_path):
    srv, url = _subir(tmp_path)
    try:
        e = _enviar(url, "05a_extrato_aurora.csv", b"data;valor\r\n1;2", "Helena")
        assert e["envio"]["arquivo_salvo"] == "05a_extrato_aurora.csv"
        e = _enviar(url, "05a_extrato_aurora.csv", b"data;valor\r\n1;2\r\n3;4", "Carla")
        assert e["envio"]["arquivo_salvo"] == "05a_extrato_aurora_v2.csv" and "nova versão" in e["envio"]["aviso"]
        e = _enviar(url, "05a_extrato_aurora.csv", b"data;valor\r\n1;2\r\n3;4\r\n5;6")
        assert e["envio"]["arquivo_salvo"] == "05a_extrato_aurora_v3.csv"

        entrada = tmp_path / "meses" / "2026-09" / "entrada"
        assert (entrada / "05a_extrato_aurora.csv").read_bytes() == b"data;valor\r\n1;2"   # original intacto
        vs = _fonte(e, "aurora")["versoes"]
        assert [v["arquivo"] for v in vs] == ["05a_extrato_aurora.csv", "05a_extrato_aurora_v2.csv",
                                              "05a_extrato_aurora_v3.csv"]
        assert [v["mais_recente"] for v in vs] == [False, False, True]
        assert vs[1]["usuario"] == "Carla" and vs[1]["tamanho"] > vs[0]["tamanho"]

        linhas = _envios(tmp_path)
        assert list(linhas[0])[:5] == ["data_hora", "arquivo_salvo", "nome_original", "tipo_reconhecido", "usuario"]
        assert [(l["arquivo_salvo"], l["nome_original"], l["tipo_reconhecido"], l["usuario"]) for l in linhas[:2]] == [
            ("05a_extrato_aurora.csv", "05a_extrato_aurora.csv", "aurora", "Helena"),
            ("05a_extrato_aurora_v2.csv", "05a_extrato_aurora.csv", "aurora", "Carla")]
        assert linhas[0]["data_hora"]
    finally:
        _parar(srv)


def test_reenvio_identico_nao_duplica(tmp_path):
    srv, url = _subir(tmp_path)
    try:
        _enviar(url, "aurora_set.csv", b"data;valor\r\n1;2")
        e = _enviar(url, "aurora_set.csv", b"data;valor\r\n1;2")                  # mesmo nome e conteúdo
        assert e["envio"]["duplicado"] and "idêntico ao já enviado em" in e["envio"]["aviso"]
        e = _enviar(url, "outro_nome_aurora.csv", b"data;valor\r\n1;2")           # outro nome, mesmo conteúdo
        assert e["envio"]["duplicado"] and e["envio"]["arquivo_salvo"] == "aurora_set.csv"
        assert [p.name for p in (tmp_path / "meses" / "2026-09" / "entrada").iterdir()
                if not p.name.startswith("_")] == ["aurora_set.csv"]
        assert len(_envios(tmp_path)) == 1
        assert len(_fonte(e, "aurora")["versoes"]) == 1
    finally:
        _parar(srv)


def test_remover_move_para_removidos_e_registra(tmp_path):
    srv, url = _subir(tmp_path)
    try:
        _enviar(url, "aurora_set.csv", b"v1")
        _enviar(url, "aurora_set.csv", b"v2")
        e = _req(url + "/api/remover", "POST", json.dumps({"arquivo": "aurora_set_v2.csv", "usuario": "Helena"}).encode())
        entrada = tmp_path / "meses" / "2026-09" / "entrada"
        assert not (entrada / "aurora_set_v2.csv").exists()
        assert (entrada / "_removidos" / "aurora_set_v2.csv").read_bytes() == b"v2"       # nunca apaga
        vs = _fonte(e, "aurora")["versoes"]
        assert [v["arquivo"] for v in vs] == ["aurora_set.csv"] and vs[0]["mais_recente"]
        ultima = _envios(tmp_path)[-1]
        assert (ultima["arquivo_salvo"], ultima["acao"], ultima["usuario"]) == ("aurora_set_v2.csv", "removido", "Helena")

        for ruim in ("../../x", "_envios.csv", "nao_existe.csv"):                          # só arquivos ativos do mês
            with pytest.raises(urllib.error.HTTPError) as exc:
                _req(url + "/api/remover", "POST", json.dumps({"arquivo": ruim}).encode())
            assert exc.value.code == 400
        # reenviar o conteúdo removido é permitido (não conta como idêntico a algo ativo)
        e = _enviar(url, "aurora_set.csv", b"v2")
        assert e["envio"]["arquivo_salvo"] == "aurora_set_v2.csv" and not e["envio"].get("duplicado")
    finally:
        _parar(srv)


def test_mes_da_aba_desatualizada_nao_grava_no_mes_errado(tmp_path):
    srv, url = _subir(tmp_path)
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            _req(url + "/api/enviar", "POST", b"x", {"X-Nome-Arquivo": "aurora.csv", "X-Mes": "2026-08"})
        assert exc.value.code == 409
        assert not (tmp_path / "meses").exists()
    finally:
        _parar(srv)


def test_rodar_usa_pasta_do_mes_e_guarda_historico(tmp_path, raiz):
    srv, url = _subir(tmp_path)
    try:
        for p in achatar(descobrir_arquivos(raiz)):
            _enviar(url, p.name, p.read_bytes())
        e1 = _req(url + "/api/rodar", "POST", b"")
        assert e1["erro"] is None, e1["erro"]
        assert e1["resultado"]["checkout"]["valor"] == "R$ 203.735,34"
        pasta1 = Path(e1["pasta"])
        assert pasta1.parent == tmp_path / "meses" / "2026-09" / "execucoes" and (pasta1 / "saida" / "pendencias.csv").exists()
        assert not (pasta1 / "entrada").exists()                       # a entrada é a pasta do mês, não uma cópia

        e2 = _req(url + "/api/rodar", "POST", b"")                     # segunda execução: histórico preservado
        pasta2 = Path(e2["pasta"])
        assert pasta2 != pasta1 and pasta1.exists() and (pasta2 / "saida" / "pendencias.csv").exists()
        assert len(e2["execucoes"]) == 2 and e2["execucoes"][0] == pasta2.name   # a mais recente primeiro
        assert "versoes" in e2["resultado"]                              # None enquanto o fechamento não expõe r["versoes"]
    finally:
        _parar(srv)


def test_versao_nova_do_aurora_consolida_e_aparece_no_resultado(tmp_path, raiz):
    srv, url = _subir(tmp_path)
    try:
        for p in achatar(descobrir_arquivos(raiz)):
            _enviar(url, p.name, p.read_bytes())
        base = _req(url + "/api/rodar", "POST", b"")
        assert base["erro"] is None, base["erro"]
        aur = descobrir_arquivos(raiz)["aurora"]
        linhas = aur.read_text(encoding="utf-8").splitlines()
        i = next(k for k, l in enumerate(linhas) if l.startswith(";SALDO FINAL"))
        nova = "30/09/2026;TAR PACOTE SERVICOS PJ;;-1,00;-1.920.089,60"
        v2 = "\r\n".join(linhas[:i] + [nova] + linhas[i:]) + "\r\n"
        e = _enviar(url, aur.name, v2.encode("utf-8"))
        assert e["envio"]["arquivo_salvo"] == aur.name.replace(".csv", "_v2.csv")
        e = _req(url + "/api/rodar", "POST", b"")
        assert e["erro"] is None, e["erro"]
        r = e["resultado"]
        assert r["lancamentos"] == base["resultado"]["lancamentos"] + 1
        assert r["checkout"]["valor"] == "R$ 203.735,34"
        v = r["versoes"]["aurora"]
        assert [Path(a).name for a in v["arquivos"]] == [aur.name, aur.name.replace(".csv", "_v2.csv")]
        assert "Aurora" in v["texto"] and v["novas"]
    finally:
        _parar(srv)
