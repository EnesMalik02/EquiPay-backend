from decimal import Decimal

_CURRENCY_META: dict[str, tuple[str, int]] = {
    "TRY": ("₺", 2),
    "USD": ("$", 2),
    "EUR": ("€", 2),
    "JPY": ("¥", 0),
}


def format_balance(amount: Decimal, currency_code: str) -> tuple[str, str]:
    """Returns (balance_formatted, balance_direction).

    balance_formatted: e.g. "+₺150.00", "-$50.00", "Denk"
    balance_direction: "receivable" | "debt" | "settled"
    """
    symbol, places = _CURRENCY_META.get(currency_code, (currency_code, 2))

    if amount > 0:
        return f"+{symbol}{amount:.{places}f}", "receivable"
    elif amount < 0:
        return f"-{symbol}{abs(amount):.{places}f}", "debt"
    else:
        return f"{symbol}{Decimal(0):.{places}f}", "settled"
