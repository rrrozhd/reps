"""Algo drill — Number of Islands (graph flood fill)."""

from harness import ANY, Pred  # noqa: F401

KIND = "algo"
TOPIC = "graphs"
DIFFICULTY = "medium"
SLUG = "num-islands"
TITLE = "Number of Islands"
ENTRYPOINT = "num_islands"

MARKDOWN = r"""
# Number of Islands

You are given a 2D `grid` of integers where each cell is `1` (land) or `0`
(water). An **island** is a maximal group of `1`s connected **4-directionally**
(up, down, left, right — *not* diagonally). Return the number of islands.

Assume the grid is rectangular (every row has the same length). The border of
the grid is surrounded by water.

## Signature

```python
def num_islands(grid: list[list[int]]) -> int
```

## Examples

**Example 1**

```
grid = [[1, 1, 0],
        [0, 1, 0]]
num_islands(grid) == 1
```

The three `1`s are all orthogonally connected, so they form a single island.

**Example 2**

```
grid = [[1, 1, 0, 0, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 1]]
num_islands(grid) == 3
```

Top-left block, the lone `1` in the middle, and the bottom-right pair — three
separate islands. Note the two `1`s that only touch at a corner are **not**
connected.

## Constraints

- `0 <= rows, cols <= 300`
- Each cell is exactly `0` or `1`.
- An empty grid (`[]`) or a grid of empty rows (`[[]]`) has `0` islands.

> **Hint.** Walk every cell; when you hit an unvisited `1`, start a BFS/DFS flood
> fill that sinks (or marks as seen) the whole connected component, then bump the
> counter. Track visited cells so you never recount the same island — a `set` of
> `(row, col)` keeps the input grid untouched.
"""

STARTER = "def num_islands(grid):\n    pass\n"

REFERENCE = '''\
from collections import deque


def num_islands(grid):
    if not grid or not grid[0]:
        return 0
    rows, cols = len(grid), len(grid[0])
    seen = set()
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1 and (r, c) not in seen:
                count += 1
                seen.add((r, c))
                q = deque([(r, c)])
                while q:
                    x, y = q.popleft()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < rows and 0 <= ny < cols
                                and grid[nx][ny] == 1
                                and (nx, ny) not in seen):
                            seen.add((nx, ny))
                            q.append((nx, ny))
    return count
'''


# ------------------------------------------------------------------ Examples
def examples(F):
    return [
        ("[[1,1,0],[0,1,0]] -> 1", 1, F([[1, 1, 0], [0, 1, 0]])),
        (
            "classic 4x5 grid -> 3",
            3,
            F([
                [1, 1, 0, 0, 0],
                [1, 1, 0, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 1, 1],
            ]),
        ),
        (
            "ring of land -> 1",
            1,
            F([[1, 1, 1], [1, 0, 1], [1, 1, 1]]),
        ),
    ]


# ------------------------------------------------------------------ Edge cases
def edges(F):
    return [
        ("empty grid [] -> 0", 0, F([])),
        ("grid of empty rows [[]] -> 0", 0, F([[]])),
        ("single water [[0]] -> 0", 0, F([[0]])),
        ("single land [[1]] -> 1", 1, F([[1]])),
        ("all water 2x2 -> 0", 0, F([[0, 0], [0, 0]])),
        ("all land 2x2 -> 1", 1, F([[1, 1], [1, 1]])),
        ("diagonal touch only -> 2", 2, F([[1, 0], [0, 1]])),
        (
            "checkerboard 3x3 -> 5",
            5,
            F([[1, 0, 1], [0, 1, 0], [1, 0, 1]]),
        ),
        ("single column [[1],[0],[1]] -> 2", 2, F([[1], [0], [1]])),
        ("single row [[1,0,1,1]] -> 2", 2, F([[1, 0, 1, 1]])),
    ]


def no_mutation(F):
    # A correct visited-set solution leaves the caller's grid untouched.
    grid = [[1, 1, 0], [0, 1, 1]]
    snapshot = [row[:] for row in grid]
    result = F(grid)
    return [
        ("counts the single island -> 1", 1, result),
        ("does not mutate the input grid", snapshot, grid),
    ]


# ------------------------------------------------------------------ Scale
def big(F):
    n = 100
    # Land only at even/even cells, each isolated -> 50*50 = 2500 islands.
    isolated = [
        [1 if (i % 2 == 0 and j % 2 == 0) else 0 for j in range(n)]
        for i in range(n)
    ]
    # One solid 80x80 block -> a single island.
    solid = [[1] * 80 for _ in range(80)]
    return [
        ("100x100 isolated even cells -> 2500", 2500, F(isolated)),
        ("80x80 solid block -> 1", 1, F(solid)),
    ]


LEVELS = [
    {"name": "Examples", "tests": [examples]},
    {"name": "Edge cases", "tests": [edges, no_mutation]},
    {"name": "Scale", "tests": [big]},
]
