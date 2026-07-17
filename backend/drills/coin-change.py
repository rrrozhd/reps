"""Algo drill — Coin Change (fewest coins; unbounded-knapsack DP)."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "dp"
DIFFICULTY = "medium"
SLUG = "coin-change"
TITLE = "Coin Change"
ENTRYPOINT = "coin_change"

MARKDOWN = r"""
# Coin Change

You are given a list of coin denominations `coins` and a target `amount`.
Return the **fewest number of coins** needed to make up `amount`. You have an
**unlimited** supply of each denomination. If no combination sums to `amount`,
return `-1`.

```python
def coin_change(coins, amount) -> int:
    ...
```

- Each denomination may be used **any number of times** (unbounded).
- The order of coins in the answer doesn't matter — only the count.
- Return `0` when `amount == 0` (zero coins needed), regardless of `coins`.

---

## Examples

```
coin_change([1, 2, 5], 11)  -> 3     # 5 + 5 + 1
coin_change([2], 3)         -> -1    # 3 is unreachable with only 2s
coin_change([1, 3, 4], 6)   -> 2     # 3 + 3  (greedy 4+1+1 would use 3 — wrong)
```

## Constraints

- `0 <= amount`
- `coins` may be **empty** (then only `amount == 0` is solvable).
- Denominations are positive; the list may contain **duplicates** or values
  **larger than `amount`** (those simply can't be used).

---

> **The trap:** greedy "take the biggest coin that fits" is wrong for arbitrary
> denominations — `[1,3,4]` for `6` proves it. Build a 1-D DP table `dp[a] =
> fewest coins to make a`, with `dp[0] = 0` and every other cell seeded to
> "infinity". For each sub-amount `a` from `1..amount`, try every coin `c <= a`
> and take `min(dp[a], dp[a-c] + 1)`. Because each coin is reused freely, you
> read *forward* from smaller sub-amounts — that's the unbounded knapsack. The
> answer is `dp[amount]`, or `-1` if it never dropped below infinity. Runs in
> `O(amount * len(coins))`.
"""

STARTER = "def coin_change(coins, amount):\n    pass\n"

REFERENCE = '''\
def coin_change(coins, amount):
    # dp[a] = fewest coins to make sub-amount a; amount+1 stands in for infinity
    # (a real answer can never exceed `amount`, since the smallest coin is >= 1).
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != INF else -1
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ("[1,2,5] a=11 -> 3 (5+5+1)", 3, F([1, 2, 5], 11)),
        ("[2] a=3 -> -1 (unreachable)", -1, F([2], 3)),
        ("[1,3,4] a=6 -> 2 (3+3, not greedy 4+1+1)", 2, F([1, 3, 4], 6)),
    ]


# ------------------------------------------------------------------ Edge cases
def edges(F):
    return [
        # amount 0 -> 0 coins, even with denominations available
        ("[1,2,5] a=0 -> 0", 0, F([1, 2, 5], 0)),
        # amount 0 with no coins is still solvable with zero coins
        ("[] a=0 -> 0", 0, F([], 0)),
        # empty coin set, positive amount -> impossible
        ("[] a=7 -> -1", -1, F([], 7)),
        # single coin, exact multiple
        ("[7] a=7 -> 1", 1, F([7], 7)),
        # single coin, not a multiple
        ("[3] a=7 -> -1", -1, F([3], 7)),
        # every coin larger than the amount -> impossible
        ("[5,10] a=3 -> -1", -1, F([5, 10], 3)),
        # a coin equal to the amount -> exactly one coin
        ("[2,4,6] a=6 -> 1", 1, F([2, 4, 6], 6)),
        # duplicate denominations don't change the answer
        ("[2,2,5] a=11 -> 4 (5+2+2+2)", 4, F([2, 2, 5], 11)),
        # unordered denominations still work
        ("[5,2,1] a=11 -> 3", 3, F([5, 2, 1], 11)),
    ]


# ------------------------------------------------------------------ Scale
def big(F):
    # Large amount: an un-memoized exponential recursion would stall here.
    return [
        # 10000 made of 5s only -> 2000 coins
        ("[1,2,5] a=10000 -> 2000", 2000, F([1, 2, 5], 10000)),
        # classic awkward denominations where greedy fails badly
        ("[186,419,83,408] a=6249 -> 20", 20, F([186, 419, 83, 408], 6249)),
        # canonical US coin system, large target
        ("[1,5,10,25] a=9999 -> 405", 405, F([1, 5, 10, 25], 9999)),
    ]


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edges]},
    {"name": "Scale", "tests": [big]},
]
