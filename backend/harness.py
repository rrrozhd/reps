"""Tiny check/matcher helpers shared by every drill's test suite.

A "test" is a plain function ``t(Cls) -> list[Check]`` where each
``Check`` is a ``(label, expected, actual)`` tuple. The function builds a
fresh instance of the user's class, drives it, and captures real return
values into the tuples. The runner compares ``expected`` against
``actual`` with :func:`matches` (so a test can naturally reference an id
it got back earlier in the same scenario).
"""


class _Any:
    """Matches anything — use when a call must simply not raise."""

    def match(self, actual):
        return True

    def __repr__(self):
        return "ANY"


ANY = _Any()


class Pred:
    """Matches when ``fn(actual)`` is truthy. ``desc`` is shown in results."""

    def __init__(self, fn, desc):
        self.fn = fn
        self.desc = desc

    def match(self, actual):
        try:
            return bool(self.fn(actual))
        except Exception:
            return False

    def __repr__(self):
        return self.desc


def matches(expected, actual):
    if isinstance(expected, (_Any, Pred)):
        return expected.match(actual)
    return expected == actual


def show(v):
    return repr(v)
