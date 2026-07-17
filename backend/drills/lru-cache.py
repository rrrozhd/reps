"""Drill C — LRU Cache with TTL and historical reads (the log-not-scalar trap)."""

from harness import ANY, Pred  # noqa: F401

SLUG = "lru-cache"
TITLE = "LRU Cache with TTL"
DIFFICULTY = "CodeSignal-style ICA archetype · 4 levels"
ENTRYPOINT = "LRUCache"

MARKDOWN = r"""
# LRU Cache with TTL

The cache is built with a fixed **capacity** (`LRUCache(capacity)` — a positive
int). Timestamps arrive **non-decreasing**; keys and values are strings.
**Recency is by operation order**, not by timestamp value (two ops may share a
timestamp). Both `get` and `put` count as *using* a key. When an insert of a
**new** key would exceed capacity, the **least-recently-used** live entry is
evicted first.

---

## Level 1 — get / put with eviction

- **`put(ts, key, value) -> None`** — insert or update `key`. A `put` makes the
  key the **most-recently-used**. If `key` is new and the cache is already full,
  first **evict the least-recently-used** live entry. Overwriting an existing key
  updates its value, refreshes recency, and (see L3) clears any TTL.
- **`get(ts, key) -> str | None`** — the current value, or `None` if the key is
  missing / evicted / expired. A **successful** `get` refreshes recency (the key
  becomes most-recently-used). A miss changes nothing.

## Level 2 — Stats

- **`keys(ts) -> list[str]`** — every key **alive at `ts`**, sorted ascending.
- **`stats(ts) -> dict`** — `{"size": <#live at ts>, "hits": <int>, "misses":
  <int>}`. `hits`/`misses` are **cumulative** counters over every current-time
  `get`: a hit when it returned a value, a miss when it returned `None`.
  `keys`, `stats`, and the historical read (L4) never touch these counters.

## Level 3 — TTL & lazy expiry

- **`put_with_ttl(ts, key, value, ttl) -> None`** — like `put` but the entry
  **expires at `ts + ttl`**; a read **at or after** that instant sees it as gone.
  Expiry is **lazy** — evaluated against the current timestamp, not on a timer.
  An expired entry frees its capacity slot the next time any op touches the
  cache, so it will **not** be the one evicted. A later plain `put` clears the
  TTL (permanent); a later `put_with_ttl` resets it.

## Level 4 — Historical reads

- **`get(ts, key, at_timestamp) -> str | None`** — the value **as of
  `at_timestamp`**, honoring whatever the key's state was then: `None` if it
  hadn't been inserted yet, had already been **evicted**, or had **expired** by
  `at_timestamp`. This read is **pure** — no recency change, no hit/miss change.
  `at_timestamp <= ts`.

---

> **Read all four levels first.** L4 kills the scalar `value` map: a key's
> current value can be *gone* while its value at a past instant was something
> real. Store a per-key **append log** of `(ts, value, expiry_at)` records —
> and log a **tombstone** on every eviction. Then every read, current or
> historical, is one binary search into that log.
"""

STARTER = '''\
import bisect
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        pass

    # ---- Level 1 ----
    def put(self, ts, key, value):
        pass

    def get(self, ts, key, at_timestamp=None):
        pass

    # ---- Level 2 ----
    def keys(self, ts):
        pass

    def stats(self, ts):
        pass

    # ---- Level 3 ----
    def put_with_ttl(self, ts, key, value, ttl):
        pass
'''

REFERENCE = '''\
import bisect
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        # live set, ordered by recency: front == LRU, back == MRU
        self.live = OrderedDict()          # key -> (value, expiry_at_or_None)
        # per-key append log: (ts, value_or_None, expiry_at_or_None)
        # value None == tombstone (eviction); records land in ts order.
        self.log = {}
        self.hits = 0
        self.misses = 0

    # ---- housekeeping ----
    def _sweep(self, ts):
        # Lazy expiry: drop entries whose TTL elapsed as of ts. No log record is
        # needed — the record's expiry_at already encodes expiry for history.
        for key, (_v, exp) in list(self.live.items()):
            if exp is not None and exp <= ts:
                del self.live[key]

    def _record(self, ts, key, value, expiry):
        self.log.setdefault(key, []).append((ts, value, expiry))

    def _insert(self, ts, key, value, expiry):
        self._sweep(ts)
        if key in self.live:                       # update: no eviction
            self.live[key] = (value, expiry)
            self.live.move_to_end(key)
        else:
            if len(self.live) >= self.capacity:
                evicted, _ = self.live.popitem(last=False)   # drop LRU
                self._record(ts, evicted, None, None)        # eviction tombstone
            self.live[key] = (value, expiry)
        self._record(ts, key, value, expiry)

    def _value_at(self, key, at):
        recs = self.log.get(key)
        if not recs:
            return None
        i = bisect.bisect_right([r[0] for r in recs], at) - 1
        if i < 0:
            return None
        _w, value, expiry = recs[i]
        if value is None:                          # tombstone (evicted)
            return None
        if expiry is not None and at >= expiry:    # expired as of `at`
            return None
        return value

    # ---- Level 1 ----
    def put(self, ts, key, value):
        self._insert(ts, key, value, None)

    def get(self, ts, key, at_timestamp=None):
        if at_timestamp is not None:               # historical read — pure
            return self._value_at(key, at_timestamp)
        self._sweep(ts)
        if key in self.live:
            value, _exp = self.live[key]
            self.live.move_to_end(key)             # a read refreshes recency
            self.hits += 1
            return value
        self.misses += 1
        return None

    # ---- Level 2 ----
    def keys(self, ts):
        self._sweep(ts)
        return sorted(self.live.keys())

    def stats(self, ts):
        self._sweep(ts)
        return {"size": len(self.live), "hits": self.hits, "misses": self.misses}

    # ---- Level 3 ----
    def put_with_ttl(self, ts, key, value, ttl):
        self._insert(ts, key, value, ts + ttl)
'''


# ------------------------------------------------------------------ Level 1
def l1_put_get(C):
    c = C(2)
    out = [("get missing -> None", None, c.get(1, "a"))]
    out.append(("put a -> None", None, c.put(1, "a", "x")))
    out.append(("get a -> x", "x", c.get(2, "a")))
    out.append(("put a again -> None", None, c.put(3, "a", "y")))
    out.append(("get a -> y (updated in place)", "y", c.get(4, "a")))
    return out


def l1_eviction(C):
    c = C(2)
    c.put(1, "a", "1")
    c.put(2, "b", "2")
    c.put(3, "c", "3")            # full -> evict LRU (a)
    return [
        ("a evicted -> None", None, c.get(4, "a")),
        ("b alive -> 2", "2", c.get(5, "b")),
        ("c alive -> 3", "3", c.get(6, "c")),
    ]


def l1_get_refreshes_recency(C):
    c = C(2)
    c.put(1, "a", "1")
    c.put(2, "b", "2")
    c.get(3, "a")                 # a becomes MRU, b is now LRU
    c.put(4, "c", "3")            # evicts b, NOT a
    return [
        ("b evicted -> None", None, c.get(5, "b")),
        ("a survived (recently read) -> 1", "1", c.get(6, "a")),
        ("c alive -> 3", "3", c.get(7, "c")),
    ]


def l1_overwrite_refreshes_recency(C):
    c = C(2)
    c.put(1, "a", "1")
    c.put(2, "b", "2")
    c.put(3, "a", "10")          # overwrite -> a MRU, b LRU
    c.put(4, "c", "3")           # evicts b
    return [
        ("b evicted -> None", None, c.get(5, "b")),
        ("a survived, updated -> 10", "10", c.get(6, "a")),
        ("c alive -> 3", "3", c.get(7, "c")),
    ]


# ------------------------------------------------------------------ Level 2
def l2_stats_hits_misses(C):
    c = C(2)
    c.put(1, "a", "x")
    out = [
        ("get a -> x (hit)", "x", c.get(2, "a")),
        ("get z -> None (miss)", None, c.get(3, "z")),
        ("get a -> x (hit)", "x", c.get(4, "a")),
    ]
    out.append(("stats -> size1 hits2 misses1",
                {"size": 1, "hits": 2, "misses": 1}, c.stats(5)))
    return out


def l2_keys_sorted(C):
    c = C(3)
    c.put(1, "banana", "1")
    c.put(2, "apple", "2")
    c.put(3, "cherry", "3")
    return [
        ("keys sorted ascending",
         ["apple", "banana", "cherry"], c.keys(4)),
    ]


def l2_keys_excludes_evicted(C):
    c = C(2)
    c.put(1, "b", "1")
    c.put(2, "a", "2")
    c.put(3, "c", "3")           # evicts LRU (b)
    return [
        ("keys exclude evicted -> [a, c]", ["a", "c"], c.keys(4)),
        ("stats size reflects eviction -> 2",
         {"size": 2, "hits": 0, "misses": 0}, c.stats(5)),
    ]


# ------------------------------------------------------------------ Level 3
def l3_ttl_expiry(C):
    c = C(2)
    c.put_with_ttl(1, "a", "x", 100)     # expires at 101
    return [
        ("get before expiry -> x", "x", c.get(50, "a")),
        ("get at expiry instant -> None", None, c.get(101, "a")),
        ("get after expiry -> None", None, c.get(200, "a")),
        ("keys after expiry -> []", [], c.keys(200)),
    ]


def l3_put_clears_ttl(C):
    c = C(2)
    c.put_with_ttl(1, "a", "x", 100)     # would expire at 101
    c.put(50, "a", "y")                  # plain put -> permanent
    return [
        ("get long after -> y (permanent)", "y", c.get(1000, "a")),
        ("keys long after -> [a]", ["a"], c.keys(1001)),
    ]


def l3_ttl_reset(C):
    c = C(2)
    c.put_with_ttl(1, "a", "x", 100)     # expires at 101
    c.put_with_ttl(50, "a", "y", 100)    # resets: expires at 150
    return [
        ("get at 120 -> y", "y", c.get(120, "a")),
        ("get at 150 (new expiry) -> None", None, c.get(150, "a")),
    ]


def l3_expiry_frees_slot(C):
    c = C(2)
    c.put(1, "a", "a")
    c.put_with_ttl(2, "b", "b", 10)      # b expires at 12
    c.put(20, "c", "c")                  # lazy sweep drops b first; a NOT evicted
    return [
        ("a survived (expired b freed the slot) -> a", "a", c.get(21, "a")),
        ("b expired -> None", None, c.get(21, "b")),
        ("c present -> c", "c", c.get(21, "c")),
    ]


# ------------------------------------------------------------------ Level 4
def l4_history_evictions(C):
    c = C(2)
    c.put(10, "A", "a1")
    c.put(20, "B", "b1")
    c.get(25, "A")                # A -> MRU, B -> LRU
    c.put(30, "C", "c1")          # evicts B (LRU) at ts 30
    c.put(40, "A", "a2")          # overwrite A in place
    return [
        ("A as-of 5 (pre-create) -> None", None, c.get(100, "A", 5)),
        ("A as-of 10 -> a1", "a1", c.get(100, "A", 10)),
        ("A as-of 39 (pre-overwrite) -> a1", "a1", c.get(100, "A", 39)),
        ("A as-of 40 -> a2", "a2", c.get(100, "A", 40)),
        ("A current -> a2", "a2", c.get(100, "A")),
        ("B as-of 20 -> b1", "b1", c.get(100, "B", 20)),
        ("B as-of 29 (pre-evict) -> b1", "b1", c.get(100, "B", 29)),
        ("B as-of 30 (evicted this ts) -> None", None, c.get(100, "B", 30)),
        ("B as-of 50 -> None", None, c.get(100, "B", 50)),
        ("B current (evicted) -> None", None, c.get(100, "B")),
    ]


def l4_reinsert(C):
    c = C(1)
    c.put(10, "A", "a1")
    c.put(20, "B", "b1")          # evicts A at 20
    c.put(30, "A", "a2")          # evicts B at 30, reinserts A
    return [
        ("A as-of 10 -> a1", "a1", c.get(100, "A", 10)),
        ("A as-of 15 -> a1", "a1", c.get(100, "A", 15)),
        ("A as-of 20 (evicted) -> None", None, c.get(100, "A", 20)),
        ("A as-of 25 -> None", None, c.get(100, "A", 25)),
        ("A as-of 30 (reinserted) -> a2", "a2", c.get(100, "A", 30)),
        ("A current -> a2", "a2", c.get(100, "A")),
        ("B as-of 20 -> b1", "b1", c.get(100, "B", 20)),
        ("B as-of 30 (evicted) -> None", None, c.get(100, "B", 30)),
        ("B current -> None", None, c.get(100, "B")),
    ]


def l4_history_ttl(C):
    c = C(3)
    c.put_with_ttl(10, "X", "x1", 100)   # alive [10, 110)
    c.put(20, "Y", "y1")
    return [
        ("X as-of 50 -> x1", "x1", c.get(1000, "X", 50)),
        ("X as-of 109 -> x1", "x1", c.get(1000, "X", 109)),
        ("X as-of 110 (expiry boundary) -> None", None, c.get(1000, "X", 110)),
        ("X as-of 200 -> None", None, c.get(1000, "X", 200)),
        ("X current (expired) -> None", None, c.get(1000, "X")),
        ("Y as-of 5 (pre-create) -> None", None, c.get(1000, "Y", 5)),
        ("Y as-of 20 -> y1", "y1", c.get(1000, "Y", 20)),
        ("Y current -> y1", "y1", c.get(1000, "Y")),
    ]


LEVELS = [
    {"name": "Level 1 — get / put with eviction",
     "tests": [l1_put_get, l1_eviction,
               l1_get_refreshes_recency, l1_overwrite_refreshes_recency]},
    {"name": "Level 2 — Stats",
     "tests": [l2_stats_hits_misses, l2_keys_sorted, l2_keys_excludes_evicted]},
    {"name": "Level 3 — TTL & lazy expiry",
     "tests": [l3_ttl_expiry, l3_put_clears_ttl, l3_ttl_reset, l3_expiry_frees_slot]},
    {"name": "Level 4 — Historical reads",
     "tests": [l4_history_evictions, l4_reinsert, l4_history_ttl]},
]
