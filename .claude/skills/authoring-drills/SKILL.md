---
name: authoring-drills
description: Author a new progressive coding-interview drill for the reps harness — spec, starter, a verified reference solution, and level tests. Use when the user (or the web coach) asks to generate a practice problem by topic/difficulty.
argument-hint: [topic] [easy|medium|hard]
---

# Authoring a reps drill

A **drill** is one problem with **progressive levels** (the CodeSignal ICA house
style: each level bolts a new requirement onto the same growing system). It lives
as a single Python module in `backend/drills/<slug>.py` and is discovered
automatically — no registration step.

## The philosophy (bake this into the problem)

- **Levels are additive.** L2 extends L1's object; L4 must be reachable without
  rewriting L1's data model. Design the state object once so the last level is
  nearly free. The signature move: when a late level needs *history at arbitrary
  points*, the early level must store a **checkpoint/append log**, not a scalar.
- **Difficulty** = how many levels + how much the late levels punish a naive L1.
  `easy` ≈ 2 levels, `medium` ≈ 3, `hard` ≈ 4 with a nasty final twist.

## The module contract (all required unless noted)

```python
SLUG = "<slug>"            # matches the filename, [a-z0-9-]
TITLE = "Human Title"
DIFFICULTY = "medium · 3 levels"      # shown as a pill
ENTRYPOINT = "Solution"    # the class name the candidate must define
MARKDOWN = "..."           # the task spec (see below)
STARTER = "..."            # class skeleton with stub methods (returns None)
REFERENCE = "..."          # a COMPLETE, CORRECT solution as a string
LEVELS = [                 # progressive levels, each with test functions
    {"name": "Level 1 — ...", "tests": [t_l1_a, t_l1_b]},
    ...
]
# optional: def render_state(cls) -> {...}   # only for filesystem-like visuals
```

### MARKDOWN
Markdown, one `##` section per level, each bullet defining a method as
`` **`method(args) -> ret`** `` with its rules and every `None`/`False` edge
case spelled out. End with a one-line hint about the state-design trap.

### STARTER
A triple-quoted string: `class <ENTRYPOINT>:` with `__init__` and every method
stubbed with `pass`. It must import-cleanly (stubs are fine).

### REFERENCE
A triple-quoted string containing a full working solution that defines
`<ENTRYPOINT>`. Standard library only (`bisect`, `collections`, `heapq` ok).

### Tests
Each test is a plain function `def t(Cls) -> list[(label, expected, actual)]`.
It builds a fresh `Cls()`, drives it, and captures **real return values** into
the tuples. The runner compares `expected == actual`. Because the function holds
the real returns, later checks can reference an id an earlier call produced.

```python
def l1_basic(C):
    s = C()
    return [
        ("create A -> True", True, s.create("A")),
        ("create A again -> False", False, s.create("A")),
    ]
```

For non-literal expectations import matchers from `harness`:
`from harness import ANY, Pred` — `ANY` matches anything (call must not raise);
`Pred(fn, "desc")` matches when `fn(actual)` is truthy.

## The hard rule: it MUST verify before you finish

After writing `backend/drills/<slug>.py`, run:

```
python3 backend/verify_drill.py <slug>
```

This executes your REFERENCE against your own LEVELS. It must print
`<slug>: N/N checks passed` with **no FAIL lines**. If anything fails, the bug is
in your reference OR your test's expected value — fix and re-run until green. A
drill that doesn't verify is not done. Never hand back an unverified drill.

## Algorithmic problems (`KIND = "algo"`)

A second problem type: a **single function** (LeetCode-style), tagged by topic and
difficulty, tested by groups of cases. Same module file, a few different fields:

```python
KIND = "algo"
TOPIC = "graphs"                 # arrays, strings, hashmap, two-pointers, sliding-window,
                                 # binary-search, stack, intervals, trees, graphs, dp, heap
DIFFICULTY = "medium"            # easy | medium | hard  (shown as a badge)
ENTRYPOINT = "num_islands"       # a FUNCTION name (not a class)
MARKDOWN = "..."                 # problem statement + a couple of worked examples + constraints
STARTER = "def num_islands(grid):\n    pass\n"
REFERENCE = "def num_islands(grid):\n    ..."   # correct, stdlib only
LEVELS = [                       # here "levels" are test GROUPS, not difficulty tiers
    {"name": "Examples",   "tests": [ex]},
    {"name": "Edge cases", "tests": [edges]},
    {"name": "Scale",      "tests": [big]},     # optional: a larger input
]
```

Test functions receive the **function** and call it:

```python
def ex(F):
    return [
        ("[[1,1,0],[0,1,0]] -> 1", 1, F([[1,1,0],[0,1,0]])),
        ("all water -> 0", 0, F([[0,0],[0,0]])),
    ]
```

Guidance: MARKDOWN states the signature, 1–2 worked examples, and constraints.
Cover the classic edge cases (empty input, single element, all-same, duplicates,
negatives, already-sorted/reversed). Add one "Scale" case big enough that an
obviously-quadratic solution would look slow (correctness only — no hard timeout).
Verify exactly the same way: `python3 backend/verify_drill.py <slug>` must be green.

## Good topics & the trap each teaches

- **state machine / simulation** (banking, inventory) → checkpoint log for history
- **sliding window / rate limiter** → deque of timestamps, lazy eviction
- **LRU / LFU cache** → ordered map + eviction policy, then TTL, then history
- **in-memory KV / filesystem** → per-key/-node write log; lazy expiry
- **interval / calendar** → sorted intervals, merge, then "as-of" queries
- **graph / dependency** → adjacency + toposort, then incremental edges

Pick a skin the user asked for; make L1 trivial, escalate to a late level whose
read/query pattern forces the log-not-scalar design.
