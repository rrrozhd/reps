"""Algo drill — Trapping Rain Water (classic two-pointer O(n)/O(1))."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "two-pointers"
DIFFICULTY = "hard"
SLUG = "trapping-rain-water"
TITLE = "Trapping Rain Water"
ENTRYPOINT = "trap"

MARKDOWN = r"""
# Trapping Rain Water

Given `height`, a list of non-negative integers where each value is the height of
a bar of width `1`, compute **how many units of water** are trapped between the
bars after it rains.

```python
def trap(height) -> int:
    ...
```

Water sitting above bar `i` is bounded by the tallest bar to its left and the
tallest bar to its right: it holds `min(max_left, max_right) - height[i]` units
(clamped at `0`). The answer is the sum over every index.

---

## Examples

```
trap([0,1,0,2,1,0,1,3,2,1,2,1]) -> 6
#     the dips between the taller bars hold 6 units total

trap([4,2,0,3,2,5]) -> 9
#     the deep basin behind the height-5 wall holds 9 units

trap([3,0,2,0,4]) -> 7
#     3 + 1 + 3 across the three sunken columns
```

## Constraints

- `0 <= len(height)` — the list may be **empty** (answer `0`).
- Each `height[i]` is a non-negative integer (`0` is allowed).
- A single bar, a strictly rising ramp, or a strictly falling ramp traps nothing.

---

> **The trap:** the naive approach precomputes `max_left[i]` and `max_right[i]`
> in two arrays — correct, but `O(n)` **extra space**. The interview answer walks
> two pointers inward from both ends. Whichever side has the **smaller** running
> max is the side whose water level is already decided, so you can settle that
> column and step that pointer in. One pass, `O(1)` space.
"""

STARTER = "def trap(height):\n    pass\n"

REFERENCE = '''\
def trap(height):
    if not height:
        return 0
    left, right = 0, len(height) - 1
    left_max, right_max = height[left], height[right]
    total = 0
    while left < right:
        # The smaller of the two running maxes bounds its column's water.
        if left_max <= right_max:
            left += 1
            left_max = max(left_max, height[left])
            total += left_max - height[left]
        else:
            right -= 1
            right_max = max(right_max, height[right])
            total += right_max - height[right]
    return total
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ("[0,1,0,2,1,0,1,3,2,1,2,1] -> 6", 6,
         F([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1])),
        ("[4,2,0,3,2,5] -> 9", 9, F([4, 2, 0, 3, 2, 5])),
        ("[3,0,2,0,4] -> 7", 7, F([3, 0, 2, 0, 4])),
    ]


# ------------------------------------------------------------------ Edge cases
def edges(F):
    return [
        # empty input traps nothing
        ("[] -> 0", 0, F([])),
        # single bar has no left/right walls
        ("[5] -> 0", 0, F([5])),
        # two bars can never form a basin
        ("[1,2] -> 0", 0, F([1, 2])),
        ("[2,1] -> 0", 0, F([2, 1])),
        # all-equal bars: flat, no water
        ("[3,3,3] -> 0", 0, F([3, 3, 3])),
        # all zeros
        ("[0,0,0] -> 0", 0, F([0, 0, 0])),
        # strictly increasing ramp
        ("[1,2,3,4,5] -> 0", 0, F([1, 2, 3, 4, 5])),
        # strictly decreasing ramp
        ("[5,4,3,2,1] -> 0", 0, F([5, 4, 3, 2, 1])),
        # minimal single-dip basin
        ("[2,0,2] -> 2", 2, F([2, 0, 2])),
        # duplicate walls around one dip
        ("[5,5,1,5,5] -> 4", 4, F([5, 5, 1, 5, 5])),
    ]


# ------------------------------------------------------------------ Scale
def big(F):
    # One huge basin: two walls of 1000 around 9998 zero-height columns.
    # Every interior column traps min(1000, 1000) = 1000 units.
    height = [1000] + [0] * 9998 + [1000]
    return [
        ("wall-0*9998-wall (n=10000) -> 9998000", 9_998_000, F(height)),
    ]


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edges]},
    {"name": "Scale", "tests": [big]},
]
