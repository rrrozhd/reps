"""Drill — Sliding-window Rate Limiter (deque/log archetype)."""

from harness import ANY, Pred  # noqa: F401  (available to test authors)

SLUG = "rate-limiter"
TITLE = "Sliding-Window Rate Limiter"
DIFFICULTY = "CodeSignal-style ICA archetype · 4 levels"
ENTRYPOINT = "RateLimiter"

MARKDOWN = r"""
# Sliding-Window Rate Limiter

Requests arrive with **non-decreasing** timestamps (milliseconds). A limiter
admits at most `limit` requests to a single `client_id` within any **sliding
window** of `window` ms. The default window is **1000 ms** and the default
limit is **3**.

A request at `ts` is admitted when the number of **already-accepted** requests
for that client in the half-open interval `(ts - window, ts]` is **below** the
limit. An admitted request is recorded; a denied request is **not** recorded
(it never counts against the window).

---

## Level 1 — Fixed window + limit

- **`allow(ts, client_id) -> bool`** — `True` if the request is admitted (and
  recorded), `False` if it would exceed the limit within the current window.
  Old timestamps fall out of the window as time advances (lazy eviction), so a
  client that was maxed out becomes admittable again once its early requests
  age past `window`. Each `client_id` is tracked independently.

## Level 2 — Per-client limits

- **`set_limit(client_id, limit) -> None`** — override the limit for one
  client; other clients keep the default. Takes effect on subsequent `allow`
  calls (already-recorded timestamps are untouched). Raising the limit admits
  more; lowering it denies until the window drains below the new limit.

## Level 3 — Penalty block after repeated denials

- **`set_penalty(threshold, block_ms) -> None`** — arm a global penalty. When a
  client is denied **`threshold` times in a row** (a successful `allow` resets
  the streak), it is **blocked** until `deny_ts + block_ms`. While blocked,
  every `allow` returns `False` **regardless of the window** and does not
  record anything or extend the block. At the first `allow` with
  `ts >= block_until` the block clears, the streak resets, and the request is
  evaluated normally against the window.

## Level 4 — Historical count ("as-of")

- **`count(ts, client_id, at_timestamp) -> int`** — how many of the client's
  **accepted** requests were in the window `(at_timestamp - window,
  at_timestamp]`, evaluated **as of** `at_timestamp` (a possibly-past instant,
  `at_timestamp <= ts`). Unknown client → `0`. A request drops out of the count
  exactly when `at_timestamp == request_ts + window`.

---

> **Read all four levels first.** L1 tempts you to store a `deque` and
> `popleft()` timestamps that age out — but L4 asks how many requests were in
> the window at an **arbitrary past instant**, and those popped timestamps are
> gone. Store an **append-only log** of accepted timestamps per client; because
> timestamps are non-decreasing the log stays sorted, and every window count —
> live or historical — is two `bisect`s. Eviction is logical, never physical.
"""

STARTER = '''\
import bisect

DEFAULT_WINDOW = 1000
DEFAULT_LIMIT = 3


class RateLimiter:
    def __init__(self, window=DEFAULT_WINDOW, limit=DEFAULT_LIMIT):
        pass

    # ---- Level 1 ----
    def allow(self, ts, client_id):
        pass

    # ---- Level 2 ----
    def set_limit(self, client_id, limit):
        pass

    # ---- Level 3 ----
    def set_penalty(self, threshold, block_ms):
        pass

    # ---- Level 4 ----
    def count(self, ts, client_id, at_timestamp):
        pass
'''

REFERENCE = '''\
import bisect

DEFAULT_WINDOW = 1000
DEFAULT_LIMIT = 3


class RateLimiter:
    def __init__(self, window=DEFAULT_WINDOW, limit=DEFAULT_LIMIT):
        self.window = window
        self.limit = limit
        self.log = {}            # client_id -> append-only sorted [accepted ts]
        self.limits = {}         # client_id -> custom limit
        self.streak = {}         # client_id -> consecutive denial count
        self.block_until = {}    # client_id -> ts until which client is blocked
        self.pen_threshold = None
        self.pen_block = 0

    def _in_window(self, ts_list, at):
        # accepted requests in (at - window, at]  — two bisects, no popping
        hi = bisect.bisect_right(ts_list, at)
        lo = bisect.bisect_right(ts_list, at - self.window)
        return hi - lo

    def _limit_of(self, client_id):
        return self.limits.get(client_id, self.limit)

    # ---- Level 1 (+ Level 3 block) ----
    def allow(self, ts, client_id):
        bu = self.block_until.get(client_id)
        if bu is not None:
            if ts < bu:
                return False                 # still serving penalty
            self.block_until[client_id] = None
            self.streak[client_id] = 0       # block cleared

        ts_list = self.log.setdefault(client_id, [])
        if self._in_window(ts_list, ts) < self._limit_of(client_id):
            ts_list.append(ts)               # append-only; ts non-decreasing
            self.streak[client_id] = 0
            return True

        s = self.streak.get(client_id, 0) + 1
        self.streak[client_id] = s
        if self.pen_threshold is not None and s >= self.pen_threshold:
            self.block_until[client_id] = ts + self.pen_block
        return False

    # ---- Level 2 ----
    def set_limit(self, client_id, limit):
        self.limits[client_id] = limit

    # ---- Level 3 ----
    def set_penalty(self, threshold, block_ms):
        self.pen_threshold = threshold
        self.pen_block = block_ms

    # ---- Level 4 ----
    def count(self, ts, client_id, at_timestamp):
        ts_list = self.log.get(client_id)
        if not ts_list:
            return 0
        return self._in_window(ts_list, at_timestamp)
'''


# ------------------------------------------------------------------ Level 1
def l1_basic(C):
    rl = C()                                  # window 1000, limit 3
    return [
        ("allow @0 -> True", True, rl.allow(0, "a")),
        ("allow @100 -> True", True, rl.allow(100, "a")),
        ("allow @200 -> True", True, rl.allow(200, "a")),
        ("4th in window @300 -> False", False, rl.allow(300, "a")),
        ("@1050 (oldest aged out) -> True", True, rl.allow(1050, "a")),
    ]


def l1_independent_clients(C):
    rl = C()
    rl.allow(0, "a")
    rl.allow(1, "a")
    rl.allow(2, "a")
    return [
        ("a 4th in window -> False", False, rl.allow(3, "a")),
        ("b first request -> True", True, rl.allow(3, "b")),
        ("b second request -> True", True, rl.allow(4, "b")),
    ]


# ------------------------------------------------------------------ Level 2
def l2_set_limit_lower(C):
    rl = C()
    rl.set_limit("a", 1)
    return [
        ("a 1st (limit 1) -> True", True, rl.allow(0, "a")),
        ("a 2nd (limit 1) -> False", False, rl.allow(1, "a")),
        ("a after window slide -> True", True, rl.allow(2000, "a")),
    ]


def l2_set_limit_raise_and_default(C):
    rl = C()                                  # default limit 3
    rl.allow(0, "b")
    rl.allow(1, "b")
    rl.allow(2, "b")
    out = [("b 4th at default limit -> False", False, rl.allow(3, "b"))]
    rl.set_limit("b", 5)
    out.append(("b 4th after raise to 5 -> True", True, rl.allow(3, "b")))
    out.append(("b 5th -> True", True, rl.allow(4, "b")))
    out.append(("b 6th (limit 5) -> False", False, rl.allow(5, "b")))
    # a different client still uses the default limit of 3
    out.append(("c 1st (default) -> True", True, rl.allow(0, "c")))
    out.append(("c 2nd -> True", True, rl.allow(1, "c")))
    out.append(("c 3rd -> True", True, rl.allow(2, "c")))
    out.append(("c 4th (default limit) -> False", False, rl.allow(3, "c")))
    return out


# ------------------------------------------------------------------ Level 3
def l3_block_after_repeated_denials(C):
    rl = C()
    rl.set_penalty(2, 5000)                   # 2 consecutive denials -> block 5000ms
    rl.allow(0, "a")
    rl.allow(1, "a")
    rl.allow(2, "a")                          # window full (limit 3)
    return [
        ("1st over-limit denial -> False", False, rl.allow(3, "a")),
        ("2nd denial trips the block -> False", False, rl.allow(4, "a")),
        ("blocked even though window freed -> False", False, rl.allow(2000, "a")),
        ("request at block expiry -> True", True, rl.allow(5004, "a")),
        ("after unblock, normal allow -> True", True, rl.allow(5005, "a")),
    ]


def l3_streak_resets_on_success(C):
    rl = C()
    rl.set_penalty(2, 5000)
    rl.allow(0, "a")
    rl.allow(1, "a")
    rl.allow(2, "a")                          # window full
    out = [("denial #1 -> False", False, rl.allow(3, "a"))]         # streak 1
    out.append(("success drains window & resets streak -> True",
                True, rl.allow(1004, "a")))                          # streak 0
    rl.allow(1005, "a")
    rl.allow(1006, "a")                        # refill the window
    # streak was reset, so this lone denial does NOT trip the block
    out.append(("denial #2 (non-consecutive) -> False", False, rl.allow(1007, "a")))
    out.append(("not blocked; window free again -> True", True, rl.allow(2007, "a")))
    return out


# ------------------------------------------------------------------ Level 4
def l4_count_history(C):
    rl = C()
    rl.allow(0, "a")
    rl.allow(500, "a")
    rl.allow(900, "a")                        # 3 accepted, window full
    rl.allow(950, "a")                        # DENIED (over limit) -> not recorded
    rl.allow(1100, "a")                       # 0 aged out -> accepted
    rl.allow(1200, "a")                       # DENIED -> not recorded
    rl.allow(1600, "a")                       # accepted
    return [
        ("as-of 900 -> 3", 3, rl.count(2000, "a", 900)),
        ("as-of 950 (denied not counted) -> 3", 3, rl.count(2000, "a", 950)),
        ("as-of 1100 (0 evicted) -> 3", 3, rl.count(2000, "a", 1100)),
        ("as-of 1600 -> 3", 3, rl.count(2000, "a", 1600)),
        ("as-of 0 (only first) -> 1", 1, rl.count(2000, "a", 0)),
    ]


def l4_count_edges(C):
    rl = C()
    rl.allow(100, "a")                        # one accepted request
    return [
        ("unknown client -> 0", 0, rl.count(500, "z", 400)),
        ("before first request -> 0", 0, rl.count(500, "a", 50)),
        ("at the request instant -> 1", 1, rl.count(500, "a", 100)),
        ("just inside window edge (1099) -> 1", 1, rl.count(2000, "a", 1099)),
        ("at window-drop boundary (1100) -> 0", 0, rl.count(2000, "a", 1100)),
    ]


LEVELS = [
    {"name": "Level 1 — Fixed window + limit",
     "tests": [l1_basic, l1_independent_clients]},
    {"name": "Level 2 — Per-client limits",
     "tests": [l2_set_limit_lower, l2_set_limit_raise_and_default]},
    {"name": "Level 3 — Penalty block",
     "tests": [l3_block_after_repeated_denials, l3_streak_resets_on_success]},
    {"name": "Level 4 — Historical count",
     "tests": [l4_count_history, l4_count_edges]},
]
