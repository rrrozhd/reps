"""Algo drill — Longest substring without repeating characters (sliding window)."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "sliding-window"
DIFFICULTY = "medium"
SLUG = "longest-substring"
ENTRYPOINT = "length_of_longest_substring"
TITLE = "Longest Substring Without Repeating Characters"

MARKDOWN = r"""
# Longest Substring Without Repeating Characters

Given a string `s`, return the **length of the longest substring** that
contains no repeating characters. A *substring* is a contiguous slice of `s`
(not a subsequence).

```python
def length_of_longest_substring(s: str) -> int:
    ...
```

---

## Examples

- `length_of_longest_substring("abcabcbb")` → `3`
  The answer is `"abc"`, length 3.
- `length_of_longest_substring("bbbbb")` → `1`
  The answer is `"b"`, length 1.
- `length_of_longest_substring("pwwkew")` → `3`
  The answer is `"wke"`, length 3. Note that `"pwke"` is a *subsequence*, not a
  substring, so it does not count.

## Constraints

- `0 <= len(s)` — the empty string returns `0`.
- `s` may contain any characters (letters, digits, symbols, spaces, unicode).
- Aim for `O(n)` time and `O(k)` space, where `k` is the size of the
  character set in the window.

---

> **The trap:** keep a `last_seen[char] -> index` map and a `start` pointer.
> When you see a repeat, only advance `start` **forward** — clamp it with
> `max(start, last_seen[char] + 1)`. Blindly jumping `start` back to an old
> index breaks inputs like `"abba"` (answer `2`) and `"tmmzuxt"` (answer `5`).
"""

STARTER = "def length_of_longest_substring(s):\n    pass\n"

REFERENCE = '''\
def length_of_longest_substring(s):
    last_seen = {}          # char -> most recent index
    start = 0               # left edge of the current window
    best = 0
    for i, ch in enumerate(s):
        prev = last_seen.get(ch)
        if prev is not None and prev >= start:
            start = prev + 1          # clamp forward only
        last_seen[ch] = i
        best = max(best, i - start + 1)
    return best
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ('"abcabcbb" -> 3', 3, F("abcabcbb")),
        ('"bbbbb" -> 1', 1, F("bbbbb")),
        ('"pwwkew" -> 3', 3, F("pwwkew")),
    ]


# ------------------------------------------------------------------ Edge cases
def edge_basics(F):
    return [
        ('"" -> 0', 0, F("")),
        ('"a" -> 1 (singleton)', 1, F("a")),
        ('"au" -> 2 (all distinct)', 2, F("au")),
        ('" " -> 1 (single space)', 1, F(" ")),
        ('"abcdef" -> 6 (all distinct)', 6, F("abcdef")),
    ]


def edge_clamp_forward(F):
    # The cases that only pass when `start` is clamped forward, never rewound.
    return [
        ('"abba" -> 2', 2, F("abba")),
        ('"dvdf" -> 3', 3, F("dvdf")),
        ('"tmmzuxt" -> 5', 5, F("tmmzuxt")),
        ('"abccba" -> 3', 3, F("abccba")),
    ]


def edge_variety(F):
    return [
        ('"   " -> 1 (all spaces)', 1, F("   ")),
        ('"aab" -> 2', 2, F("aab")),
        ('"cdd" -> 2', 2, F("cdd")),
        ('digits "1231234" -> 4 ("1234")', 4, F("1231234")),
        ('"anviaj" -> 5 ("nviaj")', 5, F("anviaj")),
        ('"ohvhjdml" -> 6 ("vhjdml")', 6, F("ohvhjdml")),
        ('unicode "aébécé" -> 3 ("béc")', 3, F("aébécé")),
    ]


# ------------------------------------------------------------------ Scale
def scale(F):
    # Repeated alphabet: best run is one full 26-letter block.
    alpha = "abcdefghijklmnopqrstuvwxyz"
    repeated = alpha * 1000                       # 26,000 chars
    # Fully distinct long string via distinct codepoints -> answer == length.
    distinct = "".join(chr(0x100 + i) for i in range(5000))
    # Uniform char, long -> answer 1.
    uniform = "a" * 100000
    return [
        ("alphabet x1000 -> 26", 26, F(repeated)),
        ("5000 distinct codepoints -> 5000", 5000, F(distinct)),
        ("100000 x 'a' -> 1", 1, F(uniform)),
    ]


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edge_basics, edge_clamp_forward, edge_variety]},
    {"name": "Scale", "tests": [scale]},
]
