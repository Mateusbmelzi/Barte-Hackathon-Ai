"""Valores FIXOS auditados de forma independente (docs/02_validacao.md e docs/01_entendimento_dados.md
§3.5/§9), conferidos contra os CSVs gerados em saida/ (não contra estruturas internas)."""
from collections import defaultdict
from decimal import Decimal as D

import pandas as pd
import pytest


def _ler(resultado, nome):
    return pd.read_csv(resultado["saida"] / nome, sep=";", dtype=str, keep_default_na=False)


def _soma(vals):
    return sum((D(v) for v in vals), D("0"))


def test_totais_auditados(resultado):
    com = _ler(resultado, "comissoes_por_lojista.csv")
    notas = _ler(resultado, "notas_a_emitir.csv")
    div = _ler(resultado, "divergencias_taxa.csv")
    lan = _ler(resultado, "lancamentos_classificados.csv")
    chk = com[com.linha_negocio == "CHECKOUT"]
    rem = com[com.linha_negocio == "REMESSA"]
    assert _soma(chk.comissao_brl) == D("207039.73")
    n_chk = notas[notas.linha_negocio == "CHECKOUT"]
    assert len(n_chk) == 20 and _soma(n_chk.valor_brl) == D("207045.23")
    d_chk = div[div.linha_negocio == "CHECKOUT"]
    assert len(d_chk) == 210 and _soma(d_chk.diferenca_brl) == D("16973.65")
    assert _soma(rem.comissao_brl) == D("39543.45")
    assert sum(int(x) for x in rem.qtd_transacoes) == 228
    n_rem = notas[notas.linha_negocio == "REMESSA"]
    assert len(n_rem) == 1 and n_rem.valor_brl.iloc[0] == "39543.45" and n_rem.tomador_cnpj.iloc[0] == "75374179000146"
    d_rem = div[div.linha_negocio == "REMESSA"]
    assert len(d_rem) == 23 and _soma(d_rem.diferenca_brl) == D("1418.85")
    casa = chk[chk.cnpj == "00520815000100"]
    assert casa.comissao_brl.iloc[0] == "-5.50"
    assert len(lan) == 184


@pytest.mark.parametrize("cnpj,comissao", [
    ("03229837000103", "7316.07"),    # Fluente
    ("07752116000126", "10711.41"),   # Kiwi (de-para S03, com reversão)
    ("23109187000161", "16077.90"),   # Oxford (taxas como texto, estorno de agosto)
    ("22224579000109", "11916.02"),   # Bridge (troca de vigência 15/09)
    ("95927868000148", "15621.27"),   # Rota Global
    ("66564512000199", "7767.78"),    # Novo Horizonte (de-para S03)
    ("78576234000179", "9014.42"),    # Horizonte Viagens (de-para S03)
    ("17217888000111", "18522.09"),   # Mundo Aberto
])
def test_checkout_por_lojista(resultado, cnpj, comissao):
    com = _ler(resultado, "comissoes_por_lojista.csv")
    linha = com[(com.linha_negocio == "CHECKOUT") & (com.cnpj == cnpj)]
    assert linha.comissao_brl.tolist() == [comissao]


@pytest.mark.parametrize("cnpj,valor,n", [
    ("00520815000100", "15397.42", 118),   # Casa (taxa zero)
    ("95927868000148", "1546.28", 87),     # Rota (+0,5 p.p.)
    ("22224579000109", "29.95", 5),        # Bridge (vigência ignorada)
])
def test_divergencia_checkout_por_lojista(resultado, cnpj, valor, n):
    div = _ler(resultado, "divergencias_taxa.csv")
    d = div[(div.linha_negocio == "CHECKOUT") & (div.cnpj == cnpj)]
    assert len(d) == n and _soma(d.diferenca_brl) == D(valor)


@pytest.mark.parametrize("cnpj,comissao", [
    ("17217888000111", "3547.69"),   # Mundo Aberto
    ("50900987000179", "1292.67"),   # Bagagem (duplicata fora)
    ("53857560000123", "3764.05"),   # Canguru (negativa fora)
    ("95927868000148", "4918.34"),   # Rota
    ("95739378000118", "3007.30"),   # Ponte Aérea (negativa fora)
])
def test_remessa_por_lojista(resultado, cnpj, comissao):
    com = _ler(resultado, "comissoes_por_lojista.csv")
    linha = com[(com.linha_negocio == "REMESSA") & (com.cnpj == cnpj)]
    assert linha.comissao_brl.tolist() == [comissao]
