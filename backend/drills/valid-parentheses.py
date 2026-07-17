"""Algo drill — Valid Parentheses (classic stack warm-up)."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "stack"
DIFFICULTY = "easy"
SLUG = "valid-parentheses"
ENTRYPOINT = "is_valid"
TITLE = "Valid Parentheses"

MARKDOWN = r"""
# Valid Parentheses

Given a string `s` containing only the characters `()[]{}`, decide whether the
brackets are **balanced and correctly nested**.

A string is valid when:

1. every opening bracket is closed by the **same type** of bracket, and
2. brackets close in the **right order** — the most recently opened bracket is
   the first one closed (last-in, first-out).

```
def is_valid(s: str) -> bool
```

Return `True` if `s` is valid, otherwise `False`.

---

## Examples

- `is_valid("()[]{}")` → `True` — three independent, well-formed pairs.
- `is_valid("([)]")` → `False` — the `)` tries to close a `[`, so the nesting
  is crossed.
- `is_valid("{[]}")` → `True` — properly nested inside-out.

## Constraints

- `0 <= len(s) <= 10^4`.
- `s` consists only of the characters `'('`, `')'`, `'['`, `']'`, `'{'`, `'}'`.
- The empty string is considered valid.

---

> **Hint.** Walk the string with a **stack**. Push every opener; on a closer,
> pop and check it matches. Any mismatch, a pop from an empty stack, or a
> non-empty stack at the end means invalid.
"""

STARTER = "def is_valid(s):\n    pass\n"

REFERENCE = '''\
def is_valid(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ('"()" -> True', True, F("()")),
        ('"()[]{}" -> True', True, F("()[]{}")),
        ('"(]" -> False', False, F("(]")),
        ('"([)]" -> False', False, F("([)]")),
        ('"{[]}" -> True', True, F("{[]}")),
    ]


# ------------------------------------------------------------------ Edge cases
def edges(F):
    return [
        ('"" (empty) -> True', True, F("")),
        ('"(" single open -> False', False, F("(")),
        ('")" single close -> False', False, F(")")),
        ('"]" lone close -> False', False, F("]")),
        ('"((" -> False', False, F("((")),
        ('"))" -> False', False, F("))")),
        ('"(()" -> False', False, F("(()")),
        ('"())" -> False', False, F("())")),
        ('"([{}])" nested -> True', True, F("([{}])")),
        ('"(((())))" deep balanced -> True', True, F("(((())))")),
        ('")(" right count wrong order -> False', False, F(")(")),
        ('"{[()]}{}" -> True', True, F("{[()]}{}")),
    ]


# ------------------------------------------------------------------ Scale
def scale(F):
    balanced = "()" * 5000                       # 10k chars, all valid pairs
    deep = "(" * 5000 + ")" * 5000               # 10k chars, deeply nested
    unbalanced_deep = "(" * 5000 + ")" * 4999    # one opener never closed
    return [
        ("5000 flat pairs -> True", True, F(balanced)),
        ("5000-deep nesting -> True", True, F(deep)),
        ("deep, one unclosed -> False", False, F(unbalanced_deep)),
    ]


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edges]},
    {"name": "Scale", "tests": [scale]},
]
