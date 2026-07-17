"""Drill — Lazy Job Scheduler (fires jobs on a lazy timeline, like banking cashback)."""

from harness import ANY, Pred  # noqa: F401  (available to test authors)

SLUG = "job-scheduler"
TITLE = "Lazy Job Scheduler"
DIFFICULTY = "Ramp ICA archetype · 4 levels"
ENTRYPOINT = "Scheduler"

MARKDOWN = r"""
# Lazy Job Scheduler

Timestamps arrive **non-decreasing** (the first arg of every call is the current
time). `run_at` is a future run time and always satisfies **`run_at >= ts`** —
you never schedule into the past. Job ids are unique strings; once used, a
job id is never reused. This is the banking machine wearing a scheduler skin:
**lazy firing** is the cashback engine, and **historical status** is
`get_balance`.

---

## Level 1 — Schedule / cancel / status

- **`schedule(ts, job_id, run_at) -> bool`** — register `job_id` to fire at
  `run_at`. `True` if registered, `False` if `job_id` already exists.
- **`cancel(ts, job_id) -> bool`** — cancel a still-pending job. `True` if the
  job was `SCHEDULED` (and is now `CANCELLED`); `False` if `job_id` is unknown,
  already `DONE` (its run time has passed), or already `CANCELLED`.
- **`get_status(ts, job_id) -> str | None`** — `"SCHEDULED"`, `"DONE"`, or
  `"CANCELLED"`; `None` if `job_id` is unknown.

## Level 2 — Pending list

- **`pending(ts) -> list[str]`** — every job that is still `SCHEDULED` (not yet
  run, not cancelled) as of `ts`, as job ids sorted **ascending**. No pending
  jobs → `[]`.

## Level 3 — Lazy firing

- Before **every** operation, any job whose **`run_at <= current ts`** flips from
  `SCHEDULED` to `DONE`. Firing is **lazy** — it is realized against the current
  timestamp at the moment an op is handled, exactly like the cashback engine.
  A job fires at the instant `ts` reaches `run_at` (`run_at <= ts`).
- A job cancelled **before** it fires never runs (stays `CANCELLED` forever). A
  job that has already fired can no longer be cancelled.

## Level 4 — Status as-of a past time

- **`get_status(ts, job_id, at_timestamp) -> str | None`** — the status the job
  held **as of `at_timestamp`** (`at_timestamp <= ts`): `"SCHEDULED"` before its
  run/cancel, `"DONE"` once `run_at <= at_timestamp`, `"CANCELLED"` once it was
  cancelled. `None` if the job did not exist yet at `at_timestamp` (or the id is
  unknown).

---

> **Read all four levels first.** L4 kills the obvious design: a mutable
> `status` field can't answer *"what was the status at 3pm?"* Record each
> transition as a `(ts, status)` event and **bisect** the log — every read,
> current or historical, is one binary search. Firing is just appending a
> `DONE` event at `run_at`; cancelling appends a `CANCELLED` event.
"""

STARTER = '''\
import bisect
import heapq


class Scheduler:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def schedule(self, ts, job_id, run_at):
        pass

    def cancel(self, ts, job_id):
        pass

    def get_status(self, ts, job_id, at_timestamp=None):
        pass

    # ---- Level 2 ----
    def pending(self, ts):
        pass
'''

REFERENCE = '''\
import bisect
import heapq


class Scheduler:
    def __init__(self):
        # job_id -> {"run_at": int, "log": [(ts, status), ...]}
        # log is append-only and ts-monotonic; status derives from it.
        self.jobs = {}
        self._due = []      # min-heap of (run_at, seq, job_id) for pending fires
        self._seq = 0

    # lazy firing engine — run before EVERY op
    def _advance(self, t):
        while self._due and self._due[0][0] <= t:
            run_at, _seq, job_id = heapq.heappop(self._due)
            job = self.jobs.get(job_id)
            if job is None:
                continue
            if job["log"][-1][1] == "SCHEDULED":   # skip cancelled/gone jobs
                job["log"].append((run_at, "DONE"))

    def _status_asof(self, job, at):
        log = job["log"]
        i = bisect.bisect_right([e[0] for e in log], at) - 1
        return None if i < 0 else log[i][1]

    # ---- Level 1 ----
    def schedule(self, ts, job_id, run_at):
        self._advance(ts)
        if job_id in self.jobs:
            return False
        self.jobs[job_id] = {"run_at": run_at, "log": [(ts, "SCHEDULED")]}
        self._seq += 1
        heapq.heappush(self._due, (run_at, self._seq, job_id))
        return True

    def cancel(self, ts, job_id):
        self._advance(ts)
        job = self.jobs.get(job_id)
        if job is None or job["log"][-1][1] != "SCHEDULED":
            return False
        job["log"].append((ts, "CANCELLED"))
        return True

    def get_status(self, ts, job_id, at_timestamp=None):
        self._advance(ts)
        job = self.jobs.get(job_id)
        if job is None:
            return None
        if at_timestamp is None:
            return job["log"][-1][1]
        return self._status_asof(job, at_timestamp)

    # ---- Level 2 ----
    def pending(self, ts):
        self._advance(ts)
        return sorted(jid for jid, job in self.jobs.items()
                      if job["log"][-1][1] == "SCHEDULED")
'''


# ------------------------------------------------------------------ Level 1
def l1_schedule_status(C):
    s = C()
    out = [("schedule j1 -> True", True, s.schedule(1, "j1", 100))]
    out.append(("schedule j1 again -> False", False, s.schedule(2, "j1", 200)))
    out.append(("status j1 (before run) -> SCHEDULED", "SCHEDULED", s.get_status(3, "j1")))
    out.append(("status unknown -> None", None, s.get_status(3, "nope")))
    return out


def l1_cancel(C):
    s = C()
    s.schedule(1, "j1", 100)
    return [
        ("cancel unknown -> False", False, s.cancel(2, "nope")),
        ("cancel j1 -> True", True, s.cancel(2, "j1")),
        ("status after cancel -> CANCELLED", "CANCELLED", s.get_status(3, "j1")),
        ("cancel again -> False", False, s.cancel(4, "j1")),
    ]


# ------------------------------------------------------------------ Level 2
def l2_pending_sorted(C):
    s = C()
    s.schedule(1, "b", 100)
    s.schedule(1, "a", 100)
    s.schedule(1, "c", 100)
    return [("pending sorted -> [a,b,c]", ["a", "b", "c"], s.pending(2))]


def l2_pending_excludes_cancelled(C):
    s = C()
    s.schedule(1, "x", 100)
    s.schedule(1, "y", 100)
    s.schedule(1, "z", 100)
    s.cancel(2, "y")
    return [("pending excludes cancelled -> [x,z]", ["x", "z"], s.pending(3))]


def l2_pending_empty(C):
    s = C()
    return [("pending with no jobs -> []", [], s.pending(1))]


# ------------------------------------------------------------------ Level 3
def l3_fires_at_run_at(C):
    s = C()
    s.schedule(1, "j1", 100)
    return [
        ("before run -> SCHEDULED", "SCHEDULED", s.get_status(50, "j1")),
        ("at exactly run_at -> DONE", "DONE", s.get_status(100, "j1")),
        ("after run -> DONE", "DONE", s.get_status(200, "j1")),
    ]


def l3_pending_excludes_fired(C):
    s = C()
    s.schedule(1, "j1", 100)
    s.schedule(1, "j2", 300)
    return [
        ("both pending -> [j1,j2]", ["j1", "j2"], s.pending(50)),
        ("j1 fired -> [j2]", ["j2"], s.pending(150)),
        ("both fired -> []", [], s.pending(400)),
    ]


def l3_cancel_prevents_fire(C):
    s = C()
    s.schedule(1, "j1", 100)
    return [
        ("cancel before run -> True", True, s.cancel(50, "j1")),
        ("still CANCELLED past run_at -> CANCELLED", "CANCELLED", s.get_status(200, "j1")),
        ("cancelled job not pending -> []", [], s.pending(200)),
    ]


def l3_cant_cancel_fired(C):
    s = C()
    s.schedule(1, "j1", 100)
    return [
        ("cancel after fire -> False", False, s.cancel(150, "j1")),
        ("status stays DONE -> DONE", "DONE", s.get_status(160, "j1")),
    ]


# ------------------------------------------------------------------ Level 4
def l4_asof_fired(C):
    s = C()
    s.schedule(10, "j1", 100)
    return [
        ("current (fired) -> DONE", "DONE", s.get_status(200, "j1")),
        ("as-of before scheduled -> None", None, s.get_status(200, "j1", 5)),
        ("as-of at schedule ts -> SCHEDULED", "SCHEDULED", s.get_status(200, "j1", 10)),
        ("as-of just before run -> SCHEDULED", "SCHEDULED", s.get_status(200, "j1", 99)),
        ("as-of at exactly run_at -> DONE", "DONE", s.get_status(200, "j1", 100)),
        ("as-of after run -> DONE", "DONE", s.get_status(200, "j1", 150)),
    ]


def l4_asof_cancelled(C):
    s = C()
    s.schedule(10, "j1", 100)
    s.cancel(50, "j1")
    return [
        ("as-of before scheduled -> None", None, s.get_status(200, "j1", 5)),
        ("as-of after sched, before cancel -> SCHEDULED", "SCHEDULED", s.get_status(200, "j1", 30)),
        ("as-of at cancel instant -> CANCELLED", "CANCELLED", s.get_status(200, "j1", 50)),
        ("as-of past run_at (never fired) -> CANCELLED", "CANCELLED", s.get_status(200, "j1", 150)),
        ("current -> CANCELLED", "CANCELLED", s.get_status(200, "j1")),
    ]


def l4_asof_unknown(C):
    s = C()
    return [("as-of unknown job -> None", None, s.get_status(100, "nope", 50))]


LEVELS = [
    {"name": "Level 1 — Schedule / cancel / status",
     "tests": [l1_schedule_status, l1_cancel]},
    {"name": "Level 2 — Pending list",
     "tests": [l2_pending_sorted, l2_pending_excludes_cancelled, l2_pending_empty]},
    {"name": "Level 3 — Lazy firing",
     "tests": [l3_fires_at_run_at, l3_pending_excludes_fired,
               l3_cancel_prevents_fire, l3_cant_cancel_fired]},
    {"name": "Level 4 — Status as-of a past time",
     "tests": [l4_asof_fired, l4_asof_cancelled, l4_asof_unknown]},
]
