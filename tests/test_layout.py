"""S53: layout diferente (coluna renomeada/removida) = fonte "com layout inesperado": parte bloqueada +
pendência LAYOUT_INESPERADO com as colunas faltantes e as encontradas; nunca stack trace."""
import shutil

import openpyxl

from src import fechamento, leitores
from src.leitores import descobrir_arquivos
from tests.test_fonte_ausente import ler_csv, pend


def copiar(raiz, destino):
    destino.mkdir(parents=True, exist_ok=True)
    for v in descobrir_arquivos(raiz).values():
        for p in (v if isinstance(v, list) else [v]):
            shutil.copy(p, destino / p.name)
    return destino


def rodar(ent, tmp_path):
    return fechamento.executar(ent, tmp_path / "saida", investigar=False), tmp_path / "saida"


def editar_texto(arquivo, antigo, novo):
    t = arquivo.read_bytes().decode("latin-1")
    assert antigo in t
    arquivo.write_bytes(t.replace(antigo, novo, 1).encode("latin-1"))


def test_orbe_coluna_renomeada(raiz, tmp_path):
    ent = copiar(raiz, tmp_path / "e")
    for p in ent.glob("*orbe*.csv"):
        editar_texto(p, "valor_bruto", "valor_bruto_brl")
    r, saida = rodar(ent, tmp_path)
    assert r["bloqueado"]["checkout"] and not r["bloqueado"]["remessa"]
    ps = pend(saida, "LAYOUT_INESPERADO")
    assert ps and all(p["quem_decide"] == "Helena (Financeiro)" and p["valor_brl"] == "0.00" for p in ps)
    assert "valor_bruto" in ps[0]["motivo"] and "valor_bruto_brl" in ps[0]["motivo"]   # faltante e encontrada
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"REMESSA"}
    txt = fechamento.resumo(r)
    assert "FECHAMENTO PARCIAL" in txt and "layout inesperado" in txt and "Traceback" not in txt


def test_um_orbe_ruim_e_outro_bom_usa_o_bom(raiz, tmp_path):
    ent = copiar(raiz, tmp_path / "e")
    ruim = sorted(ent.glob("*orbe*.csv"))[-1]
    editar_texto(ruim, "valor_bruto", "bruto")
    r, saida = rodar(ent, tmp_path)
    assert r["parcial"] and r["bloqueado"]["checkout"]            # checkout inteiro bloqueado, não só o arquivo ruim
    (p,) = pend(saida, "LAYOUT_INESPERADO")
    assert ruim.name in p["motivo"] and "checkout inteiro ficou bloqueado" in p["motivo"]
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"REMESSA"}
    assert not pend(saida, "SALDO_CHECKOUT_NAO_POSITIVO")


def test_plano_aurora_e_ofx_com_layout_diferente(raiz, tmp_path):
    ent = copiar(raiz, tmp_path / "e")
    editar_texto(next(ent.glob("*plano_de_contas*.csv")), "ACEITA_LANCTO", "ACEITA")
    editar_texto(next(ent.glob("*aurora*.csv")), "Valor (R$)", "Valor")
    ofx = next(ent.glob("*.ofx"))
    ofx.write_bytes(ofx.read_bytes().replace(b"<FITID>", b"<ID>"))
    r, saida = rodar(ent, tmp_path)
    assert len(pend(saida, "LAYOUT_INESPERADO")) == 3
    assert ler_csv(saida, "lancamentos_classificados.csv") == []
    assert {c["linha_negocio"] for c in ler_csv(saida, "comissoes_por_lojista.csv")} == {"CHECKOUT", "REMESSA"}


def test_taxas_sem_coluna(raiz, tmp_path):
    ent = copiar(raiz, tmp_path / "e")
    caminho = next(ent.glob("*taxas*.xlsx"))
    wb = openpyxl.load_workbook(caminho)
    ws = wb[next(n for n in wb.sheetnames if "vigente" in n.lower())]
    achou = False
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.strip().lower() == "pix":
                c.value, achou = "Pix 2", True
    assert achou
    wb.save(caminho)
    r, saida = rodar(ent, tmp_path)
    (p,) = pend(saida, "LAYOUT_INESPERADO")
    assert "PIX" in p["motivo"] and "Pix 2" in p["motivo"] and r["bloqueado"]["checkout"]


def test_arquivo_lixo_nao_gera_stack_trace(raiz, tmp_path):
    ent = copiar(raiz, tmp_path / "e")
    next(ent.glob("*.eml")).write_bytes(b"lixo")
    r, saida = rodar(ent, tmp_path)
    (p,) = pend(saida, "LAYOUT_INESPERADO")
    assert "Traceback" not in p["motivo"] and r["bloqueado"]["remessa"]


def test_validar_layout_arquivo_completo_ok(raiz):
    for chave, v in descobrir_arquivos(raiz).items():
        for p in (v if isinstance(v, list) else [v]):
            assert leitores.validar_layout(chave, p) is None, p.name
