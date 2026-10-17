from src import leitores


def test_contagens(raiz):
    d = leitores.ler_tudo(raiz)
    assert len(d["orbe"]) == 1943
    assert len(d["ponte"]) == 233                      # inclui a duplicata; rodapé fora
    assert len({o["op"] for o in d["ponte"]}) == 232
    assert len(d["aurora"]) == 84
    assert len(d["meridiano"]) == 100
    assert len(d["plano"]) == 52
    assert sum(1 for c in d["plano"].values() if c["aceita"]) == 32
    ativos = [c for c in d["contratos"] if not c["riscado"]]
    assert len(d["contratos"]) == 25 and len(ativos) == 24  # Globo Trotter riscada


def test_aurora_saldo_e_linha_fisica(raiz):
    movs, meta = leitores.ler_aurora(next(raiz.glob("*aurora*.csv")))
    assert movs[0]["ref"] == "L9" and movs[-1]["ref"] == "L92"
    assert meta["saldo_anterior"] + sum(m["valor"] for m in movs) == meta["saldo_final"]


def test_planilha_tipos_estranhos(raiz):
    c = {x["linha"]: x for x in leitores.ler_taxas(next(raiz.glob("*taxas*.xlsx")))}
    assert c[14]["cnpj"] == "03229837000103"           # CNPJ numérico sem zero à esquerda
    assert c[25]["cnpj"] == "08780784000120"
    assert str(c[20]["taxas"]["PARC_2_6"]) == "3.09"         # taxa como texto "3,09%"
    assert c[29]["spread"] is None                     # "padrão"
    assert c[6]["fim"].isoformat() == "2026-09-14" and c[7]["inicio"].isoformat() == "2026-09-15"


def test_ponte_anexo_em_memoria(raiz):
    ops, meta = leitores.ler_ponte(next(raiz.glob("*.eml")))
    assert meta["anexo"].endswith(".xlsx")
    assert meta["data_repasse"].isoformat() == "2026-10-06"
    assert all(len(o["cnpj"]) == 14 for o in ops)
