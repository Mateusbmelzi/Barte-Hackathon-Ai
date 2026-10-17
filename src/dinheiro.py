"""Aritmética de dinheiro. Sempre Decimal; nunca float/round() para valores finais."""
from decimal import Decimal, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


def dec(valor):
    """Converte texto BR ('1.234,56', '-0,5'), número ou Decimal para Decimal. None/'' -> None."""
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))  # str(float) = representação mais curta (ex.: 0.015012)
    s = str(valor).strip()
    if s == "":
        return None
    if "," in s:  # formato BR: milhar '.' e decimal ','
        s = s.replace(".", "").replace(",", ".")
    return Decimal(s)


def arred(valor):
    """R01/S11: centavo, meio centavo para cima e simétrico no negativo
    (0,005 -> 0,01; -0,005 -> -0,01). ROUND_HALF_UP do Decimal arredonda
    o meio para longe do zero, que é exatamente o simétrico pedido."""
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def soma(valores):
    total = Decimal("0.00")
    for v in valores:
        total += v
    return total


def fmt(valor):
    """Valor monetário para CSV: ponto decimal, 2 casas."""
    return f"{arred(valor):.2f}"


def fmt_pct(valor):
    """Taxa em % para CSV (ex.: 2.69, 0, 1.5012)."""
    if valor is None:
        return ""
    s = f"{Decimal(valor):.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def fmt_br(valor):
    """Valor em texto pt-BR para discriminação de nota (ex.: R$ 7.316,07)."""
    s = f"{arred(valor):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
