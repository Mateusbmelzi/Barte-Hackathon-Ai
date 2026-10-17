"""Contatos (src/contatos.py): CRUD, validação de e-mail e conteúdo do cadastro/contatos.csv entregue."""
import pytest

from src import checkout, config, contatos
from src.contatos import ContatoInvalido


@pytest.fixture
def pasta(tmp_path):
    return tmp_path / "cadastro"


def _novo(**kw):
    base = {"papel": "LOJISTA", "cnpj": "12.345.678/0001-95", "nome": "Fulano", "email": "fulano@x.exemplo.com.br"}
    base.update(kw)
    return base


def test_ler_sem_arquivo_e_adicionar(pasta):
    assert contatos.ler(pasta) == [] and contatos.para("ORBE", pasta=pasta) == []
    c = contatos.adicionar(pasta, _novo(), "ana")
    assert c["id_contato"] == "K001" and c["cnpj"] == "12345678000195"
    assert contatos.adicionar(pasta, _novo(cnpj="", papel="ORBE", email="o@orbe.exemplo.com.br"), "ana")["id_contato"] == "K002"
    assert [x["id_contato"] for x in contatos.ler(pasta)] == ["K001", "K002"]
    assert next((pasta / "contatos.csv").open(encoding="utf-8")).strip() == "id_contato;papel;cnpj;nome;email;observacao"


def test_para(pasta):
    contatos.adicionar(pasta, _novo(), "ana")
    contatos.adicionar(pasta, _novo(cnpj="98765432000110", nome="Outro", email="o@y.exemplo.com.br"), "ana")
    contatos.adicionar(pasta, _novo(papel="PONTE", cnpj="", email="p@ponte.exemplo.com.br"), "ana")
    assert [c["nome"] for c in contatos.para("LOJISTA", "12345678000195", pasta=pasta)] == ["Fulano"]
    assert [c["nome"] for c in contatos.para("lojista", "98.765.432/0001-10", pasta=pasta)] == ["Outro"]
    assert contatos.para("LOJISTA", None, pasta=pasta) == []             # lojista exige o CNPJ
    assert len(contatos.para("PONTE", pasta=pasta)) == 1 and contatos.para("COMERCIAL", pasta=pasta) == []


@pytest.mark.parametrize("campos, trecho", [
    ({"email": "sem-arroba"}, "E-mail"), ({"email": "a@b"}, "E-mail"), ({"email": "a@b.com, c@d.com"}, "E-mail"),
    ({"email": ""}, "e-mail"), ({"nome": " "}, "nome"), ({"papel": "CHEFE"}, "Papel"),
    ({"cnpj": "123"}, "14 dígitos"), ({"papel": "ORBE"}, "Só contato de LOJISTA"),
])
def test_validacao(pasta, campos, trecho):
    with pytest.raises(ContatoInvalido, match=trecho):
        contatos.adicionar(pasta, _novo(**campos), "ana")
    assert contatos.ler(pasta) == []


def test_duplicado_recusado(pasta):
    contatos.adicionar(pasta, _novo(), "ana")
    with pytest.raises(ContatoInvalido, match="Já existe"):
        contatos.adicionar(pasta, _novo(nome="Outro nome", email="FULANO@x.exemplo.com.br"), "ana")


def test_atualizar(pasta):
    contatos.adicionar(pasta, _novo(), "ana")
    c = contatos.atualizar(pasta, "K001", {"email": "novo@x.exemplo.com.br", "observacao": "ok", "id_contato": "K999"}, "ana")
    assert c["email"] == "novo@x.exemplo.com.br" and contatos.ler(pasta)[0]["observacao"] == "ok"
    assert contatos.ler(pasta)[0]["id_contato"] == "K001"
    with pytest.raises(ContatoInvalido, match="E-mail"):
        contatos.atualizar(pasta, "K001", {"email": "ruim"}, "ana")
    assert contatos.ler(pasta)[0]["email"] == "novo@x.exemplo.com.br"
    with pytest.raises(ContatoInvalido, match="não encontrado"):
        contatos.atualizar(pasta, "K777", {"nome": "x"}, "ana")


def test_remover_move_para_historico(pasta):
    contatos.adicionar(pasta, _novo(), "ana")
    contatos.adicionar(pasta, _novo(cnpj="98765432000110", email="o@y.exemplo.com.br"), "ana")
    assert contatos.remover(pasta, "K001", "bia")["email"] == "fulano@x.exemplo.com.br"
    assert [c["id_contato"] for c in contatos.ler(pasta)] == ["K002"]
    h = contatos.ler_removidos(pasta)
    assert len(h) == 1 and h[0]["id_contato"] == "K001" and h[0]["removido_por"] == "bia" and h[0]["removido_em"]
    assert contatos.adicionar(pasta, _novo(email="z@x.exemplo.com.br"), "ana")["id_contato"] == "K003"   # id nunca reaproveitado
    with pytest.raises(ContatoInvalido):
        contatos.remover(pasta, "K001", "bia")


def test_cadastro_entregue(raiz, resultado):
    cs = contatos.ler(raiz / "cadastro")
    por_papel = {p: [c for c in cs if c["papel"] == p] for p in config.PAPEIS_CONTATO}
    assert all(por_papel[p] for p in config.PAPEIS_CONTATO)
    assert not [e for c in cs for e in contatos.validar(c, [])]
    assert all(c["email"].endswith(".exemplo.com.br") for c in cs)
    cnpjs = set(checkout.nome_por_cnpj(resultado["dados"]["contratos"]))
    assert cnpjs <= {c["cnpj"] for c in por_papel["LOJISTA"]}
    assert contatos.para("COMERCIAL", pasta=raiz / "cadastro")[0]["email"] == "comercial@tarvo.exemplo.com.br"
    assert contatos.para("FINANCEIRO_INTERNO", pasta=raiz / "cadastro")[0]["email"] == "helena@tarvo.exemplo.com.br"
    assert all("fictício" in c["observacao"] for c in cs)


def test_atlas_resolve_por_cnpj_e_por_ec(raiz):
    pasta = raiz / "cadastro"
    por_cnpj = contatos.para("LOJISTA", "39566044000119", pasta=pasta)
    assert len(por_cnpj) == 1 and "Atlas" in por_cnpj[0]["nome"]
    assert contatos.para("LOJISTA", pasta=pasta, ec="1076801732") == por_cnpj
    assert contatos.para("LOJISTA", pasta=pasta, ec="999") == []
