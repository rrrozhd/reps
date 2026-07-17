"""Drill — In-Memory DB with nested transactions & versioned history."""

from harness import ANY, Pred  # noqa: F401  (available to test authors)

SLUG = "memory-db"
TITLE = "In-Memory DB with Transactions"
DIFFICULTY = "CodeSignal-style ICA archetype · 4 levels"
ENTRYPOINT = "Database"

MARKDOWN = r"""
# In-Memory Key-Value DB with Transactions

A single-threaded key-value store. Keys and values are strings. Design the state
object once — the last level makes a scalar `key -> value` map impossible.

---

## Level 1 — Basic ops

- **`set(key, value) -> None`** — set (or overwrite) `key` to `value`.
- **`get(key) -> str | None`** — current value of `key`, or `None` if the key is
  absent (never set, or deleted).
- **`delete(key) -> bool`** — `True` if the key was present (and is now removed),
  `False` if it was already absent.

## Level 2 — Value count

- **`count(value) -> int`** — how many keys currently hold exactly `value`. No
  match → `0`. Must reflect any writes buffered by open transactions (Level 3).

## Level 3 — Nested transactions

Writes inside a transaction **buffer** — they are visible to reads made from
inside that transaction (and to deeper nested ones), but do not touch the durable
store until committed all the way to the base.

- **`begin() -> None`** — open a new transaction. Transactions **nest**: a second
  `begin` opens a child of the first.
- **`commit() -> bool`** — commit the **innermost** open transaction. Its buffered
  writes fold into the enclosing transaction, or into the durable store if it was
  the outermost one. `True` if a transaction was open, else `False` (nothing to
  commit).
- **`rollback() -> bool`** — discard the **innermost** open transaction and all of
  its buffered writes; any enclosing transaction is untouched. `True` if a
  transaction was open, else `False`.

`get`, `delete`, and `count` all see the innermost buffered view. A `delete`
inside a transaction buffers a removal (later rolled back or committed like any
other write).

## Level 4 — Versioned history

Every write that lands in the **durable store** bumps a global version counter by
one — a top-level `set`/`delete`, or each buffered write applied when an outermost
transaction commits (applied in the order they were first written). Buffered
writes inside still-open transactions have **no** version yet.

- **`version() -> int`** — the current durable version (starts at `0`, before any
  durable write).
- **`get(key, at_version) -> str | None`** — the value of `key` **as of** that
  durable version: the latest durable write to `key` with version `<= at_version`,
  or `None` if the key had no live value then (never written yet, or its newest
  write at-or-before `at_version` was a delete). `0 <= at_version <= version()`.
  Historical reads see only the **durable** timeline — writes buffered in open
  transactions are invisible.

---

> **Read all four levels first.** L4 asks for a key's value *at an old version*
> after it has since been overwritten or deleted — a live `key -> value` map
> throws that away. Store an append-only **log** per key of
> `(version, value | tombstone)`; every read, current or historical, is one
> binary search. Transactions are a **stack of overlay dicts** over that base.
"""

STARTER = '''\
import bisect


class Database:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def set(self, key, value):
        pass

    def get(self, key, at_version=None):
        pass

    def delete(self, key):
        pass

    # ---- Level 2 ----
    def count(self, value):
        pass

    # ---- Level 3 ----
    def begin(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    # ---- Level 4 ----
    def version(self):
        pass
'''

REFERENCE = '''\
import bisect

_TOMB = object()          # tombstone sentinel: marks a delete


class Database:
    def __init__(self):
        # durable append-only history: key -> [(version, value_or__TOMB)]
        self.log = {}
        self.ver = 0
        # open transactions: stack of overlay dicts (key -> value_or__TOMB).
        # empty stack == no transaction; deeper index == more nested.
        self.stack = []

    # ---------------- helpers ----------------
    def _base_current(self, key):
        recs = self.log.get(key)
        if not recs:
            return None
        v = recs[-1][1]
        return None if v is _TOMB else v

    def _current(self, key):
        # innermost buffered view first, then the durable base
        for overlay in reversed(self.stack):
            if key in overlay:
                v = overlay[key]
                return None if v is _TOMB else v
        return self._base_current(key)

    def _effective_map(self):
        m = {}
        for key, recs in self.log.items():
            v = recs[-1][1]
            if v is not _TOMB:
                m[key] = v
        for overlay in self.stack:          # bottom-to-top: deeper wins
            for k, v in overlay.items():
                if v is _TOMB:
                    m.pop(k, None)
                else:
                    m[k] = v
        return m

    def _base_write(self, key, value):
        self.ver += 1
        self.log.setdefault(key, []).append((self.ver, value))

    # ---------------- Level 1 ----------------
    def set(self, key, value):
        if self.stack:
            self.stack[-1][key] = value
        else:
            self._base_write(key, value)

    def get(self, key, at_version=None):
        if at_version is None:
            return self._current(key)
        recs = self.log.get(key)            # durable timeline only
        if not recs:
            return None
        versions = [r[0] for r in recs]
        i = bisect.bisect_right(versions, at_version) - 1
        if i < 0:
            return None
        v = recs[i][1]
        return None if v is _TOMB else v

    def delete(self, key):
        existed = self._current(key) is not None
        if self.stack:
            self.stack[-1][key] = _TOMB
        elif existed:
            self._base_write(key, _TOMB)
        return existed

    # ---------------- Level 2 ----------------
    def count(self, value):
        return sum(1 for v in self._effective_map().values() if v == value)

    # ---------------- Level 3 ----------------
    def begin(self):
        self.stack.append({})

    def commit(self):
        if not self.stack:
            return False
        top = self.stack.pop()
        if self.stack:                      # fold into enclosing transaction
            self.stack[-1].update(top)
        else:                               # land in the durable store, in order
            for k, v in top.items():
                if v is _TOMB:
                    if self._base_current(k) is not None:
                        self._base_write(k, _TOMB)
                else:
                    self._base_write(k, v)
        return True

    def rollback(self):
        if not self.stack:
            return False
        self.stack.pop()
        return True

    # ---------------- Level 4 ----------------
    def version(self):
        return self.ver
'''


# ------------------------------------------------------------------ Level 1
def l1_set_get_delete(C):
    db = C()
    out = [("get missing -> None", None, db.get("a"))]
    db.set("a", "hello")
    out.append(("get a -> hello", "hello", db.get("a")))
    db.set("a", "world")
    out.append(("get a after overwrite -> world", "world", db.get("a")))
    out.append(("delete a -> True", True, db.delete("a")))
    out.append(("get a after delete -> None", None, db.get("a")))
    out.append(("delete a again -> False", False, db.delete("a")))
    out.append(("delete never-seen -> False", False, db.delete("zzz")))
    return out


# ------------------------------------------------------------------ Level 2
def l2_count_basic(C):
    db = C()
    db.set("a", "x")
    db.set("b", "x")
    db.set("c", "y")
    return [
        ("count x -> 2", 2, db.count("x")),
        ("count y -> 1", 1, db.count("y")),
        ("count absent -> 0", 0, db.count("z")),
    ]


def l2_count_after_change(C):
    db = C()
    db.set("a", "x")
    db.set("b", "x")
    db.set("c", "x")
    db.set("b", "y")          # b now y
    db.delete("c")            # c gone
    return [
        ("count x after overwrite+delete -> 1", 1, db.count("x")),
        ("count y -> 1", 1, db.count("y")),
    ]


# ------------------------------------------------------------------ Level 3
def l3_commit_basic(C):
    db = C()
    db.set("a", "0")
    db.begin()
    db.set("a", "1")
    out = [
        ("inside txn get a -> 1", "1", db.get("a")),
        ("version unchanged during txn -> 1", 1, db.version()),
    ]
    db.set("b", "9")
    out.append(("commit -> True", True, db.commit()))
    out.append(("after commit get a -> 1", "1", db.get("a")))
    out.append(("after commit get b -> 9", "9", db.get("b")))
    return out


def l3_rollback_basic(C):
    db = C()
    db.set("a", "0")
    db.begin()
    db.set("a", "1")
    db.set("b", "2")
    return [
        ("inside txn get a -> 1", "1", db.get("a")),
        ("rollback -> True", True, db.rollback()),
        ("after rollback get a -> 0", "0", db.get("a")),
        ("after rollback get b -> None", None, db.get("b")),
        ("commit with no txn -> False", False, db.commit()),
        ("rollback with no txn -> False", False, db.rollback()),
    ]


def l3_nested_rollback_inner(C):
    db = C()
    db.set("a", "0")
    db.begin()               # T1
    db.set("a", "1")
    db.begin()               # T2 (nested)
    db.set("a", "2")
    out = [("innermost get a -> 2", "2", db.get("a"))]
    out.append(("rollback T2 -> True", True, db.rollback()))
    out.append(("back in T1 get a -> 1", "1", db.get("a")))
    out.append(("commit T1 -> True", True, db.commit()))
    out.append(("durable get a -> 1", "1", db.get("a")))
    out.append(("version after base set + T1 commit -> 2", 2, db.version()))
    return out


def l3_nested_commit_merges_to_parent(C):
    db = C()
    db.begin()               # T1
    db.set("a", "1")
    db.begin()               # T2
    db.set("a", "2")
    db.set("b", "3")
    out = [("commit T2 -> True", True, db.commit())]   # folds into T1
    out.append(("still in T1, base untouched: version -> 0", 0, db.version()))
    out.append(("get a (T1 view) -> 2", "2", db.get("a")))
    out.append(("get b (T1 view) -> 3", "3", db.get("b")))
    out.append(("rollback T1 -> True", True, db.rollback()))
    out.append(("get a after discard -> None", None, db.get("a")))
    out.append(("get b after discard -> None", None, db.get("b")))
    out.append(("version still 0 (nothing durable)", 0, db.version()))
    return out


def l3_delete_and_count_in_txn(C):
    db = C()
    db.set("a", "x")
    db.set("b", "x")
    db.begin()
    out = [
        ("delete a in txn -> True", True, db.delete("a")),
        ("get a in txn -> None", None, db.get("a")),
        ("count x in txn -> 1", 1, db.count("x")),
    ]
    db.set("c", "x")                       # buffered write inside the txn
    out.append(("count x after set c=x -> 2", 2, db.count("x")))
    out.append(("rollback -> True", True, db.rollback()))
    out.append(("get a restored -> x", "x", db.get("a")))
    out.append(("count x restored -> 2", 2, db.count("x")))
    return out


# ------------------------------------------------------------------ Level 4
def l4_history_basic(C):
    db = C()
    db.set("a", "1")         # v1
    db.set("a", "2")         # v2
    db.set("b", "9")         # v3
    db.delete("a")           # v4 (tombstone)
    return [
        ("version -> 4", 4, db.version()),
        ("current get a -> None (deleted)", None, db.get("a")),
        ("as-of 0 -> None", None, db.get("a", 0)),
        ("as-of 1 -> 1", "1", db.get("a", 1)),
        ("as-of 2 -> 2", "2", db.get("a", 2)),
        ("as-of 3 (still 2) -> 2", "2", db.get("a", 3)),
        ("as-of 4 (tombstone) -> None", None, db.get("a", 4)),
        ("b as-of 2 (not yet) -> None", None, db.get("b", 2)),
        ("b as-of 3 -> 9", "9", db.get("b", 3)),
    ]


def l4_history_boundary(C):
    db = C()
    db.set("k", "first")     # v1
    db.set("k", "second")    # v2
    db.delete("k")           # v3
    db.set("k", "third")     # v4
    return [
        ("as-of 1 -> first", "first", db.get("k", 1)),
        ("as-of 2 -> second", "second", db.get("k", 2)),
        ("as-of 3 (just deleted) -> None", None, db.get("k", 3)),
        ("as-of 4 -> third", "third", db.get("k", 4)),
        ("current -> third", "third", db.get("k")),
    ]


def l4_history_through_commit(C):
    db = C()
    db.set("a", "1")         # v1
    db.begin()
    db.set("a", "2")         # buffered
    db.set("b", "5")         # buffered
    out = [
        ("version during txn -> 1", 1, db.version()),
        ("commit -> True", True, db.commit()),   # a->2 (v2), b->5 (v3)
        ("version after commit -> 3", 3, db.version()),
        ("a as-of 1 -> 1", "1", db.get("a", 1)),
        ("a as-of 2 -> 2", "2", db.get("a", 2)),
        ("b as-of 2 (before it landed) -> None", None, db.get("b", 2)),
        ("b as-of 3 -> 5", "5", db.get("b", 3)),
    ]
    return out


def l4_history_ignores_open_txn(C):
    db = C()
    db.set("a", "1")         # v1
    db.begin()
    db.set("c", "7")         # buffered, no version
    return [
        ("current get c -> 7 (buffered visible)", "7", db.get("c")),
        ("historical get c at current version -> None", None, db.get("c", db.version())),
        ("version still 1 (buffered not durable)", 1, db.version()),
    ]


LEVELS = [
    {"name": "Level 1 — Basic ops",
     "tests": [l1_set_get_delete]},
    {"name": "Level 2 — Value count",
     "tests": [l2_count_basic, l2_count_after_change]},
    {"name": "Level 3 — Nested transactions",
     "tests": [l3_commit_basic, l3_rollback_basic, l3_nested_rollback_inner,
               l3_nested_commit_merges_to_parent, l3_delete_and_count_in_txn]},
    {"name": "Level 4 — Versioned history",
     "tests": [l4_history_basic, l4_history_boundary, l4_history_through_commit,
               l4_history_ignores_open_txn]},
]
