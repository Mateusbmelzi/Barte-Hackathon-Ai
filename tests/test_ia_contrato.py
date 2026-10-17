"""IA de contrato: leitura de texto, extração com guarda-corpos e proposta para o cadastro (sem rede)."""
import copy
import io
import json
import zipfile
from pathlib import Path

import pytest

from src import cadastro as cad, ia_contrato as ic

RAIZ = Path(__file__).resolve().parent.parent
CONTRATO = RAIZ / "tests" / "fixtures" / "contrato_ficticio_exemplo.txt"
CLIENTE = {"nome": "Aurora Intercambio Ltda", "cnpj": "11222333000181", "ec_orbe": "", "origem": "PONTE",
           "contrato_arquivo": "contrato_ficticio_exemplo.txt"}
CTX = {"competencia": "09/2026", "assinatura": "Helena — Financeiro Tarvo"}


class Falso:
    provedor, modelo = "falso", "claude-sonnet-5-5"

    def __init__(self, resposta):
        self.resposta, self.chamadas = resposta, []

    def gerar(self, system, mensagem):
        self.chamadas.append((system, mensagem))
        return copy.deepcopy(self.resposta), "modelo-falso"


def _tx(faixa, valor, ev):
    return {"faixa": faixa, "valor": valor, "evidencia": ev}


def resposta_boa():
    return {
        "partes": {"lojista": "AURORA INTERCAMBIO LTDA", "cnpj": "11.222.333/0001-81"},
        "vigencia_inicio": "2026-10-01", "vigencia_fim": "2028-09-30",
        "taxas": [_tx("DEBITO", "1.59", "Debito: 1,59%"), _tx("CREDITO A VISTA", "2.79", "Credito a vista: 2,79%"),
                  _tx("PARC_2_6", "3.29", "de 2 a 6 vezes: 3,29%"), _tx("PARC_7_12", "3.89", "de 7 a 12 vezes: 3,89%"),
                  _tx("PIX", "0.95", "Pix: 0,95%"), _tx("ANTECIPACAO", "2.15", "Antecipacao de recebiveis: 2,15%"),
                  _tx("SPREAD_REMESSA", "1.35", "spread de 1,35% sobre o valor da operacao")],
        "condicoes_especiais": [{"tipo": "ISENCAO", "descricao": "Isenção de MDR nos 3 primeiros meses",
                                 "faixas": ["DEBITO", "CREDITO A VISTA", "PARC_2_6", "PARC_7_12", "PIX"], "valor": "",
                                 "inicio": "2026-10-01", "fim": "2026-12-31",
                                 "evidencia": "isencao total de MDR (itens \"a\" a \"e\" da clausula 2) nos 3 primeiros meses"}],
        "regras_negocio": [{"assunto": "REPASSE", "texto": "Repasse nos dias 10 e 24.",
                            "evidencia": "nos dias 10 e 24 de cada mes"}],
        "acoes_sugeridas": [{"destino": "ORBE", "motivo": "Condição especial que a Orbe precisa aplicar.",
                             "assunto": "Cadastro de condições do lojista Aurora Intercambio",
                             "corpo": "Olá, equipe Orbe. Pedimos aplicar ao lojista Aurora Intercambio Ltda as taxas de "
                                      "débito 1,59%, crédito à vista 2,79% e antecipação 2,15%, com isenção de MDR de "
                                      "01/10/2026 a 31/12/2026. Podem confirmar o cadastro?"},
                            {"destino": "PONTE", "motivo": "Spread negociado.", "assunto": "Spread de remessa Aurora",
                             "corpo": "Olá, equipe Ponte. O spread negociado para o lojista é 1,35%. Podem aplicar?"}],
        "duvidas": [],
    }


def run(resp, texto=None, cliente=CLIENTE):
    texto = texto if texto is not None else CONTRATO.read_text(encoding="utf-8")
    return ic.extrair(texto, cliente, CTX, cliente_ia=Falso(resp))


# ---------------------------------------------------------------- ler_texto
def test_ler_texto_txt_utf8_e_cp1252():
    assert "AURORA" in ic.ler_texto(CONTRATO.read_bytes(), "c.txt")
    assert ic.ler_texto("Cláusula única de pagamento 2,5%".encode("cp1252"), "c.txt") == "Cláusula única de pagamento 2,5%"
    assert ic.ler_texto(str(CONTRATO)).startswith("*** DOCUMENTO FICTICIO")


def _docx(paragrafos):
    corpo = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{p}</w:t></w:r></w:p>" for p in paragrafos)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{corpo}</w:body></w:document>")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("word/document.xml", xml)
    return b.getvalue()


def test_ler_texto_docx():
    t = ic.ler_texto(_docx(["Cláusula 1 &amp; 2", "Taxa de débito: 1,59%"]), "contrato.docx")
    assert t == "Cláusula 1 & 2\nTaxa de débito: 1,59%"


def test_ler_texto_erros_legiveis_e_limite():
    with pytest.raises(ValueError, match="docx"):
        ic.ler_texto(b"nao sou zip", "x.docx")
    with pytest.raises(ValueError, match="PDF"):
        ic.ler_texto(b"%PDF-1.4 lixo", "x.pdf")
    with pytest.raises(ValueError, match="não suportado"):
        ic.ler_texto(b"abc", "x.exe")
    longo = ic.ler_texto(("abcdefghij " * 8000).encode(), "x.txt")
    assert "truncado" in longo and len(longo) < 60500


# ---------------------------------------------------------------- extração + guarda-corpos
def test_extracao_completa_passa_pelos_guarda_corpos():
    r = run(resposta_boa())
    assert r["erro"] == "" and r["ajustes"] == [] and r["duvidas"] == []
    assert {t["faixa"]: t["valor"] for t in r["taxas"]} == {
        "DEBITO": "1.59", "CREDITO A VISTA": "2.79", "PARC_2_6": "3.29", "PARC_7_12": "3.89", "PIX": "0.95",
        "ANTECIPACAO": "2.15", "SPREAD_REMESSA": "1.35"}
    assert r["partes"]["cnpj"] == "11222333000181" and r["vigencia_inicio"] == "2026-10-01"
    assert [a["destino"] for a in r["acoes_sugeridas"]] == ["ORBE", "PONTE"]
    assert r["versao_prompt"] == "contrato-v1" and r["modelo"] == "modelo-falso"
    assert r["aviso"].startswith("Extração da IA") and "aprovado_por" not in json.dumps(r)
    assert all("Helena — Financeiro Tarvo" in a["corpo"] for a in r["acoes_sugeridas"])


def test_evidencia_inexistente_remove_o_item():
    resp = resposta_boa()
    resp["taxas"][0]["evidencia"] = "Débito fica em 1,59% para sempre"
    resp["regras_negocio"][0]["evidencia"] = "repasse no quinto dia útil"
    r = run(resp)
    assert "DEBITO" not in {t["faixa"] for t in r["taxas"]} and r["regras_negocio"] == []
    assert sum("evidência não é um trecho literal" in a for a in r["ajustes"]) == 2


def test_evidencia_compara_sem_acento_caixa_e_espacos():
    resp = resposta_boa()
    resp["taxas"][0]["evidencia"] = "  DÉBITO:   1,59%  "
    r = run(resp)
    assert "DEBITO" in {t["faixa"] for t in r["taxas"]}


def test_valor_inventado_e_removido():
    resp = resposta_boa()
    resp["taxas"][1]["valor"] = "2.99"                     # o contrato diz 2,79
    resp["condicoes_especiais"][0]["valor"] = "7.77"
    r = run(resp)
    assert "CREDITO A VISTA" not in {t["faixa"] for t in r["taxas"]}
    assert r["condicoes_especiais"] == []
    assert any("2.99" in a for a in r["ajustes"]) and any("7.77" in a for a in r["ajustes"])


def test_faixa_tipo_assunto_e_destino_fora_do_enum():
    resp = resposta_boa()
    resp["taxas"].append(_tx("BOLETO", "0.95", "Pix: 0,95%"))
    resp["condicoes_especiais"].append({**resp["condicoes_especiais"][0], "tipo": "BRINDE"})
    resp["regras_negocio"].append({"assunto": "SEGREDO", "texto": "x", "evidencia": "nos dias 10 e 24 de cada mes"})
    resp["acoes_sugeridas"].append({"destino": "CONCORRENTE", "motivo": "m", "assunto": "a", "corpo": "c"})
    resp["acoes_sugeridas"].append({"destino": "FINANCEIRO_INTERNO", "motivo": "m", "assunto": "a", "corpo": "c"})
    r = run(resp)
    assert len(r["taxas"]) == 7 and len(r["condicoes_especiais"]) == 1 and len(r["regras_negocio"]) == 1
    assert [a["destino"] for a in r["acoes_sugeridas"]] == ["ORBE", "PONTE"]
    for trecho in ("BOLETO", "BRINDE", "SEGREDO", "CONCORRENTE", "FINANCEIRO_INTERNO"):
        assert any(trecho in a for a in r["ajustes"]), trecho


def test_email_com_valor_ou_promessa_invalidos_e_removido():
    resp = resposta_boa()
    resp["acoes_sugeridas"][0]["corpo"] = "Aplicar débito 1,59% e crédito 9,99% ao lojista."
    resp["acoes_sugeridas"][1]["corpo"] = "A Ponte pagará R$ 50.000,00 ao lojista pelo spread de 1,35%."
    resp["acoes_sugeridas"].append({"destino": "COMERCIAL", "motivo": "m", "assunto": "Cadastro",
                                    "corpo": "Vamos creditar o lojista pela diferença."})
    resp["acoes_sugeridas"].append({"destino": "COMERCIAL", "motivo": "m", "assunto": "Longo", "corpo": "x" * 1600})
    r = run(resp)
    assert r["acoes_sugeridas"] == []
    assert len([a for a in r["ajustes"] if a.startswith("ação para")]) == 4


def test_nao_contrato_devolve_duvidas_e_listas_vazias():
    r = run({**resposta_boa(), "duvidas": []}, texto="Receita de bolo: misture farinha, ovos e açúcar. Asse por quarenta minutos.")
    assert r["taxas"] == [] and r["condicoes_especiais"] == [] and r["regras_negocio"] == [] and r["acoes_sugeridas"] == []
    assert r["duvidas"] and "não parece conter taxas" in r["duvidas"][0]


def test_cnpj_diferente_vira_duvida_e_data_inventada_e_removida():
    resp = resposta_boa()
    resp["vigencia_fim"] = "2031-01-01"
    r = run(resp, cliente={**CLIENTE, "cnpj": "39566044000119"})
    assert r["vigencia_fim"] == "" and any("vigência final" in a for a in r["ajustes"])
    assert any("diferente do CNPJ do cliente" in d for d in r["duvidas"])


def test_erros_da_ia_nao_quebram():
    class Quebra:
        def gerar(self, s, m):
            raise RuntimeError("boom")
    r = ic.extrair(CONTRATO.read_text(encoding="utf-8"), CLIENTE, CTX, cliente_ia=Quebra())
    assert r["erro"].startswith("IA indisponível") and r["taxas"] == []
    assert ic.extrair("", CLIENTE, CTX, cliente_ia=Falso({}))["duvidas"]


def test_mensagem_ao_modelo_traz_o_contrato_e_o_cliente():
    f = Falso(resposta_boa())
    ic.extrair(CONTRATO.read_text(encoding="utf-8"), CLIENTE, CTX, cliente_ia=f)
    system, msg = f.chamadas[0]
    assert "contrato-v1" in system and "AURORA INTERCAMBIO" in msg and "11222333000181" in msg


# ---------------------------------------------------------------- para_cadastro
@pytest.fixture()
def ext():
    return run(resposta_boa())


def test_para_cadastro_exige_aprovado_por(ext, tmp_path):
    p = ic.para_cadastro(ext, CLIENTE, "", "helena", RAIZ / "cadastro")
    assert p["condicoes"] and any("aprovado_por" in e for e in p["erros"])


def test_para_cadastro_condicoes_corretas(ext):
    p = ic.para_cadastro(ext, CLIENTE, "Comercial (Rafael)", "helena", RAIZ / "cadastro")
    assert p["erros"] == []
    esp = {c["campo"]: c for c in p["condicoes"] if c["tipo"] == "TAXA_ESPECIAL"}
    assert set(esp) == set(cad.FAIXAS) and len(esp) == 7
    assert esp["SPREAD_REMESSA"]["linha_negocio"] == "REMESSA" and esp["SPREAD_REMESSA"]["valor"] == "1.35"
    assert esp["PIX"]["linha_negocio"] == "CHECKOUT" and esp["PIX"]["valor"] == "0.95"
    for c in esp.values():
        assert (c["vigencia_inicio"], c["vigencia_fim"]) == ("2026-10-01", "2028-09-30")
        assert c["fonte"] == "contrato contrato_ficticio_exemplo.txt" and c["aprovado_por"] == "Comercial (Rafael)"
        assert c["cnpj"] == "11222333000181"
    iso = [c for c in p["condicoes"] if c["tipo"] == "ISENCAO"]
    assert len(iso) == 1 and iso[0]["campo"] == "DEBITO,CREDITO A VISTA,PARC_2_6,PARC_7_12,PIX"
    assert (iso[0]["vigencia_inicio"], iso[0]["vigencia_fim"]) == ("2026-10-01", "2026-12-31")


def test_para_cadastro_nao_grava_e_grava_via_servidor(ext, tmp_path):
    import shutil
    pasta = tmp_path / "cad"
    shutil.copytree(RAIZ / "cadastro", pasta, ignore=shutil.ignore_patterns("contratos"))
    antes = (pasta / "condicoes_comerciais.csv").read_bytes()
    p = ic.para_cadastro(ext, CLIENTE, "Comercial", "helena", pasta)
    assert (pasta / "condicoes_comerciais.csv").read_bytes() == antes          # a proposta não grava
    gravadas = cad.adicionar_varias(pasta, p["condicoes"], "helena")
    assert len(gravadas) == 8


def test_para_cadastro_sem_vigencia_e_sem_taxa(tmp_path):
    ext = ic.validar({"taxas": [_tx("PIX", "0.95", "Pix: 0,95%")]}, CONTRATO.read_text(encoding="utf-8"))
    p = ic.para_cadastro(ext, CLIENTE, "Comercial", "helena", RAIZ / "cadastro")
    assert p["condicoes"] == [] and any("vigência inicial" in e for e in p["erros"])
    vazio = ic.para_cadastro(ic._resultado(), CLIENTE, "Comercial", "helena", RAIZ / "cadastro")
    assert vazio["erros"]


def test_padrao_brasileiro_nos_numeros_dos_textos():
    from src import ia_contrato as ic
    assert ic._padrao_br("Pix a 1.59% e débito 2,19%") == "Pix a 1,59% e débito 2,19%"
    assert ic._padrao_br("Total R$ 15396.77 e R$ 1.200,00") == "Total R$ 15.396,77 e R$ 1.200,00"
