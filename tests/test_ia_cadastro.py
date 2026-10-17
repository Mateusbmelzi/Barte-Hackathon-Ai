"""Testes do assistente de cadastro por IA (PLANO_03), sem rede: cliente falso e cadastro em pasta temporária."""
import copy
from decimal import Decimal

import pytest

from src import cadastro, ia, ia_cadastro

LOJA = {"lojista": "Loja Modelo Ltda", "cnpj": "11111111000111", "ec": "1000000001", "linha": 5,
        "taxas": {"DEBITO": Decimal("1.5"), "CREDITO A VISTA": Decimal("2.99"), "PARC_2_6": Decimal("3.5"),
                  "PARC_7_12": Decimal("4.5"), "PIX": Decimal("0.99"), "ANTECIPACAO": Decimal("1.2")},
        "spread": Decimal("0.015")}
OUTRA = {"lojista": "Escola Horizonte Idiomas Ltda", "cnpj": "22222222000122", "ec": "1000000002", "linha": 6,
         "taxas": {}, "spread": None}
OUTRA2 = {"lojista": "Horizonte Viagens", "cnpj": "33333333000133", "ec": "1000000003", "linha": 7,
          "taxas": {}, "spread": None}
LOJISTAS = [LOJA, OUTRA, OUTRA2]
TEXTO = "A Loja Modelo passa a pagar 2,79% no crédito à vista a partir de 01/10/2026, aprovado pelo Comercial."


def cond(**kw):
    base = {"tipo": "TAXA_ESPECIAL", "cnpj": "11111111000111", "ec_orbe": "1000000001",
            "lojista": "Loja Modelo Ltda", "linha_negocio": "CHECKOUT", "campo": "CREDITO A VISTA",
            "valor": "2.79", "vigencia_inicio": "2026-10-01", "vigencia_fim": "", "aprovado_por": "Comercial",
            "fonte": "", "observacao": ""}
    base.update(kw)
    return base


class ClienteFalso:
    provedor = "falso"
    modelo = "claude-sonnet-5-5"

    def __init__(self, condicoes=None, resumo="Taxa especial.", duvidas="", erro=None):
        self.resposta = {"condicoes": condicoes if condicoes is not None else [cond()],
                         "resumo": resumo, "duvidas": duvidas}
        self.erro, self.chamadas = erro, []

    def gerar(self, system, mensagem):
        self.chamadas.append(mensagem)
        if self.erro:
            raise self.erro
        return copy.deepcopy(self.resposta), "claude-sonnet-5-5"


def propor(cliente, texto=TEXTO, vigentes=(), lojistas=LOJISTAS, **kw):
    return ia_cadastro.propor(texto, lojistas, list(vigentes), "cadastro_inexistente", cliente=cliente, **kw)


def test_proposta_valida_com_antes_e_depois():
    r = propor(ClienteFalso())
    assert r["erro"] is None and r["duvidas"] == "" and r["erros"] == []
    assert len(r["condicoes"]) == 1
    c = r["condicoes"][0]
    assert c["tipo"] == "TAXA_ESPECIAL" and c["campo"] == "CREDITO A VISTA" and c["valor"] == "2.79"
    assert c["vigencia_inicio"] == "2026-10-01" and c["aprovado_por"] == "Comercial"
    assert c["cnpj"] == "11111111000111" and c["ec_orbe"] == "1000000001"
    assert len(r["antes_depois"]) == 1
    linha = r["antes_depois"][0]
    assert (linha["faixa"], linha["antes"], linha["depois"]) == ("Crédito à vista", "2,99%", "2,79%")
    assert "TAXA_ESPECIAL" in linha["origem"]
    assert r["aviso"].startswith("Proposta da IA")


def test_isencao_todas_lista_todas_as_faixas_com_antes_da_planilha():
    texto = "Loja Modelo isenta de taxa em todo o checkout de 01/10/2026 a 31/12/2026, aprovado pelo Comercial."
    c = cond(tipo="ISENCAO", campo="todas", valor="", vigencia_fim="2026-12-31")
    r = propor(ClienteFalso([c]), texto)
    assert r["erros"] == [] and len(r["antes_depois"]) == 6
    deb = next(l for l in r["antes_depois"] if l["faixa_codigo"] == "DEBITO")
    assert deb["antes"] == "1,50%" and deb["depois"] == "0,00%"


def test_antes_considera_condicao_vigente_existente():
    existente = {**{k: "" for k in cadastro.COLUNAS}, "id_condicao": "C001", "tipo": "TAXA_ESPECIAL",
                 "cnpj": "11111111000111", "ec_orbe": "1000000001", "linha_negocio": "CHECKOUT",
                 "campo": "CREDITO A VISTA", "valor": "2.50", "vigencia_inicio": "2026-01-01",
                 "vigencia_fim": "2026-09-30", "aprovado_por": "Comercial"}
    r = propor(ClienteFalso(), vigentes=[existente])
    assert r["antes_depois"][0]["antes"] == "2,99%"   # a existente já terminou antes de 01/10
    existente["vigencia_fim"] = ""
    r = propor(ClienteFalso(), vigentes=[existente])
    assert r["antes_depois"][0]["antes"] == "2,50%"


def test_sem_aprovador_vira_duvida_sem_condicao():
    texto = "A Loja Modelo passa a pagar 2,79% no crédito à vista a partir de 01/10/2026."
    r = propor(ClienteFalso([cond(aprovado_por="")]), texto)
    assert r["condicoes"] == [] and "aprovou" in r["duvidas"]
    # aprovador inventado pela IA que não está no texto também é recusado
    r = propor(ClienteFalso([cond(aprovado_por="Diretoria")]), texto)
    assert r["condicoes"] == [] and "aprovou" in r["duvidas"]


def test_lojista_inexistente_vira_duvida():
    r = propor(ClienteFalso([cond(cnpj="99999999000199", ec_orbe="", lojista="Fantasma")]))
    assert r["condicoes"] == [] and "lojista" in r["duvidas"].lower()


def test_lojista_ambiguo_a_ia_devolve_duvida_e_nenhuma_condicao():
    r = propor(ClienteFalso([cond()], duvidas="Há dois lojistas Horizonte; qual deles?"),
               "Horizonte passa a pagar 2,79% no crédito à vista a partir de 01/10/2026, aprovado pelo Comercial.")
    assert r["condicoes"] == [] and "Horizonte" in r["duvidas"]


def test_lojista_que_nao_esta_no_texto_vira_duvida():
    r = propor(ClienteFalso([cond(cnpj="22222222000122", ec_orbe="1000000002")]))  # texto fala da Loja Modelo
    assert r["condicoes"] == [] and "confirmar" in r["duvidas"]


def test_taxa_ou_data_inventada_vira_duvida():
    r = propor(ClienteFalso([cond(valor="1.99")]))
    assert r["condicoes"] == [] and "taxa" in r["duvidas"].lower()
    r = propor(ClienteFalso([cond(vigencia_inicio="2026-11-15")]))
    assert r["condicoes"] == [] and "data" in r["duvidas"].lower()


def test_tipo_nao_permitido():
    r = propor(ClienteFalso([cond(tipo="APAGAR_TUDO")]))
    assert r["condicoes"] == [] and "não permitido" in r["duvidas"]


def test_erros_da_validacao_do_cadastro_sao_devolvidos(monkeypatch):
    def validar(condicao, pasta, contratos=None, hoje=None):
        return ["Condição nova: já existe a condição C009 em período que se sobrepõe."]
    monkeypatch.setattr(cadastro, "validar", validar)
    r = propor(ClienteFalso())
    assert r["erros"] and "C009" in r["erros"][0] and r["antes_depois"] == []


def test_conflito_real_com_o_cadastro_gravado(tmp_path):
    cadastro.adicionar(tmp_path, cond(id_condicao="", vigencia_inicio="2026-09-01"), "teste")
    r = ia_cadastro.propor(TEXTO, LOJISTAS, cadastro.ler(tmp_path), tmp_path, cliente=ClienteFalso())
    assert r["erros"] and "sobrepõe" in r["erros"][0]
    assert len(cadastro.ler(tmp_path)) == 1  # a proposta não gravou nada


def test_faixa_invalida_cai_na_validacao():
    r = propor(ClienteFalso([cond(campo="CREDITO")]))
    assert r["erros"] and "faixa" in r["erros"][0]


def test_data_em_extenso_e_dd_mm():
    texto = "Loja Modelo: 2,79% no crédito à vista a partir de 1º de outubro de 2026, aprovado pelo Comercial."
    assert propor(ClienteFalso(), texto)["condicoes"]
    texto = "Loja Modelo: 2,79% no crédito à vista a partir de 1/10, aprovado pelo Comercial."
    assert propor(ClienteFalso(), texto)["condicoes"]


def test_bloqueio_nota_e_de_para_sem_aprovador():
    t = "Bloquear faturamento da Loja Modelo a partir de 01/10/2026 até confirmar o contrato."
    r = propor(ClienteFalso([cond(tipo="BLOQUEIO_FATURAMENTO", campo="", valor="", aprovado_por="",
                                  observacao="Contrato não confirmado")]), t)
    assert r["erros"] == [] and r["condicoes"][0]["tipo"] == "BLOQUEIO_FATURAMENTO" and r["antes_depois"] == []
    t = "O EC 1000000999 é da Loja Modelo, vale desde 01/10/2026."
    r = propor(ClienteFalso([cond(tipo="DE_PARA_EC", ec_orbe="1000000999", campo="", valor="", aprovado_por="")]), t)
    assert r["condicoes"][0]["ec_orbe"] == "1000000999"
    r = propor(ClienteFalso([cond(tipo="DE_PARA_EC", ec_orbe="1000000888", campo="", valor="", aprovado_por="")]), t)
    assert r["condicoes"] == [] and "EC" in r["duvidas"]


def test_texto_vazio_erro_do_cliente_e_sem_chave(monkeypatch, tmp_path):
    assert propor(ClienteFalso(), "  ")["duvidas"]
    r = propor(ClienteFalso(erro=ia.ErroIA("limite de uso atingido.")))
    assert "limite de uso atingido" in r["erro"] and r["condicoes"] == []
    for v in ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(ia, "RAIZ", tmp_path)
    r = ia_cadastro.propor(TEXTO, LOJISTAS, [], tmp_path)
    assert r["erro"] and r["condicoes"] == []


def test_nunca_grava(tmp_path):
    (tmp_path / "x").mkdir()
    antes = sorted(p.name for p in tmp_path.rglob("*"))
    ia_cadastro.propor(TEXTO, LOJISTAS, [], tmp_path, cliente=ClienteFalso())
    assert sorted(p.name for p in tmp_path.rglob("*")) == antes


def test_mensagem_so_leva_lojistas_e_condicoes_resumidas():
    c = ClienteFalso()
    propor(c)
    msg = c.chamadas[0]
    assert "11111111000111" in msg and '"taxas"' not in msg and '"spread"' not in msg


def test_schema_e_prompt():
    s = ia_cadastro.SCHEMA_SAIDA
    assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])
    item = s["properties"]["condicoes"]["items"]
    assert item["properties"]["tipo"]["enum"] == ["ISENCAO", "TAXA_ESPECIAL", "BLOQUEIO_FATURAMENTO",
                                                   "DE_PARA_EC", "NOTA_PENDENCIA"]
    assert set(item["required"]) == set(item["properties"])
    texto = ia_cadastro.montar_system().split("---", 1)[1]
    for termo in ["Rota", "Bridge", "Casa do Estudante", "Mundo Aberto", "12/09", "2,79"]:
        assert termo not in texto, termo
    assert ia_cadastro.versao_prompt().startswith("cadastro-v")
    for f in cadastro.FAIXAS:
        assert f in texto
