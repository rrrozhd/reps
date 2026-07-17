# In-Memory File System — a full walkthrough (how to *arrive* at the code)

The goal here isn't to memorize a solution — it's to internalize the **order of
reasoning** that produces one under exam conditions. Every ICA problem yields to
the same four moves:

1. **Read all levels first.** Let the last level dictate your data model.
2. **Design the state object once**, backward from the hardest requirement.
3. **Write your navigation primitives** before any feature.
4. **Each method = navigate → mutate the live view → record in the log.**

We'll derive the whole thing in that order.

---

## Step 0 — Read all four levels before typing (5 minutes, non-negotiable)

Skim every level and ask one question: **"What's the worst thing the last level
demands of the first level's storage?"**

- L1: `mkdir`, `add_file(path, size)`, `get_file_size(path)`.
- L2: `get_dir_size`, `find(prefix)`.
- L3: `delete`, `copy`, `move`.
- L4: **`get_file_size(path, at_version)`** — the size of a file *as of a past
  version*.

That L4 line is the whole game. It means **a file's size cannot be a single
number.** If you store `size = 42` and later overwrite it to `99`, the `42` is
gone — but L4 needs it back. So a file needs a **history of sizes over time**,
exactly like the checkpoint log in the banking/KV drills.

It also tells you there's a notion of **"version"**: a global counter that ticks
on every change. `add_file` returning an `int` is the spec handing you those
version numbers so the caller can query them later.

**Decision made before writing a line:** files are versioned; I'll keep a
per-file **write-log** of `(version, size)`. Skip this read-ahead and you'll
build L1 with a scalar `size`, then rewrite everything at L4 under time pressure.

---

## Step 1 — Design the state object (backward from L4)

Two structures, each earning its place:

```python
def __init__(self):
    self.root = {"type": "dir", "children": {}}   # the LIVE tree (current state)
    self.version = 0                                # global counter, bumps on mutations
    self.file_log = {}                              # path -> [(version, size_or_None)]
```

**Why a tree of typed nodes?** A filesystem *is* a tree, and almost every
operation is "navigate to a path." Represent each node so it can answer *"am I a
directory or a file?"*:

```
dir  ->  {"type": "dir",  "children": {name: node, ...}}
file ->  {"type": "file", "size": n}
```

Root is just a dir with no parent. (You *could* use "dir = plain dict, file =
int," but the typed node makes the dir/file check explicit and lets a file grow
extra fields later without a rewrite.)

**Why also a separate `file_log`?** The tree only knows the *present*. L4 asks
about the *past*. So alongside the live tree, keep an append-only log per file
path: each entry is `(version, size)`, and a **deletion** is recorded as
`(version, None)` — a tombstone, same idea as the KV drill. The live tree serves
L1–L3 fast; the log serves L4 with one binary search.

**Why a global `version`, and why only some ops bump it?** The spec says content
mutations are versioned. So `add_file`, `delete`, `copy`, `move` each do
`self.version += 1`; `mkdir` does **not** (directories have no size history).
`add_file` returns the new `version` so the caller has a handle for L4 queries.

You now have the entire shape of the problem. Everything below is mechanical.

---

## Step 2 — The navigation primitives (write these *before* any feature)

Every method starts by walking a path. Write that once, correctly, and the rest
is easy. Two walkers:

### `_resolve` — walk to a node (used when you want the thing itself)

```python
def _parts(self, path):
    return [p for p in path.split("/") if p]        # "/a/b/c" -> ["a","b","c"]

def _resolve(self, path):
    node = self.root
    for name in self._parts(path):
        if node["type"] != "dir" or name not in node["children"]:
            return None                              # dead end -> path doesn't exist
        node = node["children"][name]
    return node
```

Reasoning: start at root; for each path component, step into that child. If the
current node isn't a directory (can't have children) or the child is missing, the
path is invalid → `None`. `_resolve("/")` → `_parts` is empty → returns root.

### `_resolve_parent` — walk to the parent (used when you're about to create/place something)

For `mkdir`/`add_file`/`copy`/`move` you don't want the target (it may not exist
yet) — you want its **parent directory** and the **name** to create.

```python
def _resolve_parent(self, path):
    parts = self._parts(path)
    if not parts:
        return None, None                            # "/" has no parent
    node = self.root
    for name in parts[:-1]:                          # everything EXCEPT the last name
        child = node["children"].get(name) if node["type"] == "dir" else None
        if child is None or child["type"] != "dir":
            return None, None
        node = child
    return node, parts[-1]                            # (parent dir node, name to place)
```

This is the piece you were stuck on, so read the two failure lines carefully —
**your two checks are exactly these:**

- `child is None` → an ancestor (including the immediate parent) is **missing**.
- `child["type"] != "dir"` → an ancestor is a **file**, so you can't descend into
  it.

The last element of `parts[:-1]` *is* the immediate parent, so both of your
questions ("does the parent exist? is it a file?") are answered by this single
loop — and it also catches a broken path higher up (`/x/y/z` when `/x` is a file).

---

## Step 3 — Level 1, method by method

### `mkdir` — now it's four lines

```python
def mkdir(self, path):
    parent, name = self._resolve_parent(path)
    if parent is None:              return False      # parent missing OR parent is a file
    if name in parent["children"]:  return False      # already exists
    parent["children"][name] = {"type": "dir", "children": {}}
    return True
```

Reasoning, mapped to the spec's `False` cases:
- "parent is missing" and "parent is a file" → both collapse into
  `parent is None` (the primitive already distinguished them and returned
  failure).
- "already exists" → `name in parent["children"]`.
- Otherwise create an empty dir node. No `version` bump (mkdir isn't a content
  mutation).

Trace: `mkdir("/a")` → parent = root, name = "a" → create ✓. `mkdir("/x/y")` with
no `/x` → `_resolve_parent` hits missing "x" → `(None, None)` → False ✓.
`mkdir("/a/f")` where `/a/f` is a file → name "f" already in `/a` → False ✓.

### `add_file` — first method that touches the log

```python
def add_file(self, path, size):
    parent, name = self._resolve_parent(path)
    if parent is None:
        return None
    existing = parent["children"].get(name)
    if existing is not None and existing["type"] == "dir":
        return None                                   # can't turn a dir into a file
    self.version += 1
    parent["children"][name] = {"type": "file", "size": size}   # live tree
    self._log(path, size)                             # history
    return self.version
```

Reasoning: same parent walk. New failure case from the spec — if `path` is an
existing **directory**, refuse (`None`). Overwriting an existing *file* is
allowed (and is a new version). Then do the two writes that every mutation does:
update the **live tree**, and append `(version, size)` to the **log**. Return the
version — that's the handle L4 needs.

```python
def _log(self, path, size):
    self.file_log.setdefault(path, []).append((self.version, size))
```

### `get_file_size(path)` — the current-state read

```python
def get_file_size(self, path, at_version=None):
    if at_version is None:                            # current form
        node = self._resolve(path)
        return node["size"] if node and node["type"] == "file" else None
    ...                                               # historical form -> Step 6
```

Reasoning: navigate to the node; it's only a size if it exists *and* is a file
(a directory or a missing path → `None`). We fold both the current and historical
forms into one method via the `at_version` default — the spec's L4 overload.

---

## Step 4 — Level 2 (aggregates & search)

Both need "visit every file under a directory." Write that helper once:

```python
def _walk_files(self, node, prefix, out):
    for name, child in node["children"].items():
        p = prefix + "/" + name
        if child["type"] == "file":
            out.append((p, child["size"]))
        else:
            self._walk_files(child, p, out)           # recurse into subdirs
```

### `get_dir_size` — sum the subtree

```python
def get_dir_size(self, path):
    node = self._resolve(path)
    if node is None or node["type"] != "dir":
        return None                                   # not a directory
    out = []
    self._walk_files(node, path.rstrip("/"), out)
    return sum(sz for _, sz in out)
```

Reasoning: resolve the directory (must exist and be a dir, else `None`), walk all
files beneath it, sum their sizes. `path.rstrip("/")` keeps the reconstructed
paths clean when someone passes `"/"`.

### `find(prefix)` — all file paths matching a prefix

```python
def find(self, prefix):
    out = []
    self._walk_files(self.root, "", out)
    return sorted(p for p, _ in out if p.startswith(prefix))
```

Reasoning: gather every file's full path from the root, keep those starting with
`prefix`, return sorted. (Note the honest edge: `find("/a/b")` also matches
`/a/banana` — a *path* prefix, not a "directory contents" filter. Decide which
the spec wants; here it's a literal string prefix.)

---

## Step 5 — Level 3 (delete / copy / move)

The theme: **mutate the live tree, and mirror the change into the log** (files
appearing get a `(version, size)`, files disappearing get a `(version, None)`).

### `delete`

```python
def delete(self, path):
    parent, name = self._resolve_parent(path)
    if parent is None or name not in parent["children"]:
        return False
    node = parent["children"][name]
    self.version += 1
    if node["type"] == "file":
        self._log(path, None)                         # tombstone this file
    else:
        out = []
        self._walk_files(node, path.rstrip("/"), out)
        for fp, _ in out:
            self._log(fp, None)                       # tombstone every file inside
    del parent["children"][name]
    return True
```

Reasoning: find it via the parent walk. Bump the version. A deletion is an
**event on the timeline**, not an erasure — so for the file (or every file inside
a deleted directory) append a `None` tombstone at this version, *then* remove it
from the live tree. (This is the exact bug that breaks L4 if you forget it — the
log must remember that the file died at version N.)

### `copy` — deep-clone a subtree

```python
def _clone(self, node):
    if node["type"] == "file":
        return {"type": "file", "size": node["size"]}
    return {"type": "dir", "children": {k: self._clone(v) for k, v in node["children"].items()}}

def copy(self, src, dst):
    node = self._resolve(src)
    if node is None:
        return False                                  # src must exist
    dparent, dname = self._resolve_parent(dst)
    if dparent is None or dname in dparent["children"]:
        return False                                  # dst parent must exist; dst must be free
    self.version += 1
    clone = self._clone(node)
    dparent["children"][dname] = clone
    if clone["type"] == "file":
        self._log(dst, clone["size"])
    else:
        out = []
        self._walk_files(clone, dst.rstrip("/"), out)
        for fp, sz in out:
            self._log(fp, sz)                         # every copied file is a new write at dst
    return True
```

Reasoning: `src` must exist; `dst` must **not** exist and its parent must be a
real directory. Deep-copy (a shallow copy would alias children — mutating the
copy would corrupt the original). Then log every newly-created file path at the
new version.

### `move` — copy's placement + src removal, atomically

```python
def move(self, src, dst):
    node = self._resolve(src)
    if node is None or dst == src or dst.startswith(src.rstrip("/") + "/"):
        return False                                  # can't move a dir into itself
    sparent, sname = self._resolve_parent(src)
    dparent, dname = self._resolve_parent(dst)
    if sparent is None or dparent is None or dname in dparent["children"]:
        return False
    self.version += 1
    if node["type"] == "file":
        self._log(src, None)                          # gone from here
        self._log(dst, node["size"])                  # appears there
    else:
        old = []; self._walk_files(node, src.rstrip("/"), old)
        for fp, _ in old: self._log(fp, None)
        new = []; self._walk_files(node, dst.rstrip("/"), new)
        for fp, sz in new: self._log(fp, sz)
    del sparent["children"][sname]
    dparent["children"][dname] = node                 # reuse the node object — no clone needed
    return True
```

Reasoning: the one extra rule vs. copy — you can't move a directory **into its
own subtree** (`dst.startswith(src + "/")`), or you'd detach it from the tree.
Move can *reuse* the node object (no clone), but the log must show every file
leaving `src` (tombstone) and arriving at `dst` (new size) at this version.

---

## Step 6 — Level 4 (the payoff)

Because you kept the log from L1, historical reads are a two-line binary search:

```python
def get_file_size(self, path, at_version=None):
    if at_version is None:
        node = self._resolve(path)
        return node["size"] if node and node["type"] == "file" else None
    log = self.file_log.get(path)
    if not log:
        return None
    i = bisect.bisect_right([v for v, _ in log], at_version) - 1
    return None if i < 0 else log[i][1]               # size, or None if that entry was a delete
```

Reasoning: find the **last log entry whose version ≤ `at_version`**
(`bisect_right ... - 1`). If there's none (the file didn't exist yet) → `None`.
If that entry is a tombstone (`size` is `None`, i.e. it had been deleted by then)
→ `None`. Otherwise return the size that was current at that version. No special
cases — the log already encodes creation, overwrite, and deletion as points on a
line, and you just look up the point.

**This is why L4 is nearly free:** you did the hard thinking in Step 0. If you'd
stored a scalar `size`, you'd be rewriting all of L1–L3 right now.

---

## The transferable checklist

1. **Read all levels; let the last one pick your data model.** Historical/"as-of"
   reads ⇒ an append-only log, never a scalar.
2. **Design state once**: a live view for current ops + a log for history.
3. **Write navigation primitives first** (`_resolve`, `_resolve_parent`,
   `_walk_files`). Features become 3–6 lines each.
4. **Every mutation does two writes**: update the live tree *and* append to the
   log (a delete is a `None` tombstone at the current version).
5. **Bump the global version on content mutations only.**

Same machine as banking and KV. Different skin. You've now seen all three.
