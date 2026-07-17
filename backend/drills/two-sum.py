"""Algo drill — Two Sum (classic hashmap-of-complements)."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "hashmap"
DIFFICULTY = "easy"
SLUG = "two-sum"
TITLE = "Two Sum"
ENTRYPOINT = "two_sum"

MARKDOWN = r"""
# Two Sum

Given an array of integers `nums` and an integer `target`, return the **indices
of the two numbers** that add up to `target`.

```python
def two_sum(nums, target) -> list[int]:
    ...
```

- Exactly **one** valid pair is guaranteed to exist.
- Return the pair as `[i, j]` with **`i < j`** (the smaller index first).
- You may not use the same element twice.

---

## Examples

```
two_sum([2, 7, 11, 15], 9)  -> [0, 1]     # nums[0] + nums[1] == 2 + 7 == 9
two_sum([3, 2, 4], 6)       -> [1, 2]     # nums[1] + nums[2] == 2 + 4 == 6
two_sum([3, 3], 6)          -> [0, 1]     # duplicate values, two distinct indices
```

## Constraints

- `2 <= len(nums)`
- Values may be **negative, zero, or duplicated**.
- Exactly one solution exists, so you always return a pair (never an empty list).

---

> **The trap:** the brute-force double loop is `O(n^2)`. Walk the array once and
> keep a **hashmap of `value -> index`** for everything seen so far; at each
> element check whether its *complement* (`target - value`) is already in the map.
> That's one pass, `O(n)`. Storing the index of the **first** occurrence of a
> value is what keeps the returned pair in `i < j` order.
"""

STARTER = "def two_sum(nums, target):\n    pass\n"

REFERENCE = '''\
def two_sum(nums, target):
    seen = {}                      # value -> first index it appeared at
    for i, n in enumerate(nums):
        complement = target - n
        if complement in seen:
            return [seen[complement], i]
        if n not in seen:          # keep the earliest index for a repeated value
            seen[n] = i
    return []                      # unreachable: a solution is guaranteed
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ("[2,7,11,15] t=9 -> [0,1]", [0, 1], F([2, 7, 11, 15], 9)),
        ("[3,2,4] t=6 -> [1,2]", [1, 2], F([3, 2, 4], 6)),
        ("[3,3] t=6 -> [0,1] (duplicates)", [0, 1], F([3, 3], 6)),
    ]


# ------------------------------------------------------------------ Edge cases
def edges(F):
    return [
        # minimal two-element array
        ("[1,2] t=3 -> [0,1]", [0, 1], F([1, 2], 3)),
        # answer sits at the two ends
        ("[5,1,2,8] t=13 -> [0,3]", [0, 3], F([5, 1, 2, 8], 13)),
        # all-negative values
        ("[-1,-2,-3,-4,-5] t=-8 -> [2,4]", [2, 4], F([-1, -2, -3, -4, -5], -8)),
        # mixed sign, target zero
        ("[-3,4,3,90] t=0 -> [0,2]", [0, 2], F([-3, 4, 3, 90], 0)),
        # zeros as the pair
        ("[0,4,3,0] t=0 -> [0,3]", [0, 3], F([0, 4, 3, 0], 0)),
        # duplicate values but the pair uses two of them
        ("[1,5,5,3] t=10 -> [1,2]", [1, 2], F([1, 5, 5, 3], 10)),
    ]


# ------------------------------------------------------------------ Scale
def big(F):
    # nums = [1, 2, ..., 10000]; the unique pair is the last two elements.
    nums = list(range(1, 10001))
    target = 19999                 # 9999 + 10000 == nums[9998] + nums[9999]
    return [
        ("range(1,10001) t=19999 -> [9998,9999]", [9998, 9999], F(nums, target)),
    ]


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edges]},
    {"name": "Scale", "tests": [big]},
]
