"""Drill C — Versioned object storage (S3-style version history)."""

from harness import ANY, Pred  # noqa: F401  (available to test authors)

SLUG = "versioned-bucket"
TITLE = "Versioned Object Store"
DIFFICULTY = "Ramp ICA archetype · 4 levels"
ENTRYPOINT = "Bucket"

MARKDOWN = r"""
# Versioned Object Store

A blob store that keeps **every** version of every object. Keys are strings,
sizes are **positive integers**. There is **one global version counter** for the
whole bucket: every successful `put` / `delete` / `restore` advances it by one,
and the int a `put` returns is that new **global** version number. Version ids
are therefore shared across keys — a single key's own versions are a
(non-contiguous) subset of the global sequence.

---

## Level 1 — Basic ops

- **`put(key, size) -> int`** — store `size` for `key`, creating a new version.
  Advances the global counter and returns the new version number. If `key`
  already exists this overwrites the *current* value (as a new version); older
  versions are retained.
- **`get(key) -> int | None`** — the **current** size of `key`, or `None` if the
  key never existed or its latest version is a deletion.
- **`delete(key) -> bool`** — `True` if `key` was live (and records a deletion
  marker as a new version), `False` if the key is missing or already deleted.
  A `False` delete does **not** advance the version counter.

## Level 2 — Listing

- **`list(prefix) -> list[str]`** — every key that is **currently live** (latest
  version is not a deletion) and starts with `prefix`, sorted ascending.
  (`prefix=""` → all live keys.)

## Level 3 — Restore

- **`restore(key, version) -> int | None`** — make an old version of `key`
  **current again** by writing its size as a brand-new version. Advances the
  global counter and returns the new version number. `version` must be a global
  version at which a `put` on **this key** occurred. Returns `None` if `key` is
  missing, or `version` is unknown, belongs to another key, or names a deletion
  (you cannot restore a delete marker).

## Level 4 — Historical reads

- **`get(key, at_version) -> int | None`** — the size of `key` **as of global
  version `at_version`**: the latest record for `key` whose version is
  `<= at_version`. `None` if that record is a deletion, or if `key` had no
  version at or before `at_version`. Honors puts, deletes and restores alike
  (a restore is just another put record). `at_version` may be any int `>= 0`.

---

> **Read all four levels before writing one line.** L4 (`get` at an arbitrary
> version) means the current size can't be a scalar — store a per-key
> **append-only log** of `(version, size | tombstone)` and binary-search it.
> Deletes are tombstones, restores are ordinary put records, and every read —
> current or historical — is one `bisect` into that log.
"""

STARTER = '''\
import bisect


class Bucket:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def put(self, key, size):
        pass

    def get(self, key, at_version=None):
        pass

    def delete(self, key):
        pass

    # ---- Level 2 ----
    def list(self, prefix):
        pass

    # ---- Level 3 ----
    def restore(self, key, version):
        pass
'''

REFERENCE = '''\
import bisect


class Bucket:
    def __init__(self):
        # key -> [(version, size_or_None)], appended in increasing version order.
        # size None == tombstone (a delete marker).
        self.log = {}
        self.version = 0          # single global, monotonic version counter

    def _record_at(self, key, at):
        recs = self.log.get(key)
        if not recs:
            return None
        versions = [r[0] for r in recs]
        i = bisect.bisect_right(versions, at) - 1
        if i < 0:
            return None
        return recs[i]            # (version, size_or_None)

    # ---- Level 1 ----
    def put(self, key, size):
        self.version += 1
        self.log.setdefault(key, []).append((self.version, size))
        return self.version

    def get(self, key, at_version=None):
        if at_version is None:
            recs = self.log.get(key)
            if not recs:
                return None
            return recs[-1][1]    # size, or None if latest is a tombstone
        rec = self._record_at(key, at_version)
        return None if rec is None else rec[1]

    def delete(self, key):
        recs = self.log.get(key)
        if not recs or recs[-1][1] is None:   # missing or already deleted
            return False
        self.version += 1
        recs.append((self.version, None))
        return True

    # ---- Level 2 ----
    def list(self, prefix):
        out = [k for k, recs in self.log.items()
               if recs[-1][1] is not None and k.startswith(prefix)]
        return sorted(out)

    # ---- Level 3 ----
    def restore(self, key, version):
        recs = self.log.get(key)
        if not recs:
            return None
        versions = [r[0] for r in recs]
        i = bisect.bisect_left(versions, version)
        if i >= len(recs) or recs[i][0] != version:
            return None           # unknown id / another key's / out of range
        size = recs[i][1]
        if size is None:          # cannot restore a delete marker
            return None
        self.version += 1
        recs.append((self.version, size))
        return self.version
'''


# ------------------------------------------------------------------ Level 1
def l1_put_get(C):
    b = C()
    out = [("get missing -> None", None, b.get("a"))]
    v1 = b.put("a", 10)
    out.append(("put a returns version 1", 1, v1))
    out.append(("get a -> 10", 10, b.get("a")))
    v2 = b.put("a", 20)
    out.append(("put a again returns version 2", 2, v2))
    out.append(("get a after overwrite -> 20", 20, b.get("a")))
    v3 = b.put("b", 5)
    out.append(("put b returns version 3 (global counter)", 3, v3))
    out.append(("get b -> 5", 5, b.get("b")))
    return out


def l1_delete(C):
    b = C()
    b.put("a", 10)
    return [
        ("delete a -> True", True, b.delete("a")),
        ("get a after delete -> None", None, b.get("a")),
        ("delete a again -> False", False, b.delete("a")),
        ("delete missing -> False", False, b.delete("zzz")),
    ]


def l1_reput_after_delete(C):
    b = C()
    b.put("a", 10)          # v1
    b.delete("a")           # v2 tombstone
    return [
        ("put after delete revives -> v3", 3, b.put("a", 99)),
        ("get a -> 99", 99, b.get("a")),
    ]


# ------------------------------------------------------------------ Level 2
def l2_list(C):
    b = C()
    b.put("user:1", 1)
    b.put("user:2", 2)
    b.put("admin:1", 3)
    return [
        ("list user: -> sorted", ["user:1", "user:2"], b.list("user:")),
        ("list '' -> all sorted", ["admin:1", "user:1", "user:2"], b.list("")),
        ("list no match -> []", [], b.list("zzz")),
    ]


def l2_list_excludes_deleted(C):
    b = C()
    b.put("k1", 1)
    b.put("k2", 2)
    b.delete("k1")
    return [("list excludes deleted -> [k2]", ["k2"], b.list("k"))]


# ------------------------------------------------------------------ Level 3
def l3_restore_basic(C):
    b = C()
    v1 = b.put("a", 10)     # v1
    b.put("a", 20)          # v2
    out = [("get a current -> 20", 20, b.get("a"))]
    v = b.restore("a", v1)  # restores size 10 as a NEW version v3
    out.append(("restore returns new version 3", 3, v))
    out.append(("get a after restore -> 10", 10, b.get("a")))
    out.append(("restore is additive (v2 still queryable) -> 20",
                20, b.get("a", 2)))
    return out


def l3_restore_after_delete(C):
    b = C()
    v1 = b.put("a", 10)     # v1
    b.delete("a")           # v2 tombstone
    out = [("get a after delete -> None", None, b.get("a"))]
    v = b.restore("a", v1)  # v3, size 10 -> revives the key
    out.append(("restore old put after delete -> v3", 3, v))
    out.append(("get a restored -> 10", 10, b.get("a")))
    out.append(("list includes restored -> [a]", ["a"], b.list("")))
    return out


def l3_restore_invalid(C):
    b = C()
    b.put("a", 10)          # v1  (a)
    b.delete("a")           # v2  (a, tombstone)
    b.put("b", 5)           # v3  (b)
    return [
        ("restore a delete-marker version -> None", None, b.restore("a", 2)),
        ("restore another key's version -> None", None, b.restore("a", 3)),
        ("restore unknown version -> None", None, b.restore("a", 99)),
        ("restore missing key -> None", None, b.restore("zzz", 1)),
    ]


# ------------------------------------------------------------------ Level 4
def l4_history(C):
    b = C()
    b.put("a", 10)          # v1
    b.put("a", 20)          # v2
    b.delete("a")           # v3 tombstone
    b.restore("a", 1)       # v4 -> size 10
    return [
        ("as-of v0 (before anything) -> None", None, b.get("a", 0)),
        ("as-of v1 -> 10", 10, b.get("a", 1)),
        ("as-of v2 -> 20", 20, b.get("a", 2)),
        ("as-of v3 (deleted) -> None", None, b.get("a", 3)),
        ("as-of v4 (restored) -> 10", 10, b.get("a", 4)),
        ("as-of far future -> 10", 10, b.get("a", 999)),
        ("current -> 10", 10, b.get("a")),
    ]


def l4_history_multikey(C):
    b = C()
    b.put("a", 10)          # v1
    b.put("b", 5)           # v2
    b.put("a", 20)          # v3  (a changes, b untouched)
    b.delete("b")           # v4
    return [
        ("a as-of v1 -> 10", 10, b.get("a", 1)),
        ("a as-of v2 (unchanged) -> 10", 10, b.get("a", 2)),
        ("a as-of v3 -> 20", 20, b.get("a", 3)),
        ("b as-of v1 (before b's put) -> None", None, b.get("b", 1)),
        ("b as-of v2 -> 5", 5, b.get("b", 2)),
        ("b as-of v3 (a moved, b still live) -> 5", 5, b.get("b", 3)),
        ("b as-of v4 (deleted) -> None", None, b.get("b", 4)),
        ("b current -> None", None, b.get("b")),
    ]


LEVELS = [
    {"name": "Level 1 — Basic ops",
     "tests": [l1_put_get, l1_delete, l1_reput_after_delete]},
    {"name": "Level 2 — Listing",
     "tests": [l2_list, l2_list_excludes_deleted]},
    {"name": "Level 3 — Restore",
     "tests": [l3_restore_basic, l3_restore_after_delete, l3_restore_invalid]},
    {"name": "Level 4 — Historical reads",
     "tests": [l4_history, l4_history_multikey]},
]
