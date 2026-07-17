"""Algo drill — Merge Intervals (sort then sweep)."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "intervals"
DIFFICULTY = "medium"
SLUG = "merge-intervals"
TITLE = "Merge Intervals"
ENTRYPOINT = "merge"

MARKDOWN = r"""
# Merge Intervals

Given a list of intervals where each interval is a two-element list
`[start, end]` with `start <= end`, merge every set of overlapping intervals
and return the resulting list, **sorted by start**. Two intervals overlap when
they share any point — and **touching endpoints count**: `[1, 4]` and `[4, 5]`
merge into `[1, 5]`.

## Signature

```python
def merge(intervals: list[list[int]]) -> list[list[int]]:
    ...
```

The input is not guaranteed to be sorted, and `intervals` may be empty. Return a
new list of `[start, end]` pairs; do not assume the input can be mutated in
place. Each returned interval must itself be a two-element `[start, end]` list.

## Examples

```
merge([[1, 3], [2, 6], [8, 10], [15, 18]]) -> [[1, 6], [8, 10], [15, 18]]
    [1,3] and [2,6] overlap -> [1,6]; the rest are disjoint.

merge([[1, 4], [4, 5]]) -> [[1, 5]]
    Touching at 4 -> merged.
```

## Constraints

- `0 <= len(intervals) <= 10^4`
- For each interval, `start <= end`; values fit in a signed 64-bit integer and
  may be negative.
- Output is sorted ascending by start (with disjoint intervals, that also means
  by end).

> **Approach:** sort by start, then sweep once. Keep the last interval in your
> output; for each next interval, if `next.start <= last.end` extend
> `last.end = max(last.end, next.end)`, otherwise append a fresh interval. The
> `<=` (not `<`) is what makes touching endpoints merge.
"""

STARTER = "def merge(intervals):\n    pass\n"

REFERENCE = '''\
def merge(intervals):
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda iv: (iv[0], iv[1]))
    out = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        last = out[-1]
        if start <= last[1]:          # overlap or touch -> extend
            if end > last[1]:
                last[1] = end
        else:
            out.append([start, end])
    return out
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ("classic overlap",
         [[1, 6], [8, 10], [15, 18]],
         F([[1, 3], [2, 6], [8, 10], [15, 18]])),
        ("touching endpoints merge",
         [[1, 5]],
         F([[1, 4], [4, 5]])),
        ("unsorted input",
         [[1, 4], [6, 8], [10, 15]],
         F([[6, 8], [1, 4], [10, 15]])),
        ("fully nested",
         [[1, 10]],
         F([[1, 10], [2, 3], [4, 8]])),
    ]


# ------------------------------------------------------------------ Edge cases
def edges(F):
    return [
        ("empty -> []", [], F([])),
        ("single interval unchanged", [[3, 7]], F([[3, 7]])),
        ("degenerate point [5,5]", [[5, 5]], F([[5, 5]])),
        ("two identical duplicates merge", [[2, 4]], F([[2, 4], [2, 4]])),
        ("disjoint stays split", [[1, 2], [3, 4]], F([[1, 2], [3, 4]])),
        ("gap of one is NOT touching", [[1, 2], [4, 5]], F([[1, 2], [4, 5]])),
        ("negative coordinates", [[-5, -1], [3, 6]], F([[3, 6], [-5, -1]])),
        ("same start different end",
         [[1, 5]], F([[1, 3], [1, 5], [1, 2]])),
        ("chain where each touches next",
         [[1, 6]], F([[1, 2], [2, 3], [3, 4], [4, 5], [5, 6]])),
        ("later interval swallowed by earlier",
         [[1, 20]], F([[1, 20], [5, 9], [10, 11]])),
    ]


# ------------------------------------------------------------------ Scale
def scale(F):
    # 5000 disjoint intervals [0,1],[3,4],[6,7],... shuffled by construction
    # order (interleave from both ends) so the solution must sort. They never
    # touch (gap of 2 between them), so the output equals the sorted input.
    n = 5000
    base = [[3 * i, 3 * i + 1] for i in range(n)]
    shuffled = []
    lo, hi = 0, n - 1
    while lo <= hi:
        shuffled.append(base[hi])
        if lo != hi:
            shuffled.append(base[lo])
        lo += 1
        hi -= 1
    expected_disjoint = base  # already sorted, none merge

    # 5000 intervals that all overlap into a single [0, 5001] blob.
    big_overlap = [[i, i + 2] for i in range(n)]  # [0,2],[1,3],... chain
    expected_blob = [[0, n + 1]]

    return [
        ("5000 shuffled disjoint -> sorted, none merged",
         expected_disjoint, F(shuffled)),
        ("5000 overlapping -> single interval",
         expected_blob, F(big_overlap)),
    ]


LEVELS = [
    {"name": "Examples",   "tests": [examples]},
    {"name": "Edge cases", "tests": [edges]},
    {"name": "Scale",      "tests": [scale]},
]
