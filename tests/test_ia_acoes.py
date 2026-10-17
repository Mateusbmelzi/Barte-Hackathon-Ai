"""Testes da IA de ações sugeridas (PLANO_03), sem rede: o cliente é falso e injetado."""
import json

import pytest

from src import ia, ia_acoes

ITEM = {
    "chave": "PEN|DEVOLUCAO_LOJISTA_ISENCAO|EC 1000000001", "tipo": "DEVOLUCAO_LOJISTA_ISENCAO",
    "titulo": "Devolução ao lojista por isenção", "valor": "1234.56",
    "motivo": "A Orbe cobrou pela planilha em 10 transações; a devolver R$ 1.234,56 do caixa da Tarvo.",
    "quem_decide": "Helena (Financeiro) / Comercial", "lojista": "Loja Modelo Ltda", "cnpj": "11111111000111",
}
CTX = {"competencia": "09/2026", "empresa": "Tarvo", "assinatura": "Helena — Financeiro Tarvo"}
PERMITIDOS = ["COMERCIAL", "LOJISTA"]


class ClienteFalso:
    provedor = "falso"
    modelo = "claude-sonnet-5-5"

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.chamadas = resposta, erro, []

    def gerar(self, system, mensagem):
        self.chamadas.append((system, mensagem))
        if self.erro:
            raise self.erro
        return self.resposta, "claude-sonnet-5-5"


def resposta(emails, destinos=("COMERCIAL", "LOJISTA"), acao="Alinhar com o Comercial e avisar o lojista."):
    return {"chave": ITEM["chave"], "acao_resumo": acao, "destinos": list(destinos), "emails": emails,
            "prazo_sugerido": "até 3 dias úteis", "valores_citados": []}


def email(papel="COMERCIAL", assunto="Confirmação de isenção", corpo=None):
    corpo = corpo or ("Olá,\n\nA devolução de R$ 1.234,56 ao lojista depende da sua confirmação.\n\n"
                      "Helena — Financeiro Tarvo")
    return {"papel": papel, "assunto": assunto, "corpo": corpo}


def run(emails, **kw):
    return ia_acoes.sugerir(ITEM, CTX, kw.pop("permitidos", PERMITIDOS), cliente=ClienteFalso(resposta(emails, **kw)))


def test_caminho_feliz():
    r = run([email()])
    assert r["erro"] is None and r["ajustes"] == []
    assert r["chave"] == ITEM["chave"]
    assert r["emails"][0]["papel"] == "COMERCIAL" and r["destinos"] == ["COMERCIAL", "LOJISTA"]
    assert r["valores_citados"] == ["R$ 1.234,56"]
    assert r["aviso"] == "Rascunho da IA — revise antes de enviar"
    assert r["prazo_sugerido"] == "até 3 dias úteis"


def test_destino_fora_do_permitido_removido_e_email_junto():
    r = run([email("ORBE"), email("COMERCIAL")], destinos=("ORBE", "COMERCIAL"))
    assert r["destinos"] == ["COMERCIAL"]
    assert [e["papel"] for e in r["emails"]] == ["COMERCIAL"]
    assert any("ORBE" in a for a in r["ajustes"])


def test_valor_inventado_descarta_so_aquele_email():
    ruim = email("COMERCIAL", corpo="Olá, a devolução de R$ 9.999,00 está pendente.\n\nHelena — Financeiro Tarvo")
    bom = email("LOJISTA", corpo="Prezados, haverá crédito de R$ 1.234,56 conforme aprovação do "
                                 "financeiro.\n\nHelena — Financeiro Tarvo")
    r = run([ruim, bom])
    assert [e["papel"] for e in r["emails"]] == ["LOJISTA"]
    assert any("9.999,00" in a for a in r["ajustes"])


def test_valor_com_formato_diferente_mas_igual_e_aceito():
    r = run([email(corpo="Valor: R$ 1234,56.\n\nHelena — Financeiro Tarvo")])
    assert len(r["emails"]) == 1 and r["ajustes"] == []


def test_valor_do_campo_valor_sem_motivo():
    item = {**ITEM, "motivo": "Sem valores aqui."}
    r = ia_acoes.sugerir(item, CTX, PERMITIDOS, cliente=ClienteFalso(resposta([email()])))
    assert len(r["emails"]) == 1


def test_afirmar_que_ja_foi_feito_descarta():
    for texto in ("A devolução já foi feita ao lojista.", "Já devolvemos o valor.", "O estorno foi efetuado.",
                  "Já estornamos o valor."):
        r = run([email(corpo=texto + "\n\nHelena — Financeiro Tarvo")])
        assert r["emails"] == [], texto
        assert any("já foi feita" in a for a in r["ajustes"]), texto


def test_promessa_sem_conforme_aprovacao_descarta_e_com_aceita():
    sem = email("LOJISTA", corpo="Devolveremos o valor em breve.\n\nHelena — Financeiro Tarvo")
    com = email("LOJISTA", corpo="Devolveremos o valor, conforme aprovação do financeiro.\n\nHelena — Financeiro Tarvo")
    assert run([sem])["emails"] == []
    assert len(run([com])["emails"]) == 1


def test_assunto_longo_e_cortado_corpo_longo_descartado():
    r = run([email(assunto="A" * 200)])
    assert len(r["emails"][0]["assunto"]) <= 90
    r = run([email(corpo="x" * 1600)])
    assert r["emails"] == [] and any("máx. 1500" in a for a in r["ajustes"])


def test_assinatura_acrescentada_quando_falta():
    r = run([email(corpo="Olá, pode confirmar a isenção?")])
    assert r["emails"][0]["corpo"].endswith("Helena — Financeiro Tarvo")


def test_acao_resumo_com_valor_inventado_cai_para_o_objetivo():
    ctx = {**CTX, "objetivo": "Alinhar com o Comercial."}
    r = ia_acoes.sugerir(ITEM, ctx, PERMITIDOS, cliente=ClienteFalso(resposta([], acao="Devolver R$ 50,00.")))
    assert r["acao_resumo"] == "Alinhar com o Comercial."
    assert any("substituído" in a for a in r["ajustes"])


def test_erro_do_cliente_vira_erro_legivel():
    r = ia_acoes.sugerir(ITEM, CTX, PERMITIDOS, cliente=ClienteFalso(erro=ia.ErroIA("limite de uso atingido.")))
    assert "limite de uso atingido" in r["erro"] and r["emails"] == [] and r["chave"] == ITEM["chave"]
    r = ia_acoes.sugerir(ITEM, CTX, PERMITIDOS, cliente=ClienteFalso(erro=RuntimeError("x")))
    assert "erro inesperado" in r["erro"]


def test_sem_chave_nao_quebra(monkeypatch, tmp_path):
    for v in ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(ia, "RAIZ", tmp_path)
    ok, motivo = ia_acoes.disponivel()
    assert not ok and "Chave" in motivo
    r = ia_acoes.sugerir(ITEM, CTX, PERMITIDOS)
    assert r["erro"] and r["emails"] == []


def test_mensagem_so_tem_o_item_e_destinos():
    c = ClienteFalso(resposta([]))
    item = {**ITEM, "campo_interno_secreto": "NAO_ENVIAR"}
    ia_acoes.sugerir(item, CTX, PERMITIDOS, cliente=c)
    msg = c.chamadas[0][1]
    assert "NAO_ENVIAR" not in msg and "COMERCIAL" in msg and "Helena — Financeiro Tarvo" in msg
    assert "ORBE" not in msg


def test_sugerir_todos_ordem_cache_e_destinos_do_tipo(tmp_path):
    c = ClienteFalso(resposta([email()]))
    itens = [ITEM, {**ITEM, "chave": "PEN|X|2"}]
    r = ia_acoes.sugerir_todos(itens, CTX, cliente=c, max_paralelo=2, pasta=tmp_path)
    assert [x["chave"] for x in r] == [ITEM["chave"], "PEN|X|2"]
    assert len(c.chamadas) == 2
    assert (tmp_path / "sugestoes_ia.json").exists()
    c2 = ClienteFalso(erro=RuntimeError("não deveria chamar"))
    r2 = ia_acoes.sugerir_todos(itens, CTX, cliente=c2, pasta=tmp_path)
    assert c2.chamadas == [] and r2 == json.loads(json.dumps(r))


def test_erro_nao_entra_no_cache(tmp_path):
    r = ia_acoes.sugerir_todos([ITEM], CTX, cliente=ClienteFalso(erro=RuntimeError("x")), pasta=tmp_path)
    assert r[0]["erro"]
    assert json.loads((tmp_path / "sugestoes_ia.json").read_text(encoding="utf-8")) == {}


def test_schema_estrito_e_payload_openrouter():
    assert ia_acoes.SCHEMA_SAIDA["additionalProperties"] is False
    assert set(ia_acoes.SCHEMA_SAIDA["required"]) == set(ia_acoes.SCHEMA_SAIDA["properties"])
    cli = ia_acoes._OpenRouterComEsquema("sk-or-x", ia_acoes.SCHEMA_SAIDA, "acao_sugerida")
    p = cli.payload("s", "m")
    assert p["model"] == ia.MODELO_OPENROUTER and p["response_format"]["json_schema"]["strict"] is True
    assert p["response_format"]["json_schema"]["schema"] is ia_acoes.SCHEMA_SAIDA
    assert "sk-or-x" not in repr(cli)


def test_prompt_nao_contem_casos_de_setembro():
    texto = ia_acoes.montar_system().split("---", 1)[1]
    for termo in ["Rota", "Bridge", "Casa do Estudante", "Mundo Aberto", "12/09", "15/09", "01/09", "7.350",
                  "15.396", "0,50 p.p."]:
        assert termo not in texto, termo
    assert ia_acoes.versao_prompt().startswith("acoes-v")


def test_data_inventada_descarta_email_e_data_do_item_ou_competencia_passa():
    item = {**ITEM, "motivo": ITEM["motivo"] + " Cobrança desde 12/09."}
    inventada = email(corpo="Olá, desde 15/09 houve cobrança de R$ 1.234,56.\n\nHelena — Financeiro Tarvo")
    r = ia_acoes.sugerir(item, CTX, PERMITIDOS, cliente=ClienteFalso(resposta([inventada])))
    assert r["emails"] == [] and any("15/09" in a for a in r["ajustes"])
    boa = email(corpo="Olá, desde 12/09, na competência 09/2026, houve cobrança de R$ 1.234,56.\n\n"
                      "Helena — Financeiro Tarvo")
    r = ia_acoes.sugerir(item, CTX, PERMITIDOS, cliente=ClienteFalso(resposta([boa])))
    assert len(r["emails"]) == 1 and r["ajustes"] == []


def test_mensagem_traz_valor_formatado():
    c = ClienteFalso(resposta([]))
    ia_acoes.sugerir({**ITEM, "valor": "7350.00", "motivo": "PIX sem identificação."}, CTX, ["BANCO_AURORA"], cliente=c)
    assert "R$ 7.350,00" in c.chamadas[0][1]


@pytest.mark.parametrize("frase", [
    "O valor foi devolvido ao lojista.", "A taxa foi paga ontem.", "O pagamento realizado já consta.",
    "Já creditamos o valor.", "Estornamos a diferença.", "Os valores foram devolvidos.", "Já foi cobrada a Orbe.",
    "Ressarcimos o lojista.", "A devolução foi efetuada.", "O crédito já foi feito."])
def test_detector_de_ja_feito_ampliado(frase):
    r = run([email(corpo=frase + "\n\nHelena — Financeiro Tarvo")])
    assert r["emails"] == [], frase


@pytest.mark.parametrize("frase", [
    "A Orbe cobrou taxa acima do contratado.", "Solicitamos o estorno do valor.",
    "Devolveremos conforme aprovação do financeiro.", "Pedimos a devolução da diferença."])
def test_frases_legitimas_passam(frase):
    r = run([email(corpo=frase + "\n\nHelena — Financeiro Tarvo")])
    assert len(r["emails"]) == 1, frase


def test_resumo_substituido_guarda_texto_original():
    r = ia_acoes.sugerir(ITEM, {**CTX, "objetivo": "Objetivo."}, PERMITIDOS,
                         cliente=ClienteFalso(resposta([], acao="O valor foi devolvido ao lojista.")))
    assert r["acao_resumo"] == "Objetivo."
    assert any("O valor foi devolvido ao lojista." in a for a in r["ajustes"])


def test_data_iso_percentual_e_valor_numerico_do_item():
    item = {**ITEM, "motivo": "Desde 2026-09-12 a taxa foi 2,49%, +0,50 p.p.", "valor": "15396.77"}
    ctx = CTX
    boa = email(corpo="Desde 12/09 a taxa foi 2,49% (+0,50 p.p.). Valor R$ 15.396,77.\n\nHelena — Financeiro Tarvo")
    r = ia_acoes.sugerir(item, ctx, PERMITIDOS, cliente=ClienteFalso(resposta([boa])))
    assert len(r["emails"]) == 1 and r["ajustes"] == []
    iso = email(corpo="Desde 2026-09-15 houve cobrança.\n\nHelena — Financeiro Tarvo")
    r = ia_acoes.sugerir(item, ctx, PERMITIDOS, cliente=ClienteFalso(resposta([iso])))
    assert r["emails"] == [] and any("15/09" in a for a in r["ajustes"])
    for pct in ("3,10%", "0,75 p.p."):
        ruim = email(corpo=f"A taxa foi {pct}.\n\nHelena — Financeiro Tarvo")
        r = ia_acoes.sugerir(item, ctx, PERMITIDOS, cliente=ClienteFalso(resposta([ruim])))
        assert r["emails"] == [] and any("percentual" in a for a in r["ajustes"]), pct


def test_percentual_da_rota_valores_e_aceito():
    item = {**ITEM, "rota_valores": [{"id": "V1", "taxa_aplicada": "2,49%"}]}
    r = ia_acoes.sugerir(item, CTX, PERMITIDOS,
                         cliente=ClienteFalso(resposta([email(corpo="Taxa de 2,49% aplicada.\n\nHelena — Financeiro Tarvo")])))
    assert len(r["emails"]) == 1


def test_financeiro_interno_vira_nota_interna_sem_email():
    r = ia_acoes.sugerir(ITEM, CTX, ["FINANCEIRO_INTERNO"], cliente=ClienteFalso(
        {**resposta([email("FINANCEIRO_INTERNO")], destinos=("FINANCEIRO_INTERNO",)), "nota_interna": "Conferir o extrato."}))
    assert r["emails"] == [] and r["nota_interna"] == "Conferir o extrato."
    r = ia_acoes.sugerir(ITEM, CTX, ["FINANCEIRO_INTERNO"], cliente=ClienteFalso(
        resposta([email("FINANCEIRO_INTERNO", corpo="Conferir o extrato do mês.")], destinos=("FINANCEIRO_INTERNO",))))
    assert r["emails"] == [] and "Conferir" in r["nota_interna"]
    # sem esse destino permitido, a nota é ignorada
    r = ia_acoes.sugerir(ITEM, CTX, PERMITIDOS, cliente=ClienteFalso({**resposta([]), "nota_interna": "x"}))
    assert r["nota_interna"] == ""


def test_prompt_tem_sequencia_comercial_lojista_e_nota():
    t = ia_acoes.montar_system()
    assert "primeiro confirmar com o Comercial" in t and "nota_interna" in t
