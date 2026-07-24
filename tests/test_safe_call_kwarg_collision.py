"""
Regressionstest für einen Namenskollision-Bug in `utils.errors.safe_call`.

`safe_call(func, *args, default=None, **kwargs)` hatte ein eigenes
Keyword-Argument `default`, das mit den per **kwargs an `func`
durchgereichten Argumenten kollidierte, sobald `func` selbst einen
Parameter namens `default` besitzt (ein in Python sehr gebräuchlicher
Parametername, siehe z.B. `dict.get`, Konfigurations-Getter etc.).

Ruft der Aufrufer `safe_call(func, (1, 2), {"default": 5})` in der Absicht,
den Wert `5` als `default`-Argument an `func` weiterzureichen, fing
`safe_call` das Keyword-Argument (in der alten `*args`/`**kwargs`-API)
fälschlich für sich selbst ab (als "Rückgabewert bei Fehler") statt es an
`func` durchzureichen. Der Aufruf von `func` verlor dadurch
stillschweigend das `default`-Argument.

mypy meldete dazu (baseline-bekannt) an derselben Stelle:
    utils/errors.py:123: error: Arguments not allowed after ParamSpec.args
Das war kein rein kosmetischer Stub-Fehler, sondern der Typchecker wies
strukturell korrekt darauf hin, dass ein benanntes Keyword-Argument
zwischen `*args: P.args` und `**kwargs: P.kwargs` nicht sicher ist - genau
diese Unsicherheit manifestierte sich als echter Laufzeit-Bug.

Fix: `safe_call` nimmt Positions-/Keyword-Argumente für `func` jetzt als
eigene `call_args`/`call_kwargs`-Container entgegen (analog zu
`threading.Thread(target, args=..., kwargs=...)`), statt sie per
`*args`/`**kwargs` mit dem eigenen `default`-Parameter zu vermischen.
"""

from pysticky.utils.errors import safe_call


def _configurable(a: int, b: int, default: int = 99) -> int:
    """Eine Funktion, die selbst einen Parameter namens 'default' hat."""
    return a + b + default


def test_safe_call_forwards_default_kwarg_to_wrapped_function() -> None:
    """
    Ruft der Aufrufer safe_call(func, (1, 2), {"default": 5}) auf, muss
    `default=5` an `_configurable` durchgereicht werden (Ergebnis
    1+2+5=8), nicht als safe_call-eigener Fehler-Rückgabewert abgefangen
    werden (was b.a.w. zu 1+2+99=102 führen würde, weil `_configurable`
    mit seinem eigenen default=99 aufgerufen wird und der Aufruf gar
    nicht fehlschlägt).
    """
    result = safe_call(_configurable, (1, 2), {"default": 5})
    assert result == 8, (
        f"safe_call hat 'default=5' nicht an die Zielfunktion durchgereicht "
        f"(bekam {result}, erwartet 8) - Namenskollision mit dem eigenen "
        f"'default'-Parameter von safe_call"
    )


def test_safe_call_still_returns_own_default_on_real_error() -> None:
    """safe_call muss bei einem echten Fehler weiterhin seinen eigenen
    Fehler-Rückgabewert (default=...) liefern können."""

    def boom() -> int:
        raise ValueError("kaputt")

    result = safe_call(boom, default=42)
    assert result == 42


def test_safe_call_forwards_positional_and_keyword_args() -> None:
    """Normale Weiterleitung von Positions- und Keyword-Argumenten muss
    weiterhin funktionieren."""

    def add(a: int, b: int, *, c: int = 0) -> int:
        return a + b + c

    assert safe_call(add, (1, 2)) == 3
    assert safe_call(add, (1, 2), {"c": 10}) == 13


def test_safe_call_no_args_still_works() -> None:
    """Aufruf ohne jegliche Argumente (nur func) muss weiterhin funktionieren."""

    def boom() -> int:
        raise ValueError("kaputt")

    assert safe_call(boom) is None
