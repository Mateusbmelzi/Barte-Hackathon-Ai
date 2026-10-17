from decimal import Decimal as D

from src.dinheiro import arred, dec


def test_half_up_simetrico():
    assert arred(D("131.005")) == D("131.01")      # S11
    assert arred(D("-0.005")) == D("-0.01")        # simétrico (R01)
    assert arred(D("0.005")) == D("0.01")
    assert arred(D("2.345")) == D("2.35")          # half-even daria 2.34
    assert arred(D("-2.345")) == D("-2.35")
    assert arred(D("0.004999")) == D("0.00")


def test_meio_da_remessa():
    # 50% de spread com centavo ímpar cai no meio centavo: 262,01/2 = 131,005 -> 131,01
    assert arred(D("262.01") * D("0.5")) == D("131.01")


def test_dec_formato_br():
    assert dec("1.234,56") == D("1234.56")
    assert dec("-2193,16") == D("-2193.16")
    assert dec("612.334,81") == D("612334.81")
    assert dec(0.015012) == D("0.015012")
    assert dec("") is None
