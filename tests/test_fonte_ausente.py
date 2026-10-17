"""S53: fonte que falta não derruba o mês. Fecha o que não depende dela, marca PROVISORIO e abre pendência
FONTE_AUSENTE (valor 0, Helena decide). Fechamento completo: 6 CSVs idênticos, byte a byte, aos de saida/."""
import csv
import shutil

import pytest

from src import fechamento
from src.leitores import descobrir_arquivos

CSVS = ["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv",
        "lancamentos_classificados.csv", "pendencias.csv", "rastro.csv"]


def montar(raiz, destino, sem=()):
    """Copia as fontes para destino, omitindo as chaves em `sem` (ex.: 'ponte', 'taxas')."""
    destino.mkdir(parents=True, exist_ok=True)
    for chave, v in descobrir_arquivos(raiz).items():
        if chave in sem:
            continue
        for p in (v if isinstance(v, list) else [v]):
            shutil.copy(p, destino / p.name)
    return destino


def ler_csv(pasta, nome):
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def rodar(raiz, tmp_path, sem=()):
    ent = montar(raiz, tmp_path / "entrada", sem)
    r = fechamento.executar(ent, tmp_path / "saida", investigar=False)
    return r, tmp_path / "saida"


def pend(saida, tipo):
    return [p for p in ler_csv(saida, "pendencias.csv") if p["tipo"] == tipo]


def test_completo_identico_aos_de_saida(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path)
    assert not r["parcial"] and r["aviso_parcial"] is None
    for nome in CSVS:
        assert (saida / nome).read_bytes() == (raiz / "saida" / nome).read_bytes(), nome
    assert "status" not in (saida / "notas_a_emitir.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "PARCIAL" not in fechamento.resumo(r)


def test_sem_email_da_ponte(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path, sem={"ponte"})
    assert r["parcial"] and r["bloqueado"]["remessa"] and not r["bloqueado"]["checkout"]
    # checkout e lançamentos saem; remessa não
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"CHECKOUT"}
    assert {n["linha_negocio"] for n in ler_csv(saida, "notas_a_emitir.csv")} == {"CHECKOUT"}
    assert len(ler_csv(saida, "lancamentos_classificados.csv")) == 184
    assert all(c["status"] == "PROVISORIO" for c in ler_csv(saida, "comissoes_por_lojista.csv"))
    assert all(n["status"] == "PROVISORIO" for n in ler_csv(saida, "notas_a_emitir.csv"))
    # pendência FONTE_AUSENTE: valor 0, Helena, diz o que ficou bloqueado
    (p,) = pend(saida, "FONTE_AUSENTE")
    assert p["valor_brl"] == "0.00" and p["quem_decide"] == "Helena (Financeiro)"
    assert "nota da Ponte e comissões de remessa não calculadas" in p["motivo"] and "*.eml" in p["motivo"]
    # sem Ponte não há conciliação de TED/PIX: nada de pendência enganosa de "não bate"
    assert not pend(saida, "TED_PONTE_NAO_CONCILIADO") and not pend(saida, "ACOMPANHAR_REMESSA_FUTURA")
    txt = fechamento.resumo(r)
    assert txt.splitlines()[1].startswith("FECHAMENTO PARCIAL — bloqueado: nota da Ponte")
    assert "Comissão REMESSA" in txt and "BLOQUEADO" in txt


def test_sem_meridiano_aurora_classificado(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path, sem={"meridiano"})
    bancos = {l["banco"] for l in ler_csv(saida, "lancamentos_classificados.csv")}
    assert bancos == {"AURORA"} and r["bloqueado"]["MERIDIANO"] and not r["bloqueado"]["AURORA"]
    (p,) = pend(saida, "FONTE_AUSENTE")
    assert "Meridiano" in p["motivo"] and p["quem_decide"] == "Helena (Financeiro)"
    assert not pend(saida, "TRANSFERENCIA_EM_TRANSITO")          # contrapartida está no banco que falta
    # checkout e remessa não dependem do extrato: completos
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"CHECKOUT", "REMESSA"}


def test_sem_aurora(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path, sem={"aurora"})
    assert {l["banco"] for l in ler_csv(saida, "lancamentos_classificados.csv")} == {"MERIDIANO"}
    assert not pend(saida, "EXTRATO_NAO_FECHA")


def test_sem_taxas_checkout_bloqueado_remessa_segue(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path, sem={"taxas"})
    assert r["bloqueado"]["checkout"] and not r["bloqueado"]["remessa"]
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"REMESSA"}
    assert ler_csv(saida, "divergencias_taxa.csv") == []          # sem contrato não há o que comparar
    assert not pend(saida, "REMESSA_SEM_CONTRATO")
    (p,) = pend(saida, "FONTE_AUSENTE")
    assert "checkout" in p["motivo"] and "taxas" in p["motivo"]
    assert "divergências de remessa e alerta de antecipação bloqueados" in p["motivo"]
    assert "Divergências REMESSA  : BLOQUEADO" in fechamento.resumo(r)
    assert len(ler_csv(saida, "lancamentos_classificados.csv")) == 184


def test_sem_orbe_ou_sem_plano(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path / "a", sem={"orbe"})
    assert r["bloqueado"]["checkout"] and r["competencia"] == "09/2026"      # competência vem da Ponte
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"REMESSA"}
    r, saida = rodar(raiz, tmp_path / "b", sem={"plano"})
    assert ler_csv(saida, "lancamentos_classificados.csv") == []
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"CHECKOUT", "REMESSA"}


def test_rastro_continua_fechando_no_parcial(raiz, tmp_path):
    r, saida = rodar(raiz, tmp_path, sem={"ponte", "meridiano"})
    rastro = {}
    for l in ler_csv(saida, "rastro.csv"):
        rastro[l["id_saida"]] = rastro.get(l["id_saida"], 0) + float(l["valor"])
    for n in ler_csv(saida, "notas_a_emitir.csv"):
        assert rastro[n["id_saida"]] == pytest.approx(float(n["valor_brl"]), abs=0.005)
    assert len(pend(saida, "FONTE_AUSENTE")) == 2


def test_nenhuma_fonte_e_erro_legivel(tmp_path):
    ent = tmp_path / "vazia"
    ent.mkdir()
    with pytest.raises(ValueError, match="Nenhum arquivo"):
        fechamento.executar(ent, tmp_path / "s", investigar=False)
