"""Drill B — In-Memory Key-Value store with TTL (mirrors the banking machine)."""

from harness import ANY, Pred  # noqa: F401

SLUG = "kvstore"
TITLE = "Key-Value Store with TTL"
DIFFICULTY = "CodeSignal-style ICA archetype · 4 levels"
ENTRYPOINT = "KVStore"

MARKDOWN = r"""
# In-Memory Key-Value Store with TTL

Timestamps arrive **non-decreasing** (milliseconds). Keys and values are
strings. This is the same machine as the banking drill: **lazy expiry** is the
cashback engine, and **historical reads** are `get_balance`.

---

## Level 1 — Basic ops

- **`set(ts, key, value) -> None`** — set (or overwrite) `key`. Overwriting with
  a plain `set` makes the key **permanent** (clears any TTL).
- **`get(ts, key) -> str | None`** — current value, or `None` if the key is
  missing or expired.
- **`delete(ts, key) -> bool`** — `True` if the key existed (and was alive),
  else `False`.

## Level 2 — Prefix scan

- **`scan_prefix(ts, prefix) -> list[str]`** — every key that starts with
  `prefix` and is **alive at `ts`**, sorted ascending. (`prefix=""` → all live
  keys.)

## Level 3 — TTL

- **`set_with_ttl(ts, key, value, ttl) -> None`** — set `key` with a
  time-to-live of `ttl` ms. It expires at `ts + ttl`; a read **at or after**
  that instant sees it as gone. Expiry is **lazy** — evaluated at read time
  against the current timestamp. A later `set`/`set_with_ttl` resets it.

## Level 4 — Historical reads

- **`get(ts, key, at_timestamp) -> str | None`** — the value **as of
  `at_timestamp`**, honoring whatever TTL/existence was in effect at that
  moment. `None` if the key wasn't alive then. `at_timestamp <= ts`.

---

> **Read all four levels first.** L4 forces per-key history: store a **log** of
> `(write_ts, value, expiry_at)` records (plus tombstones for deletes). Every
> read — current or historical — is one binary search into that log.
"""

STARTER = '''\
import bisect


class KVStore:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def set(self, ts, key, value):
        pass

    def get(self, ts, key, at_timestamp=None):
        pass

    def delete(self, ts, key):
        pass

    # ---- Level 2 ----
    def scan_prefix(self, ts, prefix):
        pass

    # ---- Level 3 ----
    def set_with_ttl(self, ts, key, value, ttl):
        pass
'''

REFERENCE = '''\
import bisect


class KVStore:
    def __init__(self):
        # key -> [(write_ts, value_or_None, expiry_at_or_None)]
        # value None == tombstone (delete); records are appended in ts order.
        self.log = {}

    def _active(self, key, at):
        recs = self.log.get(key)
        if not recs:
            return None
        ts = [r[0] for r in recs]
        i = bisect.bisect_right(ts, at) - 1
        if i < 0:
            return None
        _w, value, expiry = recs[i]
        if value is None:                 # tombstone
            return None
        if expiry is not None and at >= expiry:
            return None
        return value

    # ---- Level 1 ----
    def set(self, ts, key, value):
        self.log.setdefault(key, []).append((ts, value, None))

    def get(self, ts, key, at_timestamp=None):
        return self._active(key, ts if at_timestamp is None else at_timestamp)

    def delete(self, ts, key):
        alive = self._active(key, ts) is not None
        self.log.setdefault(key, []).append((ts, None, None))
        return alive

    # ---- Level 2 ----
    def scan_prefix(self, ts, prefix):
        out = [k for k in self.log
               if k.startswith(prefix) and self._active(k, ts) is not None]
        return sorted(out)

    # ---- Level 3 ----
    def set_with_ttl(self, ts, key, value, ttl):
        self.log.setdefault(key, []).append((ts, value, ts + ttl))
'''


# ------------------------------------------------------------------ Level 1
def l1_set_get(C):
    kv = C()
    out = [("get missing -> None", None, kv.get(1, "a"))]
    kv.set(1, "a", "hello")
    out.append(("get a -> hello", "hello", kv.get(2, "a")))
    kv.set(3, "a", "world")
    out.append(("get a after overwrite -> world", "world", kv.get(4, "a")))
    out.append(("delete a -> True", True, kv.delete(5, "a")))
    out.append(("get a after delete -> None", None, kv.get(6, "a")))
    out.append(("delete a again -> False", False, kv.delete(7, "a")))
    return out


# ------------------------------------------------------------------ Level 2
def l2_scan(C):
    kv = C()
    kv.set(1, "user:1", "a")
    kv.set(1, "user:2", "b")
    kv.set(1, "admin:1", "c")
    return [
        ("scan user: -> sorted", ["user:1", "user:2"], kv.scan_prefix(2, "user:")),
        ("scan '' -> all sorted", ["admin:1", "user:1", "user:2"], kv.scan_prefix(2, "")),
        ("scan no match -> []", [], kv.scan_prefix(2, "zzz")),
    ]


def l2_scan_excludes_deleted(C):
    kv = C()
    kv.set(1, "k1", "a")
    kv.set(1, "k2", "b")
    kv.delete(2, "k1")
    return [("scan excludes deleted -> [k2]", ["k2"], kv.scan_prefix(3, "k"))]


# ------------------------------------------------------------------ Level 3
def l3_ttl_expiry(C):
    kv = C()
    kv.set_with_ttl(1, "a", "x", 100)       # expires at 101
    return [
        ("get before expiry -> x", "x", kv.get(50, "a")),
        ("get at expiry instant -> None", None, kv.get(101, "a")),
        ("get after expiry -> None", None, kv.get(200, "a")),
        ("scan after expiry excludes -> []", [], kv.scan_prefix(200, "a")),
    ]


def l3_set_clears_ttl(C):
    kv = C()
    kv.set_with_ttl(1, "a", "x", 100)       # would expire at 101
    kv.set(50, "a", "y")                    # plain set -> permanent
    return [
        ("get long after -> y (permanent)", "y", kv.get(1000, "a")),
        ("scan long after -> [a]", ["a"], kv.scan_prefix(1000, "a")),
    ]


def l3_ttl_reset(C):
    kv = C()
    kv.set_with_ttl(1, "a", "x", 100)       # expires at 101
    kv.set_with_ttl(50, "a", "y", 100)      # resets: expires at 150
    return [
        ("get at 120 -> y", "y", kv.get(120, "a")),
        ("get at 150 (new expiry) -> None", None, kv.get(150, "a")),
    ]


# ------------------------------------------------------------------ Level 4
def l4_history(C):
    kv = C()
    kv.set(10, "a", "v1")
    kv.set(20, "a", "v2")
    kv.delete(30, "a")
    kv.set(40, "a", "v3")
    return [
        ("as-of 5 (before first set) -> None", None, kv.get(100, "a", 5)),
        ("as-of 10 -> v1", "v1", kv.get(100, "a", 10)),
        ("as-of 15 -> v1", "v1", kv.get(100, "a", 15)),
        ("as-of 20 -> v2", "v2", kv.get(100, "a", 20)),
        ("as-of 35 (deleted) -> None", None, kv.get(100, "a", 35)),
        ("as-of 40 -> v3", "v3", kv.get(100, "a", 40)),
        ("current -> v3", "v3", kv.get(100, "a")),
    ]


def l4_history_ttl(C):
    kv = C()
    kv.set_with_ttl(10, "a", "x", 100)      # alive [10, 110)
    return [
        ("as-of 50 -> x", "x", kv.get(1000, "a", 50)),
        ("as-of 110 (expired) -> None", None, kv.get(1000, "a", 110)),
        ("as-of 200 -> None", None, kv.get(1000, "a", 200)),
        ("current (expired) -> None", None, kv.get(1000, "a")),
    ]


LEVELS = [
    {"name": "Level 1 — Basic ops",
     "tests": [l1_set_get]},
    {"name": "Level 2 — Prefix scan",
     "tests": [l2_scan, l2_scan_excludes_deleted]},
    {"name": "Level 3 — TTL",
     "tests": [l3_ttl_expiry, l3_set_clears_ttl, l3_ttl_reset]},
    {"name": "Level 4 — Historical reads",
     "tests": [l4_history, l4_history_ttl]},
]
