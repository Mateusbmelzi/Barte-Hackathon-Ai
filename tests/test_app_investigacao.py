"""Cartão de investigação (passo 4): decisão CONCORDO/DISCORDO/VERIFICAR no servidor e o HTML do cartão.

O HTML é montado no navegador (app/pagina.html); aqui as funções puras da página rodam no Node (se houver)
com um grupo e uma saída de IA montados à mão com os campos novos do contrato (PLANO_IA_02)."""
import csv
import io
import json
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest

from app import servidor
from src.leitores import achatar, descobrir_arquivos

PAGINA = Path(servidor.__file__).with_name("pagina.html")


# ------------------------------------------------ servidor
class ClienteIANovo:
    """Cliente falso que responde com os campos novos (categoria, explicação, evidências com ref)."""

    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        texto = kw["messages"][0]["content"]
        g = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])["id_grupo"]
        resp = {"id_grupo": g, "resumo": f"Resumo {g}.", "conferir": ["Pedir à Orbe a data da mudança."], "falar_com": "Orbe",
                "dado_faltante": "",
                "hipoteses": [{"causa_categoria": "REAJUSTE_SEM_CONTRATO", "causa": f"Reajuste sem contrato em {g}",
                               "explicacao": "A Orbe subiu a taxa sem que o contrato mude.",
                               "evidencias": [{"texto": "A diferença é igual nas faixas de crédito", "ref": "F1"}],
                               "fatos_citados": ["F1", "F2"], "fatos_contrarios": [], "confianca": "alta"}]}
        return SimpleNamespace(model="modelo-falso-2", stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(resp, ensure_ascii=False))])


def _json(url, metodo="GET", corpo=None, cab=None):
    r = urllib.request.Request(url, data=corpo, method=metodo, headers=cab or {})
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())


def _decidir(url, **corpo):
    return _json(url + "/api/ia/decidir", "POST", json.dumps(corpo).encode("utf-8"), {"Content-Type": "application/json"})


@pytest.fixture()
def servidor_com_ia(raiz, tmp_path):
    srv = servidor.criar_servidor(porta=0, pasta_meses=tmp_path / "meses", cliente_ia=ClienteIANovo())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    for p in achatar(descobrir_arquivos(raiz)):
        _json(url + "/api/enviar", "POST", p.read_bytes(), {"X-Nome-Arquivo": quote(p.name)})
    e = _json(url + "/api/rodar", "POST", b"")
    assert e["erro"] is None, e["erro"]
    e = _json(url + "/api/ia/gerar", "POST", b"")
    for _ in range(100):
        if e["investigacao"]["ia_estado"] == "pronto":
            break
        time.sleep(0.1)
        e = _json(url + "/api/estado")
    yield url, Path(e["pasta"]), e["investigacao"]
    srv.shutdown()
    srv.server_close()


def test_verificar_e_discordo_exigem_comentario(servidor_com_ia):
    url, pasta, _ = servidor_com_ia
    for dec in ("VERIFICAR", "DISCORDO"):
        for comentario in ("", "   "):
            with pytest.raises(urllib.error.HTTPError) as exc:
                _decidir(url, id_grupo="G01", hipotese_n=1, decisao=dec, comentario=comentario, analista="Helena")
            assert exc.value.code == 400
            assert "comentário" in json.loads(exc.value.read())["aviso_ia"].lower()
    assert not [p for p in pasta.glob("decisoes_investigacao.csv") if p.read_text(encoding="utf-8").count("\n") > 1]


def test_decisao_antiga_nao_vale_mais(servidor_com_ia):
    url, _, _ = servidor_com_ia
    with pytest.raises(urllib.error.HTTPError) as exc:
        _decidir(url, id_grupo="G01", hipotese_n=1, decisao="ACEITA", analista="Helena")
    assert exc.value.code == 400


def test_concordo_grava_csv_com_categoria(servidor_com_ia):
    url, pasta, inv = servidor_com_ia
    h = next(g for g in inv["ia"]["grupos"] if g["id_grupo"] == "G01")["hipoteses"][0]
    assert h["causa_categoria"] == "REAJUSTE_SEM_CONTRATO"
    e = _decidir(url, id_grupo="G01", hipotese_n=1, decisao="CONCORDO", analista="Helena")
    _decidir(url, id_grupo="G02", hipotese_n=1, decisao="VERIFICAR", comentario="Pedir o e-mail ao Comercial", analista="Helena")
    assert e["investigacao"]["decisoes"][0]["decisao"] == "CONCORDO"
    linhas = list(csv.DictReader(io.StringIO((pasta / "decisoes_investigacao.csv").read_text(encoding="utf-8")), delimiter=";"))
    assert list(linhas[0]) == servidor.COLUNAS_DECISOES and "causa_categoria" in linhas[0]
    assert [(l["id_grupo"], l["decisao"], l["causa_categoria"]) for l in linhas] == [
        ("G01", "CONCORDO", "REAJUSTE_SEM_CONTRATO"), ("G02", "VERIFICAR", "REAJUSTE_SEM_CONTRATO")]
    assert linhas[1]["comentario"] == "Pedir o e-mail ao Comercial" and linhas[0]["analista"] == "Helena"


def test_estado_expoe_rotulos_de_categoria(servidor_com_ia):
    _, _, inv = servidor_com_ia
    assert isinstance(inv["rotulos_categoria"], dict)


# ------------------------------------------------ HTML do cartão (funções puras da página, no Node)
GRUPO = {
    "id_grupo": "G01", "contraparte": "ORBE", "linha_negocio": "CHECKOUT", "lojista": "Loja Exemplo Ltda", "natureza": "CONTRATO",
    "qtd": 58, "valor_divergencia_brl": "1600.00", "valor_devolver_lojista_brl": "1545.86", "valor_recuperar_parceiro_brl": "1545.86",
    "resumo_fatos": "Desde 12/09 a Orbe cobra +0,50 p.p. no crédito; débito e Pix corretos.",
    "acao_regra": {"texto": "Devolver ao lojista R$ 1.545,86 e contestar o mesmo valor com a Orbe.", "regras": ["R13", "R68"]},
    "rota_valores": [
        {"id": "V1", "faixa": "CREDITO A VISTA", "de": "2026-09-01", "ate": "2026-09-11", "taxa_aplicada": "2.49", "taxa_contratada": "2.49", "qtd": 20, "diverge": False},
        {"id": "V2", "faixa": "CREDITO A VISTA", "de": "2026-09-12", "ate": "2026-09-30", "taxa_aplicada": "2.99", "taxa_contratada": "2.49", "qtd": 38, "diverge": True}],
    "condicoes_cliente": [{"id": "P10", "origem": "planilha linha 10", "texto": "desde 01/01/2026: crédito à vista 2,49%"}],
    "regras_aplicaveis": [{"id": "R13", "texto": "Divergência de contrato: devolve e cobra o parceiro."}, {"id": "R68", "texto": "Texto R68."}],
    "fatos": [{"id": "F1", "texto": "58 transações divergentes.", "refs": []}], "respostas_financeiro": [], "exemplos": ["TX1"],
}
IA = {"id_grupo": "G01", "resumo": "Resumo.", "conferir": ["Pedir à Orbe a data da mudança."], "falar_com": "Orbe",
      "modelo_resposta": "modelo-x", "versao_prompt": "v4", "aviso": "Aviso fixo da IA.", "ajustes": [{"ajuste": "confiança rebaixada", "causa": "c"}],
      "hipoteses": [
          {"causa_categoria": "REAJUSTE_SEM_CONTRATO", "causa": "Reajuste", "explicacao": "A Orbe subiu a taxa sem contrato.",
           "evidencias": [{"texto": "A diferença é de +0,50 p.p. nas três faixas", "ref": "V2"}], "fatos_citados": ["F1"],
           "fatos_contrarios": ["F1"], "confianca": "media"},
          {"causa_categoria": "TABELA_DESATUALIZADA_NO_PARCEIRO", "causa": "Tabela velha", "explicacao": "Pode ser tabela antiga.",
           "evidencias": [], "fatos_citados": ["F1"], "fatos_contrarios": [], "confianca": "baixa"}]}
ROTULOS = {"REAJUSTE_SEM_CONTRATO": "Reajuste sem contrato", "TABELA_DESATUALIZADA_NO_PARCEIRO": "Tabela desatualizada no parceiro"}


def _renderizar(grupo, ia, decisao=None, rotulos=None):
    """Roda cartaoHTML da página no Node, com um $ falso (analista = Helena); devolve o HTML."""
    fonte = PAGINA.read_text(encoding="utf-8")
    ini = fonte.index("// ------------------------------------------------ investigação de divergências")
    fim = fonte.index('$("analista").addEventListener("input"')
    esc_ = fonte[fonte.index("const esc ="):fonte.index("const tamanho")]
    codigo = (f"const $ = () => ({{ value: 'Helena' }}); {esc_}\n{fonte[ini:fim]}\n"
              f"rotulos = {json.dumps(rotulos or {})};\n"
              f"process.stdout.write(cartaoHTML({json.dumps(grupo)}, {json.dumps(ia)}, {json.dumps(decisao)}, false, true));")
    r = subprocess.run([shutil.which("node"), "-"], input=codigo, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node não instalado")


@needs_node
def test_cartao_com_ia_mostra_o_essencial_em_ordem():
    h = _renderizar(GRUPO, IA, rotulos=ROTULOS)
    ordem = ["Loja Exemplo Ltda", "Orbe", "Divergência de contrato", "O que aconteceu", "Desde 12/09 a Orbe cobra", "Linha do tempo",
             "Ação pela regra", "definido pela regra, não pela IA", "Causa provável", "sugestão da IA · confiança", "Reajuste sem contrato",
             "Por quê:", "Contra:", "Outras possibilidades", "Para confirmar", "Falar com:", "Sua decisão", "Ver detalhes"]
    pos = [h.index(t) for t in ordem]
    assert pos == sorted(pos), dict(zip(ordem, pos))
    cab = h[:h.index("O que aconteceu")]
    assert "Devolver e contestar R$ 1.545,86" in cab
    assert "Diferença pela fórmula da lista de divergências" in h[h.index('<details class="detalhes">'):]
    assert "R$ 1.545,86" in h and "A diferença é de +0,50 p.p. nas três faixas" in h
    assert "REAJUSTE_SEM_CONTRATO" not in h                         # categoria sempre em texto legível
    assert 'data-ref-ir="V2"' in h and 'data-ref="V2"' in h        # ref clicável aponta para a linha do tempo
    assert "Tabela desatualizada no parceiro" in h
    for dec in ("Concordo", "Discordo", "Preciso verificar"):
        assert dec in h


@needs_node
def test_linha_do_tempo_destaca_divergentes_e_acao_tem_texto_da_regra():
    h = _renderizar(GRUPO, IA, rotulos=ROTULOS)
    assert 'data-ref="V1" class="ok"' in h and 'data-ref="V2" class="div"' in h
    assert "2,99%" in h and "2,49%" in h and "12/09/2026 a 30/09/2026" in h and "Crédito à vista" in h
    assert 'title="Divergência de contrato: devolve e cobra o parceiro."' in h      # texto da regra ao passar o mouse


@needs_node
def test_cartao_sem_ia_mostra_1_a_4_e_8_e_o_botao():
    h = _renderizar(GRUPO, None)
    for t in ("O que aconteceu", "Linha do tempo", "Ação pela regra", "Ver detalhes", "Gerar hipóteses com IA", "data-gerar",
              "Condições do cliente", "Regras aplicáveis", "Exemplos de transação"):
        assert t in h, t
    assert "Por quê" not in h and "data-decidir" not in h


@needs_node
def test_cartao_tolera_dossie_e_ia_sem_campos_novos():
    velho = {k: v for k, v in GRUPO.items() if k not in ("resumo_fatos", "acao_regra", "rota_valores", "condicoes_cliente", "regras_aplicaveis")}
    velho["condicao_contratual"] = "Planilha linha 13"
    ia_velha = {"id_grupo": "G01", "hipoteses": [{"causa": "Causa livre antiga", "fatos_citados": ["F1"], "fatos_contrarios": [], "confianca": "alta"}]}
    h = _renderizar(velho, ia_velha)
    assert "58 transações divergentes." in h and "Devolver ao lojista" in h and "Causa livre antiga" in h
    assert "Linha do tempo" not in h and "Planilha linha 13" in h


@needs_node
def test_status_decidido_aparece_no_cartao():
    d = {"decisao": "VERIFICAR", "analista": "Helena", "data_hora": "2026-10-01T10:00:00", "comentario": "Falta o e-mail"}
    h = _renderizar(GRUPO, IA, decisao=d, rotulos=ROTULOS)
    assert "pendente de checagem" in h and "Falta o e-mail" in h and "dec-verificar" in h


@needs_node
def test_nada_de_codigo_solto_fora_dos_detalhes():
    h = _renderizar(GRUPO, IA, rotulos=ROTULOS)
    fora = h[:h.index('<details class="detalhes">')]
    import re
    sem_refs = re.sub(r'<button[^>]*class="ref".*?</button>|<span class="regra".*?</span>|data-[a-z-]+="[^"]*"|title="[^"]*"', "", fora, flags=re.S)
    assert not re.search(r"\b(F\d+|S\d{2}|C\d{3})\b", sem_refs)
