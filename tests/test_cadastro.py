"""Cadastro de condições comerciais (src/cadastro.py) e seu uso no fechamento."""
import shutil
from datetime import date
from decimal import Decimal as D

import pytest

from src import cadastro, fechamento
from src.cadastro import CadastroAusente, CadastroInvalido

CASA = ("00520815000100", "1018325654")
ROTA_CNPJ = "95927868000148"
OFICIAIS = ["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv",
            "lancamentos_classificados.csv", "pendencias.csv", "rastro.csv"]


@pytest.fixture
def cad(tmp_path, raiz):
    """Cópia do cadastro oficial para o teste poder gravar."""
    destino = tmp_path / "cadastro"
    shutil.copytree(raiz / "cadastro", destino)
    return destino


def _especial(**kw):
    base = {"tipo": "TAXA_ESPECIAL", "cnpj": ROTA_CNPJ, "lojista": "Rota Global", "linha_negocio": "CHECKOUT",
            "campo": "DEBITO", "valor": "1.00", "vigencia_inicio": "2026-09-01", "aprovado_por": "Comercial",
            "fonte": "teste"}
    base.update(kw)
    return base


# ---------------------------------------------------------------- ler / validar
def test_cadastro_inicial_tem_as_seis_condicoes_migradas(raiz):
    cs = cadastro.ler(raiz / "cadastro")
    assert [c["id_condicao"] for c in cs] == ["C001", "C002", "C003", "C004", "C005", "C006"]
    assert [c["tipo"] for c in cs] == ["ISENCAO", "DE_PARA_EC", "DE_PARA_EC", "DE_PARA_EC",
                                       "BLOQUEIO_FATURAMENTO", "NOTA_PENDENCIA"]
    c1 = cs[0]
    assert (c1["cnpj"], c1["ec_orbe"], c1["campo"], c1["aprovado_por"]) == (*CASA, "todas", "Comercial")
    assert (c1["vigencia_inicio"], c1["vigencia_fim"]) == ("2026-09-01", "2026-12-31")
    assert cs[4]["observacao"].startswith("Atlas Idiomas: sem contrato")      # texto com ';' sobrevive às aspas


def test_ler_pasta_inexistente(tmp_path):
    with pytest.raises(CadastroAusente):
        cadastro.ler(tmp_path / "nao_existe")


@pytest.mark.parametrize("troca,trecho", [
    (("id_condicao;tipo", "id;tipo"), "cabeçalho"),
    (("ISENCAO", "DESCONTO"), "tipo 'DESCONTO' inválido"),
    (("2026-09-01;2026-12-31", "01/09/2026;2026-12-31"), "data '01/09/2026' inválida"),
    (("2026-09-01;2026-12-31", "2026-09-01;2026-08-31"), "termina"),
    (("todas", "ouro"), "faixa 'OURO' desconhecida"),
    (("Comercial;2026-10-17;S07/S47", ";2026-10-17;S07/S47"), "exige aprovado_por"),
    (("C002;DE_PARA_EC", "C001;DE_PARA_EC"), "repetido"),
])
def test_ler_malformado_da_erro_legivel(cad, troca, trecho):
    arq = cad / cadastro.ARQ_CONDICOES
    arq.write_text(arq.read_text(encoding="utf-8").replace(*troca, 1), encoding="utf-8")
    with pytest.raises(CadastroInvalido) as e:
        cadastro.ler(cad)
    assert trecho in str(e.value)
    assert isinstance(e.value, ValueError)


def test_ler_linha_com_colunas_a_mais(cad):
    arq = cad / cadastro.ARQ_CONDICOES
    arq.write_text(arq.read_text(encoding="utf-8") + "C099;ISENCAO;a;b\n", encoding="utf-8")
    with pytest.raises(CadastroInvalido, match="linha 8: 4 colunas"):
        cadastro.ler(cad)


# ---------------------------------------------------------------- vigentes
def test_vigentes_por_data_lojista_linha_e_tipo(raiz):
    cs = cadastro.ler(raiz / "cadastro")
    ids = lambda xs: [c["id_condicao"] for c in xs]
    assert ids(cadastro.vigentes(cs, date(2026, 9, 15), tipo="ISENCAO")) == ["C001"]
    assert cadastro.vigentes(cs, date(2026, 8, 31), tipo="ISENCAO") == []          # antes do início
    assert cadastro.vigentes(cs, date(2027, 1, 1), tipo="ISENCAO") == []           # depois do fim
    assert ids(cadastro.vigentes(cs, date(2026, 12, 31), tipo="ISENCAO")) == ["C001"]   # fim inclusivo
    assert ids(cadastro.vigentes(cs, date(2026, 9, 15), cnpj=CASA[0])) == ["C001"]
    assert ids(cadastro.vigentes(cs, date(2026, 9, 15), ec=CASA[1])) == ["C001"]
    assert ids(cadastro.vigentes(cs, date(2026, 9, 15), ec="1076801732")) == ["C005"]
    assert ids(cadastro.vigentes(cs, date(2026, 9, 15), linha="REMESSA")) == ["C006"]
    assert ids(cadastro.vigentes(cs, date(2026, 9, 15), cnpj="17217888000111", linha="CHECKOUT")) == []
    assert len(cadastro.vigentes(cs, date(2026, 9, 15))) == 6
    assert cadastro.vigentes(None, date(2026, 9, 15)) == []


# ---------------------------------------------------------------- adicionar / encerrar / histórico
def test_adicionar_gera_id_grava_e_registra_historico(cad):
    c = cadastro.adicionar(cad, _especial(), "ana", hoje=date(2026, 10, 20))
    assert c["id_condicao"] == "C007" and c["data_registro"] == "2026-10-20"
    assert cadastro.ler(cad)[-1]["id_condicao"] == "C007"
    h = cadastro.ler_historico(cad)
    assert h[-1]["acao"] == "CRIAR" and h[-1]["usuario"] == "ana" and h[-1]["id_condicao"] == "C007"
    assert "1.00%" in h[-1]["resumo"]
    assert len(h) == 7 and h[0]["id_condicao"] == "C001"            # migração já estava no histórico


def test_adicionar_cria_cadastro_na_primeira_vez(tmp_path):
    c = cadastro.adicionar(tmp_path / "novo", _especial(), "ana")
    assert c["id_condicao"] == "C001"
    assert (tmp_path / "novo" / cadastro.ARQ_HISTORICO).exists()


@pytest.mark.parametrize("campo,valor,trecho", [
    ("aprovado_por", "", "exige aprovado_por"),
    ("valor", "abc", "valor 'abc' inválido"),
    ("valor", "120", "fora do intervalo"),
    ("campo", "DEBITO,PIX", "UMA faixa"),
    ("campo", "todas", "só vale para ISENCAO"),
    ("campo", "SPREAD_REMESSA", "não pertence à linha"),
    ("cnpj", "", "CNPJ ou o EC"),
    ("vigencia_inicio", "", "vigência inicial é obrigatória"),
])
def test_adicionar_taxa_especial_valida_campos(cad, campo, valor, trecho):
    antes = (cad / cadastro.ARQ_CONDICOES).read_bytes()
    with pytest.raises(CadastroInvalido, match=trecho):
        cadastro.adicionar(cad, _especial(**{campo: valor}), "ana")
    assert (cad / cadastro.ARQ_CONDICOES).read_bytes() == antes     # nada gravado


def test_adicionar_isencao_exige_aprovador_e_outros_tipos_exigem_seus_campos(cad):
    with pytest.raises(CadastroInvalido, match="exige aprovado_por"):
        cadastro.adicionar(cad, {"tipo": "ISENCAO", "cnpj": ROTA_CNPJ, "linha_negocio": "CHECKOUT", "campo": "todas",
                                 "vigencia_inicio": "2026-10-01"}, "ana")
    with pytest.raises(CadastroInvalido, match="DE_PARA_EC exige"):
        cadastro.adicionar(cad, {"tipo": "DE_PARA_EC", "ec_orbe": "123", "linha_negocio": "CHECKOUT",
                                 "vigencia_inicio": "2026-10-01"}, "ana")
    with pytest.raises(CadastroInvalido, match="motivo"):
        cadastro.adicionar(cad, {"tipo": "BLOQUEIO_FATURAMENTO", "ec_orbe": "123", "linha_negocio": "CHECKOUT",
                                 "vigencia_inicio": "2026-10-01"}, "ana")
    with pytest.raises(CadastroInvalido, match="quem está registrando"):
        cadastro.adicionar(cad, _especial(), " ")
    ok = cadastro.adicionar(cad, {"tipo": "ISENCAO", "cnpj": "95.927.868/0001-48", "linha_negocio": "CHECKOUT",
                                  "campo": "pix, debito", "vigencia_inicio": "2026-10-01", "aprovado_por": "Comercial"},
                            "ana")
    assert ok["cnpj"] == ROTA_CNPJ and ok["campo"] == "PIX,DEBITO"


def test_adicionar_recusa_taxa_especial_sobreposta(cad):
    cadastro.adicionar(cad, _especial(), "ana")
    with pytest.raises(CadastroInvalido, match="C007"):
        cadastro.adicionar(cad, _especial(valor="1.50", vigencia_inicio="2026-09-15"), "ana")
    cadastro.adicionar(cad, _especial(campo="PIX"), "ana")                     # outra faixa: pode


def test_encerrar_preenche_fim_nao_apaga_e_registra(cad):
    cadastro.adicionar(cad, _especial(), "ana")
    c = cadastro.encerrar(cad, "C007", "2026-09-30", "bia")
    assert c["vigencia_fim"] == "2026-09-30"
    cs = cadastro.ler(cad)
    assert len(cs) == 7 and cs[-1]["vigencia_fim"] == "2026-09-30"
    h = cadastro.ler_historico(cad)[-1]
    assert (h["acao"], h["usuario"], h["id_condicao"]) == ("ENCERRAR", "bia", "C007")
    assert cadastro.vigentes(cs, date(2026, 10, 1), tipo="TAXA_ESPECIAL") == []
    with pytest.raises(CadastroInvalido, match="só é possível antecipar"):
        cadastro.encerrar(cad, "C007", "2026-10-30", "bia")
    with pytest.raises(CadastroInvalido, match="não encontrada"):
        cadastro.encerrar(cad, "C999", "2026-10-30", "bia")
    with pytest.raises(CadastroInvalido, match="anterior ao início"):
        cadastro.encerrar(cad, "C006", date(2025, 1, 1), "bia")


# ---------------------------------------------------------------- taxa_efetiva
def _planilha_linha(resultado, cnpj, ec=None):
    return next(c for c in resultado["dados"]["contratos"] if c["cnpj"] == cnpj and not c["riscado"])


def test_taxa_efetiva_planilha_isencao_e_taxa_especial(resultado, cad):
    cs = resultado["condicoes"]
    casa = _planilha_linha(resultado, CASA[0])
    v, origem = cadastro.taxa_efetiva(casa, cs, date(2026, 9, 10), "DEBITO")
    assert v == 0 and origem == "cadastro C001 (ISENCAO, aprovado por Comercial)"
    v, origem = cadastro.taxa_efetiva(casa, cs, date(2026, 8, 31), "DEBITO")
    assert v == casa["taxas"]["DEBITO"] and origem == f"planilha linha {casa['linha']}"
    rota = _planilha_linha(resultado, ROTA_CNPJ)
    assert cadastro.taxa_efetiva(rota, cs, date(2026, 9, 10), "DEBITO")[0] == rota["taxas"]["DEBITO"]
    cadastro.adicionar(cad, _especial(valor="2.19", vigencia_inicio="2026-09-15"), "ana")
    cs2 = cadastro.ler(cad)
    assert cadastro.taxa_efetiva(rota, cs2, date(2026, 9, 14), "DEBITO")[1].startswith("planilha")
    v, origem = cadastro.taxa_efetiva(rota, cs2, date(2026, 9, 15), "DEBITO")
    assert v == D("2.19") and origem == "cadastro C007 (TAXA_ESPECIAL, aprovado por Comercial)"
    assert cadastro.taxa_efetiva(rota, cs2, date(2026, 9, 15), "PIX")[0] == rota["taxas"]["PIX"]   # outra faixa intacta


def test_taxa_efetiva_spread_remessa(resultado, cad):
    rota = _planilha_linha(resultado, ROTA_CNPJ)
    cadastro.adicionar(cad, _especial(linha_negocio="REMESSA", campo="SPREAD_REMESSA", valor="1.20"), "ana")
    v, origem = cadastro.taxa_efetiva(rota, cadastro.ler(cad), date(2026, 9, 10), "SPREAD_REMESSA")
    assert v == D("0.012") and origem.startswith("cadastro C007")


# ---------------------------------------------------------------- uso no fechamento
def _por_cnpj(r, cnpj, linha="CHECKOUT"):
    return next(c for c in r["comissoes"] if c["cnpj"] == cnpj and c["linha_negocio"] == linha)


def test_taxa_especial_nova_muda_a_comissao(raiz, cad, tmp_path, resultado):
    base = _por_cnpj(resultado, ROTA_CNPJ)
    cadastro.adicionar(cad, _especial(campo="CREDITO A VISTA", valor="9.99", fonte="aditivo teste"), "ana")
    r = fechamento.executar(raiz, tmp_path / "s", investigar=False, cadastro=cad)
    novo = _por_cnpj(r, ROTA_CNPJ)
    assert novo["comissao"] != base["comissao"]
    linhas = [l for l in r["checkout"] if l["status"] == "FATURAVEL" and l["cnpj"] == ROTA_CNPJ
              and l["modalidade"] == "CREDITO A VISTA" and l["tipo"] == "VENDA"]
    assert linhas and all(l["contratada"] == D("9.99") and "cadastro C007" in l["regra"] for l in linhas)
    # só a faixa pedida mudou
    deb = [l for l in r["checkout"] if l["status"] == "FATURAVEL" and l["cnpj"] == ROTA_CNPJ and l["modalidade"] == "DEBITO"]
    assert deb and all("cadastro" not in l["regra"] for l in deb)
    # taxa especial é condição contratual: a diferença para a Orbe vira divergência de CONTRATO, não isenção
    assert {l["natureza"] for l in r["checkout"] if l.get("cnpj") == ROTA_CNPJ and l["status"] == "FATURAVEL"} == {"CONTRATO"}


def test_isencao_encerrada_no_cadastro_volta_a_cobrar_a_planilha(raiz, cad, tmp_path, resultado):
    cadastro.encerrar(cad, "C001", "2026-09-14", "ana")
    r = fechamento.executar(raiz, tmp_path / "s", investigar=False, cadastro=cad)
    casa = [l for l in r["checkout"] if l["status"] == "FATURAVEL" and l["cnpj"] == CASA[0]]
    depois = [l for l in casa if l["data"] >= date(2026, 9, 15) and l["tipo"] in ("VENDA", "ANTECIPACAO")]
    assert depois and all("R52" not in l["regra"] and l["contratada"] > 0 for l in depois)
    antes = [l for l in casa if l["data"] <= date(2026, 9, 14) and l["tipo"] in ("VENDA", "ANTECIPACAO")]
    assert antes and all(l["contratada"] == 0 and "R52 isenção CC01" in l["regra"] for l in antes)
    assert _por_cnpj(r, CASA[0])["comissao"] > _por_cnpj(resultado, CASA[0])["comissao"]


def test_cadastro_ausente_vira_pendencia_e_nao_quebra(raiz, tmp_path, resultado):
    r = fechamento.executar(raiz, tmp_path / "s", investigar=False, cadastro=tmp_path / "nao_existe")
    p = [x for x in r["pendencias"] if x["tipo"] == "CADASTRO_AUSENTE"]
    assert len(p) == 1 and p[0]["valor"] == 0 and "notas e comissões podem estar erradas" in p[0]["motivo"]
    assert r["cadastro_ausente"] is True and r["condicoes"] == [] and r["parcial"] is True
    assert "FECHAMENTO PARCIAL" in fechamento.resumo(r) and "cadastro de condições comerciais" in r["aviso_parcial"]
    import csv as _csv
    for nome in ("comissoes_por_lojista.csv", "notas_a_emitir.csv"):
        with open(tmp_path / "s" / nome, encoding="utf-8", newline="") as f:
            linhas = list(_csv.DictReader(f, delimiter=";"))
        assert linhas and {l["status"] for l in linhas} == {"PROVISORIO"}, nome
    assert not resultado["parcial"]
    assert not any(x["tipo"] == "CADASTRO_AUSENTE" for x in resultado["pendencias"])
    # sem as condições: Casa deixa de ser isenta e Atlas deixa de ser bloqueada (cai em taxa indefinida)
    assert not any(x["tipo"] == "DEVOLUCAO_LOJISTA_ISENCAO" for x in r["pendencias"])
    assert any(x["tipo"] == "TAXA_CONTRATADA_INDEFINIDA" for x in r["pendencias"])
    assert (tmp_path / "s" / "pendencias.csv").exists()


def test_cadastro_malformado_interrompe_com_mensagem(raiz, cad, tmp_path):
    (cad / cadastro.ARQ_CONDICOES).write_text("lixo\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cabeçalho"):
        fechamento.executar(raiz, tmp_path / "s", investigar=False, cadastro=cad)


def test_cli_aceita_cadastro(raiz, tmp_path, capsys, cad):
    fechamento.main(["--saida", str(tmp_path / "s"), "--cadastro", str(tmp_path / "nao_existe")])
    assert "Pendências" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        (cad / cadastro.ARQ_CONDICOES).write_text("lixo\n", encoding="utf-8")
        fechamento.main(["--saida", str(tmp_path / "s2"), "--cadastro", str(cad)])


def test_fechamento_completo_com_cadastro_oficial_identico_a_saida(raiz, tmp_path):
    """A banca compara os 6 CSVs oficiais byte a byte: migrar as condições para o cadastro não pode mudar nada."""
    fechamento.executar(raiz, tmp_path / "s")
    for nome in OFICIAIS:
        assert (tmp_path / "s" / nome).read_bytes() == (raiz / "saida" / nome).read_bytes(), nome
    assert (tmp_path / "s" / "investigacao" / "dossie.md").read_bytes() == \
        (raiz / "saida" / "investigacao" / "dossie.md").read_bytes()


# ---------------------------------------------------------------- auditoria: arquivo truncado, sobreposição, lote
def test_ler_detecta_cadastro_truncado_pelo_historico(cad):
    arq = cad / cadastro.ARQ_CONDICOES
    linhas = arq.read_text(encoding="utf-8").splitlines(keepends=True)
    arq.write_text("".join(linhas[:2]), encoding="utf-8")            # cabeçalho + C001
    with pytest.raises(CadastroInvalido, match=r"parece incompleto: faltam C002, C003, C004, C005, C006"):
        cadastro.ler(cad)
    (cad / cadastro.ARQ_HISTORICO).unlink()                          # sem histórico: sem a checagem
    assert [c["id_condicao"] for c in cadastro.ler(cad)] == ["C001"]


def test_adicionar_recusa_isencao_sobreposta_mas_aceita_outra_faixa_ou_periodo(cad):
    base = {"tipo": "ISENCAO", "cnpj": ROTA_CNPJ, "linha_negocio": "CHECKOUT", "campo": "PIX,DEBITO",
            "vigencia_inicio": "2026-10-01", "vigencia_fim": "2026-10-31", "aprovado_por": "Comercial"}
    cadastro.adicionar(cad, base, "ana")
    with pytest.raises(CadastroInvalido, match="C007"):
        cadastro.adicionar(cad, dict(base, campo="todas", vigencia_inicio="2026-10-15", vigencia_fim=""), "ana")
    with pytest.raises(CadastroInvalido, match="C007"):
        cadastro.adicionar(cad, dict(base, campo="DEBITO", vigencia_inicio="2026-10-31"), "ana")
    cadastro.adicionar(cad, dict(base, campo="ANTECIPACAO"), "ana")                  # faixa que não cruza
    cadastro.adicionar(cad, dict(base, vigencia_inicio="2026-11-01", vigencia_fim=""), "ana")   # período que não cruza
    with pytest.raises(CadastroInvalido, match="C001"):                  # Casa já tem isenção "todas" até 31/12
        cadastro.adicionar(cad, dict(base, cnpj=CASA[0], campo="PIX"), "ana")


def test_adicionar_recusa_ec_de_outro_cnpj(cad, resultado):
    with pytest.raises(CadastroInvalido, match="já está ligado ao CNPJ 00520815000100"):
        cadastro.adicionar(cad, _especial(ec_orbe=CASA[1]), "ana")                    # EC da Casa com CNPJ da Rota (cadastro)
    contratos = resultado["dados"]["contratos"]
    rota_ec = next(c["ec"] for c in contratos if c["cnpj"] == ROTA_CNPJ and c["ec"])
    with pytest.raises(CadastroInvalido, match=f"EC Orbe {rota_ec}"):
        cadastro.adicionar(cad, _especial(cnpj=CASA[0], ec_orbe=rota_ec), "ana", contratos=contratos)   # planilha
    ok = cadastro.adicionar(cad, _especial(ec_orbe=rota_ec), "ana", contratos=contratos)
    assert ok["ec_orbe"] == rota_ec


def test_adicionar_varias_e_atomico(cad):
    antes = (cad / cadastro.ARQ_CONDICOES).read_bytes(), (cad / cadastro.ARQ_HISTORICO).read_bytes()
    lote = [_especial(campo="DEBITO"), _especial(campo="PIX", valor="0.99"), _especial(campo="DEBITO", valor="3")]
    with pytest.raises(CadastroInvalido, match="Condição nova 3 de 3.*C007"):      # 3ª colide com a 1ª do próprio lote
        cadastro.adicionar_varias(cad, lote, "ana")
    assert ((cad / cadastro.ARQ_CONDICOES).read_bytes(), (cad / cadastro.ARQ_HISTORICO).read_bytes()) == antes
    with pytest.raises(CadastroInvalido, match="Condição nova 2 de 2"):
        cadastro.adicionar_varias(cad, [_especial(), _especial(campo="PIX", valor="x")], "ana")
    assert (cad / cadastro.ARQ_CONDICOES).read_bytes() == antes[0]
    gravadas = cadastro.adicionar_varias(cad, lote[:2], "ana")
    assert [c["id_condicao"] for c in gravadas] == ["C007", "C008"]
    assert len(cadastro.ler(cad)) == 8 and [h["id_condicao"] for h in cadastro.ler_historico(cad)][-2:] == ["C007", "C008"]
    assert cadastro.adicionar_varias(cad, [], "ana") == []


# ---------------------------------------------------------------- validar (dry-run)
def test_validar_dry_run_nao_grava(cad):
    antes = (cad / "condicoes_comerciais.csv").read_bytes(), cadastro.ler_historico(cad)
    assert cadastro.validar(_especial(), cad) == []
    assert cadastro.validar([_especial(), _especial(campo="PIX")], cad) == []
    assert (cad / "condicoes_comerciais.csv").read_bytes() == antes[0] and cadastro.ler_historico(cad) == antes[1]


def test_validar_devolve_os_mesmos_erros_de_adicionar(cad):
    for ruim, trecho in [(_especial(aprovado_por=""), "aprovado_por"), (_especial(campo="XYZ"), "faixa"),
                         (_especial(valor="abc"), "inválido"), (_especial(cnpj="123"), "14 dígitos")]:
        erros = cadastro.validar(ruim, cad)
        assert len(erros) == 1 and trecho in erros[0]
        with pytest.raises(CadastroInvalido) as e:
            cadastro.adicionar(cad, ruim, "ana")
        assert str(e.value) == erros[0]


def test_validar_conflito_com_cadastro_e_entre_condicoes_da_lista(cad):
    n = len(cadastro.ler(cad))
    cadastro.adicionar(cad, _especial(), "ana")
    erros = cadastro.validar(_especial(valor="2.00"), cad)
    assert len(erros) == 1 and "Já existe a condição" in erros[0]
    lista = cadastro.validar([_especial(campo="PIX"), _especial(campo="PIX", valor="3.00"), _especial(aprovado_por="")], cad)
    assert len(lista) == 2 and "Condição nova 2 de 3" in lista[0] and "Condição nova 3 de 3" in lista[1]
    assert len(cadastro.ler(cad)) == n + 1
