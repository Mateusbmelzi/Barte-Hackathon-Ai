"""Testes da IA de investigação, sem rede: o cliente da API é falso e injetado."""
import io
import json
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import ia

FIXTURE = Path(__file__).parent / "fixtures" / "dossie_exemplo.json"


@pytest.fixture
def dossie():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ClienteFalso:
    """Imita client.messages.create; devolve respostas por id_grupo e guarda as chamadas."""

    def __init__(self, respostas=None, erro=None, stop_reason="end_turn", modelo="claude-sonnet-5-5"):
        self.respostas = respostas or {}
        self.erro = erro
        self.stop_reason = stop_reason
        self.modelo = modelo
        self.chamadas = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        if self.erro:
            raise self.erro
        texto = kwargs["messages"][0]["content"]
        dados = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        resposta = self.respostas.get(dados["id_grupo"], _resposta_padrao(dados["id_grupo"]))
        return SimpleNamespace(
            model=self.modelo,
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="text", text=json.dumps(resposta, ensure_ascii=False))],
        )


def _resposta_padrao(id_grupo, hipoteses=None):
    return {
        "id_grupo": id_grupo,
        "resumo": "Resumo de teste.",
        "hipoteses": hipoteses if hipoteses is not None else [
            {"causa": "Causa sustentada.", "fatos_citados": ["F1"], "confianca": "alta"},
        ],
        "conferir": ["Conferir algo."],
        "falar_com": "Orbe",
        "dado_faltante": "nenhum",
    }


def _grupo(resultado, id_grupo):
    return next(g for g in resultado["grupos"] if g["id_grupo"] == id_grupo)


def test_hipotese_sem_fato_descartada(dossie):
    cliente = ClienteFalso({"G02": _resposta_padrao("G02", [
        {"causa": "Sem fato.", "fatos_citados": [], "confianca": "alta"},
        {"causa": "Com fato.", "fatos_citados": ["F3", "S06"], "confianca": "alta"},
    ])})
    g = _grupo(ia.investigar(dossie, cliente=cliente), "G02")
    assert [h["causa"] for h in g["hipoteses"]] == ["Com fato."]
    assert g["hipoteses_descartadas"] == 1
    assert "nenhum fato" in g["motivos_descarte"][0]["motivo"]


def test_id_inexistente_descartado(dossie):
    # F10 existe na Rota (G02), mas não na Bridge (G04); S06 também não é da Bridge.
    cliente = ClienteFalso({"G04": _resposta_padrao("G04", [
        {"causa": "ID de outro grupo.", "fatos_citados": ["F3", "F10"], "confianca": "alta"},
        {"causa": "Resposta de outro grupo.", "fatos_citados": ["S06"], "confianca": "media"},
        {"causa": "Vigência anterior.", "fatos_citados": ["F3", "F4", "S30"], "confianca": "alta"},
    ])})
    g = _grupo(ia.investigar(dossie, cliente=cliente), "G04")
    assert [h["causa"] for h in g["hipoteses"]] == ["Vigência anterior."]
    assert g["hipoteses_descartadas"] == 2
    assert "F10" in g["motivos_descarte"][0]["motivo"]


def test_limite_de_tres_hipoteses(dossie):
    hips = [{"causa": f"H{i}", "fatos_citados": ["F1"], "confianca": "media"} for i in range(5)]
    cliente = ClienteFalso({"G01": _resposta_padrao("G01", hips)})
    g = _grupo(ia.investigar(dossie, cliente=cliente), "G01")
    assert [h["causa"] for h in g["hipoteses"]] == ["H0", "H1", "H2"]
    assert g["hipoteses_descartadas"] == 2


def test_sem_chave_indisponivel_e_nao_quebra(dossie, monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(ia, "_biblioteca_instalada", lambda: True)
    ok, motivo = ia.disponivel(tmp_path)  # tmp_path sem .env
    assert ok is False and "ANTHROPIC_API_KEY" in motivo
    r = ia.investigar(dossie, raiz=tmp_path)
    assert len(r["grupos"]) == 4
    assert all(g["erro"] and "ANTHROPIC_API_KEY" in g["erro"] for g in r["grupos"])
    assert all(g["hipoteses"] == [] for g in r["grupos"])


def test_sem_biblioteca_indisponivel(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")
    monkeypatch.setattr(ia, "_biblioteca_instalada", lambda: False)
    ok, motivo = ia.disponivel(tmp_path)
    assert ok is False and "anthropic" in motivo


def test_chave_lida_do_env(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env").write_text('# comentario\nOUTRA=1\nANTHROPIC_API_KEY="chave-do-arquivo"\n', encoding="utf-8")
    assert ia.obter_chave(tmp_path) == "chave-do-arquivo"


def test_erro_do_cliente_vira_erro_do_grupo(dossie):
    r = ia.investigar(dossie, cliente=ClienteFalso(erro=TimeoutError("lento")))
    assert len(r["grupos"]) == 4
    assert all("tempo esgotado" in g["erro"] for g in r["grupos"])


def test_recusa_e_json_invalido_viram_erro(dossie):
    r = ia.investigar(dossie, cliente=ClienteFalso(stop_reason="refusal"))
    assert all("recusou" in g["erro"] for g in r["grupos"])
    cliente = ClienteFalso()
    cliente._create = lambda **k: SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="não é json")])
    cliente.messages.create = cliente._create
    r = ia.investigar(dossie, cliente=cliente)
    assert all("JSON" in g["erro"] for g in r["grupos"])


def test_saida_tem_aviso_modelo_versao(dossie):
    r = ia.investigar(dossie, cliente=ClienteFalso())
    assert r["aviso"] == "Sugestão da IA, não verificada. A decisão é da analista."
    assert r["modelo"] == "claude-sonnet-5-5"
    assert r["versao_prompt"] == "investigacao-v3"
    for g in r["grupos"]:
        assert g["aviso"] == ia.AVISO
        assert g["modelo"] == "claude-sonnet-5-5"
        assert g["versao_prompt"] == "investigacao-v3"
        assert g["modelo_resposta"] == "claude-sonnet-5-5"
        assert g["erro"] is None


def test_chamada_usa_saida_estruturada_e_uma_por_grupo(dossie):
    cliente = ClienteFalso()
    ia.investigar(dossie, cliente=cliente)
    assert len(cliente.chamadas) == 4
    k = cliente.chamadas[0]
    assert k["model"] == "claude-sonnet-5-5"
    assert k["output_config"]["format"] == {"type": "json_schema", "schema": ia.SCHEMA_SAIDA}
    assert "temperature" not in k  # Sonnet 5.5 rejeita sampling não padrão
    assert "fallbacks" not in k and "betas" not in k  # sem fallback: quem responde é o Sonnet 5.5


def test_mensagem_contem_so_o_grupo(dossie):
    cliente = ClienteFalso()
    ia.investigar(dossie, cliente=cliente)
    # Termos de outros grupos (a S30 de G01/G03/G04 cita Bridge, Casa e Mundo Aberto, por isso ficam de fora ali).
    # Ordem do dossiê real: G01 Casa, G02 Rota, G03 Mundo Aberto (Ponte), G04 Bridge.
    outros = {"G01": ["Rota", "PC-0926", "1074504011"],
              "G02": ["Casa do Estudante", "Bridge", "Mundo Aberto", "TX88410932"],
              "G03": ["Rota", "TX884", "1074504011"],
              "G04": ["Rota", "PC-0926", "1018325654"]}
    for chamada in cliente.chamadas:
        texto = chamada["messages"][0]["content"]
        dados = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        gid = dados["id_grupo"]
        original = next(g for g in dossie["grupos"] if g["id_grupo"] == gid)
        assert dados["fatos"] == original["fatos"]
        for termo in outros[gid]:
            assert termo not in texto, f"{gid} vazou {termo}"
        for outro in dossie["grupos"]:
            if outro["id_grupo"] != gid:
                assert outro["id_grupo"] not in texto


def test_recusa_sem_fallback_registra_modelo_que_respondeu(dossie):
    r = ia.investigar(dossie, cliente=ClienteFalso(stop_reason="refusal"))
    for g in r["grupos"]:
        assert "recusou" in g["erro"] and g["hipoteses"] == []
        assert g["modelo"] == "claude-sonnet-5-5"
        assert g["modelo_resposta"] == "claude-sonnet-5-5"


def test_prompt_nao_contem_casos_de_setembro():
    texto = ia.montar_system().split("---", 1)[1]  # só o prompt de investigação
    for termo in ["Rota", "Bridge", "Casa do Estudante", "Mundo Aberto", "12/09", "15/09",
                  "0,50 p.p.", "S06", "vigência anterior"]:
        assert termo not in texto, termo


# ---------------------------------------------------------------- OpenRouter (urlopen falso)
CHAVE_OR = "sk-or-teste"


class _Resp:
    def __init__(self, corpo):
        self._corpo = json.dumps(corpo).encode("utf-8")

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_erro(codigo, mensagem="falhou", headers=None):
    corpo = json.dumps({"error": {"code": codigo, "message": mensagem}}).encode("utf-8")
    return urllib.error.HTTPError(ia.URL_OPENROUTER, codigo, "erro", headers or {}, io.BytesIO(corpo))


class UrlopenFalso:
    """Responde por id_grupo no formato chat/completions; pode levantar erros em sequência."""

    def __init__(self, erros=None, modelo="anthropic/claude-sonnet-5.5", respostas=None, conteudo=None):
        self.erros = list(erros or [])
        self.modelo = modelo
        self.respostas = respostas or {}
        self.conteudo = conteudo
        self.pedidos = []

    def __call__(self, req, timeout=None):
        self.pedidos.append({"req": req, "timeout": timeout, "corpo": json.loads(req.data.decode("utf-8"))})
        if self.erros:
            raise self.erros.pop(0)
        corpo = self.pedidos[-1]["corpo"]
        texto = corpo["messages"][1]["content"]
        gid = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])["id_grupo"]
        conteudo = self.conteudo if self.conteudo is not None else json.dumps(
            self.respostas.get(gid, _resposta_padrao(gid)), ensure_ascii=False)
        return _Resp({"id": "gen-1", "model": self.modelo,
                      "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": conteudo}}]})


def _cliente_or(urlopen):
    return ia.ClienteOpenRouter(CHAVE_OR, urlopen=urlopen, dormir=lambda s: None)


def test_openrouter_payload(dossie):
    falso = UrlopenFalso()
    ia.investigar(dossie, cliente=_cliente_or(falso))
    assert len(falso.pedidos) == 4
    p = falso.pedidos[0]
    req, corpo = p["req"], p["corpo"]
    assert req.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == f"Bearer {CHAVE_OR}"
    assert p["timeout"] == 90.0
    assert corpo["model"] == "anthropic/claude-sonnet-5.5"
    assert [m["role"] for m in corpo["messages"]] == ["system", "user"]
    assert corpo["messages"][0]["content"] == ia.montar_system()
    rf = corpo["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == ia.SCHEMA_SAIDA
    assert corpo["reasoning"] == {"effort": "medium"}
    assert "models" not in corpo  # sem lista de modelos alternativos
    assert corpo["provider"]["allow_fallbacks"] is False
    assert "temperature" not in corpo
    assert CHAVE_OR not in json.dumps(corpo)  # chave só no cabeçalho


def test_openrouter_parsing_e_modelo_resposta(dossie):
    falso = UrlopenFalso(respostas={"G03": _resposta_padrao("G03", [
        {"causa": "Válida.", "fatos_citados": ["F3", "S30"], "confianca": "alta"},
        {"causa": "ID alheio.", "fatos_citados": ["S06"], "confianca": "baixa"},
    ])})
    r = ia.investigar(dossie, cliente=_cliente_or(falso))
    assert r["provedor"] == "openrouter" and r["modelo"] == "anthropic/claude-sonnet-5.5"
    g = _grupo(r, "G03")
    assert g["erro"] is None and g["provedor"] == "openrouter"
    assert g["modelo_resposta"] == "anthropic/claude-sonnet-5.5"
    assert [h["causa"] for h in g["hipoteses"]] == ["Válida."]
    assert g["hipoteses_descartadas"] == 1
    assert g["aviso"] == ia.AVISO and g["versao_prompt"] == "investigacao-v3"
    assert CHAVE_OR not in json.dumps(r, ensure_ascii=False)


def test_openrouter_401_legivel_sem_chave(dossie):
    falso = UrlopenFalso(erros=[_http_erro(401, f"bad key {CHAVE_OR}")] * 4)
    r = ia.investigar(dossie, cliente=_cliente_or(falso))
    assert len(falso.pedidos) == 4  # 401 não é repetido
    for g in r["grupos"]:
        assert "chave inválida ou sem crédito" in g["erro"]
    assert CHAVE_OR not in json.dumps(r, ensure_ascii=False)


def test_openrouter_402(dossie):
    r = ia.investigar(dossie, cliente=_cliente_or(UrlopenFalso(erros=[_http_erro(402)] * 4)))
    assert all("sem crédito no OpenRouter" in g["erro"] for g in r["grupos"])


def test_openrouter_429_repete_e_recupera(dossie):
    falso = UrlopenFalso(erros=[_http_erro(429, headers={"Retry-After": "1"}), _http_erro(503)])
    r = ia.investigar(dossie, cliente=_cliente_or(falso))
    assert all(g["erro"] is None for g in r["grupos"])
    assert len(falso.pedidos) == 6  # G01 precisou de 3 tentativas


def test_openrouter_429_persistente_vira_erro(dossie):
    falso = UrlopenFalso(erros=[_http_erro(429)] * 12)
    r = ia.investigar(dossie, cliente=_cliente_or(falso))
    assert len(falso.pedidos) == 12  # 3 tentativas por grupo
    assert all("limite de uso" in g["erro"] for g in r["grupos"])


def test_openrouter_conteudo_invalido(dossie):
    r = ia.investigar(dossie, cliente=_cliente_or(UrlopenFalso(conteudo="isto não é json")))
    assert all("JSON" in g["erro"] for g in r["grupos"])


def test_selecao_de_provedor(monkeypatch, tmp_path):
    for v in ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    assert ia.selecionar_provedor(tmp_path) == (None, None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-normal")
    assert ia.selecionar_provedor(tmp_path)[0] == "anthropic"
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE_OR)
    assert ia.selecionar_provedor(tmp_path)[0] == "openrouter"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-normal")
    monkeypatch.setenv("OPENROUTER_API_KEY", CHAVE_OR)
    assert ia.selecionar_provedor(tmp_path)[0] == "openrouter"


def test_openrouter_disponivel_sem_biblioteca_e_via_env(dossie, monkeypatch, tmp_path):
    for v in ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    (tmp_path / ".env").write_text(f"ANTHROPIC_API_KEY={CHAVE_OR}\n", encoding="utf-8")
    monkeypatch.setattr(ia, "_biblioteca_instalada", lambda: False)
    ok, motivo = ia.disponivel(tmp_path)
    assert ok is True and "OpenRouter" in motivo and CHAVE_OR not in motivo
    falso = UrlopenFalso()
    monkeypatch.setattr(ia.urllib.request, "urlopen", falso)
    r = ia.investigar(dossie, raiz=tmp_path)
    assert r["provedor"] == "openrouter" and len(falso.pedidos) == 4
    assert all(g["erro"] is None for g in r["grupos"])
    assert repr(ia.ClienteOpenRouter(CHAVE_OR)) == "ClienteOpenRouter(chave=***)"


# ---------------------------------------------------------------- fatos contrários (prompt v3)
def _validar(hipoteses, grupo_id="G02"):
    dossie = json.loads(FIXTURE.read_text(encoding="utf-8"))
    grupo = next(g for g in dossie["grupos"] if g["id_grupo"] == grupo_id)
    return ia.validar(_resposta_padrao(grupo_id, hipoteses), grupo)


def test_schema_exige_fatos_contrarios():
    item = ia.SCHEMA_SAIDA["properties"]["hipoteses"]["items"]
    assert "fatos_contrarios" in item["properties"] and "fatos_contrarios" in item["required"]
    assert item["additionalProperties"] is False


def test_contrario_inexistente_remove_id_e_mantem_hipotese():
    r = _validar([{"causa": "C", "fatos_citados": ["F3"], "fatos_contrarios": ["F4", "F99", "S77"],
                   "confianca": "baixa"}])
    assert len(r["hipoteses"]) == 1 and r["hipoteses_descartadas"] == 0
    assert r["hipoteses"][0]["fatos_contrarios"] == ["F4"]
    assert "F99" in r["ajustes"][0]["ajuste"] and "S77" in r["ajustes"][0]["ajuste"]


def test_alta_com_contrario_vira_media():
    r = _validar([{"causa": "C", "fatos_citados": ["F3", "S06"], "fatos_contrarios": ["F6"], "confianca": "alta"}])
    h = r["hipoteses"][0]
    assert h["confianca"] == "media" and h["fatos_contrarios"] == ["F6"]
    assert any("rebaixada" in a["ajuste"] for a in r["ajustes"])


def test_alta_com_contrario_so_inexistente_continua_alta():
    r = _validar([{"causa": "C", "fatos_citados": ["F3"], "fatos_contrarios": ["F99"], "confianca": "alta"}])
    assert r["hipoteses"][0]["confianca"] == "alta" and r["hipoteses"][0]["fatos_contrarios"] == []


def test_sem_contrarios_fica_lista_vazia_e_sem_ajuste():
    r = _validar([{"causa": "C", "fatos_citados": ["F3"], "confianca": "alta"}])
    assert r["hipoteses"][0]["fatos_contrarios"] == [] and r["ajustes"] == []


def test_ordena_por_confianca_estavel_e_corta_em_tres():
    r = _validar([
        {"causa": "B1", "fatos_citados": ["F1"], "fatos_contrarios": [], "confianca": "baixa"},
        {"causa": "M1", "fatos_citados": ["F1"], "fatos_contrarios": [], "confianca": "media"},
        {"causa": "A->M", "fatos_citados": ["F1"], "fatos_contrarios": ["F4"], "confianca": "alta"},
        {"causa": "A1", "fatos_citados": ["F1"], "fatos_contrarios": [], "confianca": "alta"},
    ])
    assert [h["causa"] for h in r["hipoteses"]] == ["A1", "M1", "A->M"]
    assert r["hipoteses_descartadas"] == 1 and "limite" in r["motivos_descarte"][0]["motivo"]


def test_contrarios_pelo_caminho_openrouter(dossie):
    falso = UrlopenFalso(respostas={"G02": _resposta_padrao("G02", [
        {"causa": "Tabela 2025.", "fatos_citados": ["F6", "S06"], "fatos_contrarios": ["F6", "F42"], "confianca": "alta"},
    ])})
    g = _grupo(ia.investigar(dossie, cliente=_cliente_or(falso)), "G02")
    assert g["hipoteses"][0] == {"causa": "Tabela 2025.", "fatos_citados": ["F6", "S06"],
                                 "fatos_contrarios": ["F6"], "confianca": "media"}
    assert len(g["ajustes"]) == 2


def test_prompt_v3_tem_regras_de_contradicao():
    texto = ia.montar_system()
    assert "fatos_contrarios" in texto
    assert "Não repita a mesma causa em duas hipóteses" in texto
    assert "contradiz" in texto
