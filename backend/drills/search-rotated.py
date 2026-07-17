"""Algo drill — Search in a rotated sorted array (LeetCode 33 archetype)."""

KIND = "algo"
TOPIC = "binary-search"
DIFFICULTY = "medium"
SLUG = "search-rotated"
TITLE = "Search in Rotated Sorted Array"
ENTRYPOINT = "search"

MARKDOWN = r"""
# Search in Rotated Sorted Array

An integer array `nums` was originally sorted in **ascending** order with
**distinct** values, then **rotated** at some unknown pivot. For example
`[0, 1, 2, 4, 5, 6, 7]` might become `[4, 5, 6, 7, 0, 1, 2]` (rotated at
index 4). The array may also be rotated zero times (still fully sorted).

Given the rotated array and an integer `target`, return the **index** of
`target` in `nums`, or `-1` if it is not present.

You must write an algorithm with **`O(log n)`** runtime — a plain linear scan
does not count. The classic move is a **modified binary search**: at each step
one half `[lo..mid]` or `[mid..hi]` is guaranteed sorted; test whether `target`
falls inside that sorted half to decide which way to recurse.

## Signature

```python
def search(nums: list[int], target: int) -> int:
    ...
```

## Examples

```
search([4, 5, 6, 7, 0, 1, 2], 0) -> 4      # 0 sits at index 4
search([4, 5, 6, 7, 0, 1, 2], 3) -> -1     # 3 is absent
search([1], 0)                    -> -1     # single element, no match
```

## Constraints

- `0 <= len(nums) <= 5000`
- All values in `nums` are **distinct**.
- `nums` is a (possibly zero-time) rotation of an ascending-sorted array.
- `-10^4 <= nums[i], target <= 10^4`
- Required complexity: **`O(log n)`**.

> **Hint.** Compare `nums[mid]` against `nums[lo]` to learn which half is
> sorted, then check `target` against that half's endpoints. An empty array
> must return `-1` without touching any element.
"""

STARTER = '''\
def search(nums, target):
    pass
'''

REFERENCE = '''\
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:            # left half [lo..mid] is sorted
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                                # right half [mid..hi] is sorted
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    nums = [4, 5, 6, 7, 0, 1, 2]
    return [
        ("[4,5,6,7,0,1,2] find 0 -> 4", 4, F(nums, 0)),
        ("[4,5,6,7,0,1,2] find 3 (absent) -> -1", -1, F(nums, 3)),
        ("[4,5,6,7,0,1,2] find 4 (first) -> 0", 0, F(nums, 4)),
        ("[4,5,6,7,0,1,2] find 2 (last) -> 6", 6, F(nums, 2)),
        ("[4,5,6,7,0,1,2] find 7 (pivot-1) -> 3", 3, F(nums, 7)),
        ("[1] find 0 (absent) -> -1", -1, F([1], 0)),
    ]


# --------------------------------------------------------------- Edge cases
def edges(F):
    return [
        ("empty [] find 5 -> -1", -1, F([], 5)),
        ("single [1] find 1 -> 0", 0, F([1], 1)),
        ("single [1] find 2 (absent) -> -1", -1, F([1], 2)),
        ("two [3,1] find 3 -> 0", 0, F([3, 1], 3)),
        ("two [3,1] find 1 -> 1", 1, F([3, 1], 1)),
        ("two [3,1] find 2 (absent) -> -1", -1, F([3, 1], 2)),
        ("two sorted [1,3] find 3 -> 1", 1, F([1, 3], 3)),
    ]


def not_rotated(F):
    nums = [1, 2, 3, 4, 5, 6, 7]
    return [
        ("sorted find 1 (min) -> 0", 0, F(nums, 1)),
        ("sorted find 7 (max) -> 6", 6, F(nums, 7)),
        ("sorted find 4 (mid) -> 3", 3, F(nums, 4)),
        ("sorted find 8 (too big) -> -1", -1, F(nums, 8)),
        ("sorted find 0 (too small) -> -1", -1, F(nums, 0)),
    ]


def rotation_points(F):
    # Same underlying set rotated to every pivot; target always found correctly.
    base = [0, 1, 2, 3, 4, 5]
    out = []
    for k in range(len(base)):
        nums = base[k:] + base[:k]        # rotate left by k
        idx = (len(base) - k) % len(base)  # where value 0 lands
        out.append((f"rot k={k} find 0 -> {idx}", idx, F(nums, 0)))
        out.append((f"rot k={k} find 99 (absent) -> -1", -1, F(nums, 99)))
    return out


def negatives(F):
    nums = [3, 4, 5, -3, -2, -1, 0, 1, 2]   # ascending [-3..5] rotated at 3
    return [
        ("neg array find -3 (min) -> 3", 3, F(nums, -3)),
        ("neg array find 5 (max) -> 2", 2, F(nums, 5)),
        ("neg array find 0 -> 6", 6, F(nums, 0)),
        ("neg array find -4 (absent) -> -1", -1, F(nums, -4)),
    ]


# -------------------------------------------------------------------- Scale
def scale(F):
    n = 10000
    k = 3000
    base = list(range(n))                 # 0..9999 ascending, distinct
    nums = base[k:] + base[:k]            # [3000..9999, 0..2999]
    out = []
    # Value v (0 <= v < n) lives at index (v - k) % n after a left-rotate by k.
    for v in (0, 100, 2999, 3000, 7777, 9999):
        expected = (v - k) % n
        out.append((f"scale n={n} find {v} -> {expected}", expected, F(nums, v)))
    out.append((f"scale n={n} find 15000 (absent) -> -1", -1, F(nums, 15000)))
    out.append((f"scale n={n} find -1 (absent) -> -1", -1, F(nums, -1)))
    return out


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edges, not_rotated, rotation_points, negatives]},
    {"name": "Scale", "tests": [scale]},
]
