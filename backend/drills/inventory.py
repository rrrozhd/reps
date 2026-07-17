"""Drill — Inventory with expiring reservations (CodeSignal-style ICA archetype)."""

from harness import ANY, Pred  # noqa: F401  (available to test authors)

SLUG = "inventory"
TITLE = "Inventory with Expiring Reservations"
DIFFICULTY = "hard · 4 levels"
ENTRYPOINT = "Inventory"

MARKDOWN = r"""
# Inventory with Expiring Reservations

Timestamps arrive **non-decreasing** (milliseconds). Item ids are strings.
Quantities, ttls and `n` are **positive integers**. A *reservation* holds units
of an item for a limited time and then silently gives them back. Design the
state object once — the last level makes a scalar "available" counter useless.

---

## Level 1 — Stock & reservations

- **`add_stock(ts, item, qty) -> None`** — add `qty` units to `item` (creating
  the item if new). Stock only ever grows.
- **`available(ts, item) -> int`** — units of `item` free to reserve **right
  now**: total stock minus the quantity currently held by live reservations.
  An item that was never stocked returns `0` (never `None`).
- **`reserve(ts, item, qty, ttl) -> bool`** — if at least `qty` units are
  available at `ts`, place a hold on `qty` units for `ttl` ms and return `True`;
  otherwise reserve nothing and return `False`. A hold placed at `ts` is live for
  `[ts, ts + ttl)`. Reserving an unknown item, or more than is available, is
  `False`.

## Level 2 — Most-reserved items

- **`top_reserved(ts, n) -> list[str]`** — the top `n` items by **currently-held
  quantity** (sum of all live holds on the item), formatted `"item(qty)"`, sorted
  by held quantity **descending**, ties broken by `item` **ascending**. Only
  items with at least one live hold appear (an item at `0` held is omitted).
  Fewer than `n` qualifying items → return all of them.

## Level 3 — Reservations expire

- Holds **expire lazily**: a hold placed at `t0` for `ttl` releases its units the
  instant the clock reaches `t0 + ttl`. Expiry is evaluated against the current
  timestamp **before every operation** — a read **at or after** `t0 + ttl` sees
  those units as free again, and a fresh `reserve` may reuse the freed capacity.
  (No method is added; this sharpens `available`, `reserve` and `top_reserved`.)

## Level 4 — Availability as-of a past time

- **`available(ts, item, at_timestamp) -> int`** — units of `item` that were free
  **as of `at_timestamp`**, honoring exactly which stock existed and which holds
  were live at that instant. `at_timestamp <= ts`. A hold placed at `t0` for
  `ttl` counted against availability for `[t0, t0 + ttl)` and not a millisecond
  outside it. Returns `0` if nothing was stocked yet at that time.

---

> **Read all four levels before writing one line.** L4 asks what was available at
> an *arbitrary past instant*, so availability cannot be a running `int` — keep an
> **append-only log**: stock additions as `(ts, qty)` and every successful
> reservation as `(start, qty, expiry)`. Then availability at any time (now or
> then) is just: stock added by that time minus the holds live at that time.
"""

STARTER = '''\
class Inventory:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def add_stock(self, ts, item, qty):
        pass

    def available(self, ts, item, at_timestamp=None):
        pass

    def reserve(self, ts, item, qty, ttl):
        pass

    # ---- Level 2 ----
    def top_reserved(self, ts, n):
        pass
'''

REFERENCE = '''\
class Inventory:
    def __init__(self):
        # item -> [(ts, qty)] stock additions, appended in non-decreasing ts
        self.stock = {}
        # item -> [(start, qty, expiry)] successful reservations (append-only)
        self.holds = {}

    def _stock_at(self, item, at):
        total = 0
        for t, q in self.stock.get(item, ()):
            if t <= at:
                total += q
            else:
                break                       # additions are ts-ordered
        return total

    def _held_at(self, item, at):
        held = 0
        for start, q, expiry in self.holds.get(item, ()):
            if start <= at < expiry:        # hold live for [start, expiry)
                held += q
        return held

    def _available_at(self, item, at):
        return self._stock_at(item, at) - self._held_at(item, at)

    # ---- Level 1 ----
    def add_stock(self, ts, item, qty):
        self.stock.setdefault(item, []).append((ts, qty))

    def available(self, ts, item, at_timestamp=None):
        at = ts if at_timestamp is None else at_timestamp
        return self._available_at(item, at)

    def reserve(self, ts, item, qty, ttl):
        if qty <= self._available_at(item, ts):
            self.holds.setdefault(item, []).append((ts, qty, ts + ttl))
            return True
        return False

    # ---- Level 2 ----
    def top_reserved(self, ts, n):
        ranked = []
        for item in set(self.stock) | set(self.holds):
            held = self._held_at(item, ts)
            if held > 0:
                ranked.append((item, held))
        ranked.sort(key=lambda kv: (-kv[1], kv[0]))
        return [f"{item}({held})" for item, held in ranked[:n]]
'''


# ------------------------------------------------------------------ Level 1
def l1_add_available(C):
    inv = C()
    out = [("available unknown item -> 0", 0, inv.available(1, "widget"))]
    inv.add_stock(1, "widget", 10)
    out.append(("available after add -> 10", 10, inv.available(2, "widget")))
    inv.add_stock(3, "widget", 5)
    out.append(("available after second add -> 15", 15, inv.available(4, "widget")))
    return out


def l1_reserve(C):
    inv = C()
    inv.add_stock(1, "A", 10)
    out = []
    out.append(("reserve 4 -> True", True, inv.reserve(2, "A", 4, 100)))
    out.append(("available drops to 6", 6, inv.available(3, "A")))
    out.append(("reserve 10 (too many) -> False", False, inv.reserve(4, "A", 10, 100)))
    out.append(("available unchanged -> 6", 6, inv.available(5, "A")))
    out.append(("reserve exactly 6 -> True", True, inv.reserve(6, "A", 6, 100)))
    out.append(("available now 0", 0, inv.available(7, "A")))
    out.append(("reserve when nothing free -> False", False, inv.reserve(8, "A", 1, 100)))
    out.append(("reserve unknown item -> False", False, inv.reserve(9, "Z", 1, 100)))
    return out


# ------------------------------------------------------------------ Level 2
def l2_top_reserved(C):
    inv = C()
    for item in ("A", "B", "C"):
        inv.add_stock(1, item, 100)
    inv.reserve(2, "A", 30, 1000)      # held A = 30
    inv.reserve(3, "B", 50, 1000)      # held B = 50
    inv.reserve(4, "C", 30, 1000)      # held C = 30 (ties A on qty)
    return [
        ("top 2 -> [B(50), A(30)]", ["B(50)", "A(30)"], inv.top_reserved(5, 2)),
        ("top 10 -> all, A before C on tie",
         ["B(50)", "A(30)", "C(30)"], inv.top_reserved(5, 10)),
    ]


def l2_stacks_and_excludes_unheld(C):
    inv = C()
    inv.add_stock(1, "A", 100)
    inv.add_stock(1, "B", 100)         # B stocked but never reserved
    inv.reserve(2, "A", 10, 1000)
    inv.reserve(3, "A", 5, 1000)       # two live holds on A stack -> 15
    return [
        ("held stacks; B (0 held) omitted -> [A(15)]",
         ["A(15)"], inv.top_reserved(4, 5)),
    ]


# ------------------------------------------------------------------ Level 3
def l3_expiry_releases(C):
    inv = C()
    inv.add_stock(1, "A", 10)
    inv.reserve(2, "A", 6, 100)        # hold live [2, 102)
    return [
        ("before expiry -> 4", 4, inv.available(50, "A")),
        ("at expiry instant -> 10", 10, inv.available(102, "A")),
        ("after expiry -> 10", 10, inv.available(200, "A")),
    ]


def l3_expiry_frees_capacity(C):
    inv = C()
    inv.add_stock(1, "A", 10)
    inv.reserve(2, "A", 8, 100)        # hold live [2, 102), only 2 free
    out = []
    out.append(("reserve 5 while held -> False", False, inv.reserve(3, "A", 5, 100)))
    out.append(("reserve 5 after expiry -> True", True, inv.reserve(150, "A", 5, 100)))
    out.append(("available after re-reserve -> 5", 5, inv.available(151, "A")))
    return out


def l3_top_reserved_drops_expired(C):
    inv = C()
    inv.add_stock(1, "A", 100)
    inv.add_stock(1, "B", 100)
    inv.reserve(2, "A", 30, 50)        # hold live [2, 52)
    inv.reserve(3, "B", 20, 1000)      # hold live [3, 1003)
    return [
        ("both live -> [A(30), B(20)]", ["A(30)", "B(20)"], inv.top_reserved(10, 5)),
        ("after A expires -> [B(20)]", ["B(20)"], inv.top_reserved(60, 5)),
    ]


# ------------------------------------------------------------------ Level 4
def l4_as_of_stock_history(C):
    inv = C()
    inv.add_stock(10, "A", 100)
    inv.add_stock(20, "A", 50)
    return [
        ("as-of before any stock -> 0", 0, inv.available(100, "A", 5)),
        ("as-of at first add -> 100", 100, inv.available(100, "A", 10)),
        ("as-of between adds -> 100", 100, inv.available(100, "A", 15)),
        ("as-of at second add -> 150", 150, inv.available(100, "A", 20)),
        ("current -> 150", 150, inv.available(100, "A")),
    ]


def l4_as_of_reservation_window(C):
    inv = C()
    inv.add_stock(1, "A", 10)
    inv.reserve(5, "A", 4, 100)        # hold live [5, 105)
    return [
        ("as-of before hold start -> 10", 10, inv.available(500, "A", 4)),
        ("as-of at hold start -> 6", 6, inv.available(500, "A", 5)),
        ("as-of inside hold -> 6", 6, inv.available(500, "A", 50)),
        ("as-of just before expiry -> 6", 6, inv.available(500, "A", 104)),
        ("as-of at expiry instant -> 10", 10, inv.available(500, "A", 105)),
        ("as-of after expiry -> 10", 10, inv.available(500, "A", 200)),
    ]


def l4_as_of_overlapping_holds(C):
    inv = C()
    inv.add_stock(1, "A", 20)
    inv.reserve(10, "A", 5, 100)       # hold live [10, 110)
    inv.reserve(30, "A", 8, 20)        # hold live [30, 50)
    return [
        ("as-of 5 (no holds) -> 20", 20, inv.available(200, "A", 5)),
        ("as-of 15 (first hold) -> 15", 15, inv.available(200, "A", 15)),
        ("as-of 35 (both holds) -> 7", 7, inv.available(200, "A", 35)),
        ("as-of 50 (second expired) -> 15", 15, inv.available(200, "A", 50)),
        ("as-of 110 (both expired) -> 20", 20, inv.available(200, "A", 110)),
        ("current -> 20", 20, inv.available(200, "A")),
    ]


LEVELS = [
    {"name": "Level 1 — Stock & reservations",
     "tests": [l1_add_available, l1_reserve]},
    {"name": "Level 2 — Most-reserved items",
     "tests": [l2_top_reserved, l2_stacks_and_excludes_unheld]},
    {"name": "Level 3 — Reservations expire",
     "tests": [l3_expiry_releases, l3_expiry_frees_capacity,
               l3_top_reserved_drops_expired]},
    {"name": "Level 4 — Availability as-of a past time",
     "tests": [l4_as_of_stock_history, l4_as_of_reservation_window,
               l4_as_of_overlapping_holds]},
]
