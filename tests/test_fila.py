"""Fila de trabalho (src/fila.py): log só-acrescenta, transições, status atual, chaves estáveis e colunas extras."""
import csv
from datetime import datetime
from decimal import Decimal as D

import pytest

from src import config, fechamento, fila
from src.fila import FilaInvalida

PEN = "PEN|SPREAD_NEGATIVO|1001"
DIV = "DIV|ORBE|00520815000100|ISENCAO_NAO_INFORMADA"


def _reg(pasta, chave, acao, status="", tipo="PENDENCIA", usuario="ana", detalhe=""):
    return fila.registrar(pasta, usuario, chave, tipo, acao, status, detalhe)


def _csv(pasta, nome):
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


# ---------------------------------------------------------------- registrar / transições
def test_registrar_cria_arquivo_com_cabecalho_e_so_acrescenta(tmp_path):
    pasta = tmp_path / "meses" / "2026-09"
    assert fila.ler_log(pasta) == []
    l1 = _reg(pasta, PEN, "SUGESTAO_IA", detalhe="texto")
    _reg(pasta, PEN, "EMAIL_ENVIADO")
    bruto = (pasta / "fila_log.csv").read_text(encoding="utf-8").splitlines()
    assert bruto[0] == "data_hora;usuario;chave;tipo_item;acao;status_novo;detalhe"
    assert len(bruto) == 3 and l1["status_novo"] == ""
    antes = (pasta / "fila_log.csv").read_text(encoding="utf-8")
    _reg(pasta, PEN, "COMENTARIO", detalhe="linha 1\nlinha 2; com ponto e vírgula")
    assert (pasta / "fila_log.csv").read_text(encoding="utf-8").startswith(antes)
    assert fila.ler_log(pasta)[-1]["detalhe"] == "linha 1\nlinha 2; com ponto e vírgula"


def test_fluxo_de_status_e_reabertura(tmp_path):
    p = tmp_path
    assert fila.status_atual(fila.ler_log(p)) == {}
    assert _reg(p, PEN, "EMAIL_ENVIADO")["status_novo"] == "EM_ACOMPANHAMENTO"
    _reg(p, PEN, "EMAIL_ENVIADO")                                    # 2º e-mail: continua em acompanhamento
    assert _reg(p, PEN, "BAIXA", detalhe="resolvido")["status_novo"] == "BAIXADA"
    assert fila.status_atual(fila.ler_log(p))[PEN]["status"] == "BAIXADA"
    assert _reg(p, PEN, "REABERTA", detalhe="voltou")["status_novo"] == "ABERTA"
    assert fila.status_atual(fila.ler_log(p))[PEN]["status"] == "ABERTA"
    _reg(p, PEN, "EMAIL_ENVIADO")
    assert _reg(p, PEN, "REABERTA")["status_novo"] == "ABERTA"        # EM_ACOMPANHAMENTO -> ABERTA


def test_divergencia_pode_ser_declinada_e_reaberta(tmp_path):
    assert _reg(tmp_path, DIV, "DECLINADA", tipo="DIVERGENCIA", detalhe="não vale")["status_novo"] == "DECLINADA"
    assert _reg(tmp_path, DIV, "REABERTA", tipo="DIVERGENCIA")["status_novo"] == "ABERTA"


@pytest.mark.parametrize("previas, acao, tipo, chave", [
    ([], "DECLINADA", "PENDENCIA", PEN),                               # só divergência declina
    ([], "REABERTA", "PENDENCIA", PEN),                                # ABERTA -> ABERTA
    (["BAIXA"], "BAIXA", "PENDENCIA", PEN),                            # BAIXADA -> BAIXADA
    (["BAIXA"], "EMAIL_ENVIADO", "PENDENCIA", PEN),                    # BAIXADA -> EM_ACOMPANHAMENTO
    (["EMAIL_ENVIADO"], "DECLINADA", "DIVERGENCIA", DIV),              # EM_ACOMPANHAMENTO -> DECLINADA
    (["DECLINADA"], "BAIXA", "DIVERGENCIA", DIV),                      # DECLINADA -> BAIXADA
    ([], "ACAO_INEXISTENTE", "PENDENCIA", PEN),
    ([], "BAIXA", "OUTRO", PEN),
    ([], "BAIXA", "DIVERGENCIA", PEN),                                 # chave PEN com tipo DIVERGENCIA
])
def test_transicoes_e_valores_invalidos(tmp_path, previas, acao, tipo, chave):
    for a in previas:
        _reg(tmp_path, chave, a, tipo=tipo)
    n = len(fila.ler_log(tmp_path))
    with pytest.raises(FilaInvalida):
        _reg(tmp_path, chave, acao, tipo=tipo)
    assert len(fila.ler_log(tmp_path)) == n                            # nada foi gravado


def test_status_novo_invalido_e_usuario_obrigatorio(tmp_path):
    with pytest.raises(FilaInvalida, match="Status"):
        _reg(tmp_path, PEN, "BAIXA", status="FINALIZADA")
    with pytest.raises(FilaInvalida, match="não leva"):
        _reg(tmp_path, PEN, "BAIXA", status="EM_ACOMPANHAMENTO")
    with pytest.raises(FilaInvalida, match="usuario"):
        _reg(tmp_path, PEN, "BAIXA", usuario=" ")
    with pytest.raises(FilaInvalida, match="Chave"):
        _reg(tmp_path, "XYZ", "BAIXA")


def test_status_atual_campos(tmp_path):
    t = datetime(2026, 10, 17, 10, 0, 0)
    fila.registrar(tmp_path, "ana", PEN, "PENDENCIA", "SUGESTAO_IA", "", "texto da IA", agora=t)
    fila.registrar(tmp_path, "ana", PEN, "PENDENCIA", "EMAIL_ENVIADO", "", "", agora=t.replace(hour=11))
    fila.registrar(tmp_path, "bia", PEN, "PENDENCIA", "BAIXA", "", "pago em 20/10", agora=t.replace(hour=12))
    fila.registrar(tmp_path, "ana", PEN, "PENDENCIA", "SUGESTAO_IA", "", "outra sugestão", agora=t.replace(hour=13))
    s = fila.status_atual(fila.ler_log(tmp_path))[PEN]
    assert s == {"status": "BAIXADA", "ultima_acao": "BAIXA", "data_ultima_acao": "2026-10-17 12:00:00",
                 "responsavel": "bia", "comentario": "pago em 20/10"}     # a IA não vira ultima_acao
    assert [l["acao"] for l in fila.historico(fila.ler_log(tmp_path), PEN)][:2] == ["SUGESTAO_IA", "EMAIL_ENVIADO"]


# ---------------------------------------------------------------- chaves e itens
def test_chaves():
    assert fila.chave_pendencia({"tipo": "OPERACAO_DUPLICADA", "ref_origem": "OP9"}) == "PEN|OPERACAO_DUPLICADA|OP9"
    g = {"contraparte": "PONTE", "cnpj": "17217888000111", "natureza": "CONTRATO"}
    assert fila.chave_divergencia(g) == "DIV|PONTE|17217888000111|CONTRATO"
    linha = {"linha_negocio": "REMESSA", "cnpj": "17217888000111", "natureza": "CONTRATO"}
    assert fila.chave_divergencia(linha) == fila.chave_divergencia(g)
    assert fila.chave_divergencia({**linha, "linha_negocio": "CHECKOUT"}).startswith("DIV|ORBE|")


def test_chaves_estaveis_entre_execucoes(resultado, tmp_path):
    r2 = fechamento.executar(fechamento.RAIZ, tmp_path / "s2", investigar=False)
    k1 = [fila.chave_pendencia(p) for p in resultado["pendencias"]]
    assert k1 == [fila.chave_pendencia(p) for p in r2["pendencias"]]
    assert len(set(k1)) == len(k1)
    assert [i["chave"] for i in fila.itens(resultado)] == [i["chave"] for i in fila.itens(r2)]


def test_itens_unificados(resultado):
    its = fila.itens(resultado)
    pens = [i for i in its if i["tipo_item"] == "PENDENCIA"]
    divs = [i for i in its if i["tipo_item"] == "DIVERGENCIA"]
    assert len(pens) == len(resultado["pendencias"]) and divs
    assert all(i["status"] == "ABERTA" and i["destinos"] and i["objetivo"] and i["titulo"] for i in its)
    assert {i["chave"] for i in divs} == {fila.chave_divergencia(d) for d in resultado["divergencias"]}
    assert sum(i["qtd"] for i in divs) == len(resultado["divergencias"])
    casa = next(i for i in divs if i["natureza"] == "ISENCAO_NAO_INFORMADA")
    assert casa["destinos"] == ["COMERCIAL", "LOJISTA"] and casa["valor"] == D("15396.77")
    assert casa["valor_formula"] == "15397.42"                        # valor da ação x fórmula (truncamento, S51)
    por_tipo = {i["tipo"]: i for i in pens}
    assert por_tipo["SPREAD_NEGATIVO"]["destinos"] == ["PONTE"]
    assert por_tipo["CREDITO_NAO_IDENTIFICADO"]["destinos"] == ["BANCO_AURORA"]


def test_todo_tipo_de_pendencia_tem_acao_configurada(resultado):
    for p in resultado["pendencias"]:
        assert p["tipo"] in config.ACOES_POR_TIPO, p["tipo"]
    for a in config.ACOES_POR_TIPO.values():
        assert a["objetivo"] and a["destinos"] and set(a["destinos"]) <= set(config.PAPEIS_CONTATO)
    assert config.acao_do_tipo("TIPO_NOVO")["destinos"] == ["FINANCEIRO_INTERNO"]


# ---------------------------------------------------------------- colunas extras nos CSVs
def test_csvs_sem_fila_tudo_aberta(resultado):
    pend = _csv(resultado["saida"], "pendencias.csv")
    assert list(pend[0])[-5:] == ["status", "ultima_acao", "data_ultima_acao", "responsavel", "comentario"]
    assert all(p["status"] == "ABERTA" and not (p["ultima_acao"] or p["data_ultima_acao"] or p["responsavel"]
                                                 or p["comentario"]) for p in pend)
    div = _csv(resultado["saida"], "divergencias_taxa.csv")
    assert list(div[0])[-1] == "status" and {d["status"] for d in div} == {"ABERTA"}


def test_csvs_com_fila_refletem_o_log(resultado, tmp_path):
    mes = tmp_path / "mes"
    chave_pen = fila.chave_pendencia(resultado["pendencias"][1])         # PEN-0002
    chave_div = "DIV|ORBE|00520815000100|ISENCAO_NAO_INFORMADA"          # grupo da Casa do Estudante
    fila.registrar(mes, "ana", chave_pen, "PENDENCIA", "BAIXA", "", "resolvido com a Orbe")
    fila.registrar(mes, "ana", chave_div, "DIVERGENCIA", "EMAIL_ENVIADO")
    r = fechamento.executar(fechamento.RAIZ, tmp_path / "s", investigar=False, fila=mes)
    pend = {p["id_saida"]: p for p in _csv(r["saida"], "pendencias.csv")}
    assert (pend["PEN-0002"]["status"], pend["PEN-0002"]["ultima_acao"], pend["PEN-0002"]["responsavel"],
            pend["PEN-0002"]["comentario"]) == ("BAIXADA", "BAIXA", "ana", "resolvido com a Orbe")
    assert pend["PEN-0002"]["data_ultima_acao"]
    assert pend["PEN-0001"]["status"] == "ABERTA"
    div = _csv(r["saida"], "divergencias_taxa.csv")
    assert {d["status"] for d in div if d["natureza"] == "ISENCAO_NAO_INFORMADA"} == {"EM_ACOMPANHAMENTO"}
    assert {d["status"] for d in div if d["natureza"] != "ISENCAO_NAO_INFORMADA"} == {"ABERTA"}
    # o resto do fechamento não muda por causa da fila
    assert [c["comissao"] for c in r["comissoes"]] == [c["comissao"] for c in resultado["comissoes"]]
    its = {i["chave"]: i for i in fila.itens(r, fila.ler_log(mes))}
    assert its[chave_pen]["status"] == "BAIXADA" and its[chave_div]["status"] == "EM_ACOMPANHAMENTO"


def test_cli_fila(tmp_path, capsys):
    mes = tmp_path / "mes"
    fila.registrar(mes, "ana", "PEN|SPREAD_NEGATIVO|inexistente", "PENDENCIA", "COMENTARIO", "", "x")
    fechamento.main(["--saida", str(tmp_path / "s"), "--fila", str(mes)])
    assert (tmp_path / "s" / "pendencias.csv").exists()
    assert "Fechamento competência" in capsys.readouterr().out


def test_valor_da_divergencia_cai_na_formula_sem_dossie(resultado):
    sem = {**resultado, "investigacao": None}
    casa = next(i for i in fila.itens(sem) if i["natureza"] == "ISENCAO_NAO_INFORMADA")
    assert casa["valor"] == D(casa["valor_formula"]) == D("15397.42")


def test_cnpj_inferido_pelo_nome_para_sugerir_contato(resultado):
    its = {i["tipo"]: i for i in fila.itens(resultado) if i["tipo_item"] == "PENDENCIA"}
    assert its["DEVOLUCAO_REPASSE"]["cnpj"] == "17217888000111" and "Mundo Aberto" in its["DEVOLUCAO_REPASSE"]["lojista"]
    assert its["ACOMPANHAR_REMESSA_FUTURA"]["cnpj"] == "95739378000118"
    assert fila._cnpj_pelo_nome("PIX RECEB NOME INEXISTENTE", {"1": "Ana Ltda"}) == ""
    assert fila._cnpj_pelo_nome("PIX RECEB ANA", {"1": "Ana Ltda", "2": "Ana Maria SA"}) == ""     # ambíguo
    assert fila._cnpj_pelo_nome("DEVOLUCAO PIX - ANA LT", {"1": "Ana Ltda", "2": "Ana Maria SA"}) == "1"


def test_pendencia_e_grupo_vinculados(resultado):
    its = fila.itens(resultado)
    por = {i["chave"]: i for i in its}
    pares = [(i["chave"], i["vinculado_a"]) for i in its if i["tipo_item"] == "PENDENCIA" and i["vinculado_a"]]
    tipos = {por[a]["tipo"] for a, _ in pares}
    assert tipos == {"DEVOLUCAO_LOJISTA_ISENCAO", "DIVERGENCIA_TAXA_CHECKOUT", "DIVERGENCIA_SPREAD_REMESSA"}
    assert len(pares) == 4          # PEN-0001, 0002, 0003, 0007
    for a, b in pares:
        assert por[b]["tipo_item"] == "DIVERGENCIA" and por[b]["vinculado_a"] == a
        assert por[a]["cnpj"] == por[b]["cnpj"] and por[a]["natureza"] == "" 
        assert fila.chaves_vinculadas(a, its) == [a, b] and fila.chaves_vinculadas(b, its) == [b, a]
    solta = next(i for i in its if i["tipo"] == "SPREAD_NEGATIVO")
    assert solta["vinculado_a"] is None and fila.chaves_vinculadas(solta["chave"], its) == [solta["chave"]]
    assert sum(1 for i in its if i["tipo_item"] == "DIVERGENCIA" and i["vinculado_a"]) == 4
