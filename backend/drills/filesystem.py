"""Drill A — In-Memory File System (version-based history variant)."""

from harness import ANY, Pred  # noqa: F401

SLUG = "filesystem"
TITLE = "In-Memory File System"
DIFFICULTY = "Ramp ICA archetype · 4 levels"
ENTRYPOINT = "FileSystem"

MARKDOWN = r"""
# In-Memory File System

Paths are unix-like, e.g. `/a/b/c`. The root `/` always exists. A **global
version counter** starts at `0` and increments by 1 on every successful
**content mutation** (`add_file`, `delete`, `copy`, `move`). `mkdir` does *not*
bump it. `add_file` returns the version its write landed at — you'll need those
numbers at Level 4.

---

## Level 1 — Directories & files

- **`mkdir(path) -> bool`** — create a directory. Parent must exist and be a
  directory. `False` if it already exists, the parent is missing, or the parent
  is a file.
- **`add_file(path, size) -> int | None`** — create (or overwrite) a file with
  integer `size >= 0`. Returns the **version number** of this write, or `None`
  if the parent is missing / is a file, or `path` is an existing directory.
- **`get_file_size(path) -> int | None`** — current size, or `None` if `path`
  isn't a file.

## Level 2 — Aggregates & search

- **`get_dir_size(path) -> int | None`** — total size of every file under this
  directory, recursively. `None` if `path` isn't a directory.
- **`find(prefix) -> list[str]`** — every **file path** that starts with
  `prefix`, sorted ascending. (`find("/")` returns all files.)

## Level 3 — Move, copy, delete

- **`delete(path) -> bool`** — remove a file or a whole directory subtree.
  `False` if `path` doesn't exist.
- **`copy(src, dst) -> bool`** — deep-copy a file or directory subtree to `dst`.
  `src` must exist; `dst` must **not** already exist; `dst`'s parent must be an
  existing directory. Otherwise `False`.
- **`move(src, dst) -> bool`** — like `copy` then `delete src`. `False` on the
  same conditions, or if `dst` is inside `src`.

## Level 4 — Versioned history

- **`get_file_size(path, at_version) -> int | None`** — the file's size **as of
  that version**, or `None` if it wasn't a file at that version (never created
  yet, or already deleted). The 1-arg form still returns the current size.

---

> **Read all four levels first.** L4's versioned read means a scalar `size` per
> node won't survive — store a per-file **write log** of `(version, size)`
> checkpoints from L1, and the historical query is one binary search.
"""

STARTER = '''\
import bisect


class FileSystem:
    def __init__(self):
        pass

    # ---- Level 1 ----
    def mkdir(self, path):
        pass

    def add_file(self, path, size):
        pass

    def get_file_size(self, path, at_version=None):
        pass

    # ---- Level 2 ----
    def get_dir_size(self, path):
        pass

    def find(self, prefix):
        pass

    # ---- Level 3 ----
    def delete(self, path):
        pass

    def copy(self, src, dst):
        pass

    def move(self, src, dst):
        pass
'''

REFERENCE = '''\
import bisect


class FileSystem:
    def __init__(self):
        self.root = {"type": "dir", "children": {}}
        self.version = 0
        self.file_log = {}      # path -> [(version, size_or_None)]  (None = deleted)

    # ---------- path helpers ----------
    def _parts(self, path):
        return [p for p in path.split("/") if p != ""]

    def _resolve(self, path):
        node = self.root
        for p in self._parts(path):
            if node["type"] != "dir" or p not in node["children"]:
                return None
            node = node["children"][p]
        return node

    def _resolve_parent(self, path):
        parts = self._parts(path)
        if not parts:
            return None, None
        node = self.root
        for p in parts[:-1]:
            if node["type"] != "dir" or p not in node["children"]:
                return None, None
            node = node["children"][p]
        if node["type"] != "dir":
            return None, None
        return node, parts[-1]

    def _walk_files(self, node, prefix, out):
        for name, child in node["children"].items():
            p = prefix + "/" + name
            if child["type"] == "file":
                out.append((p, child["size"]))
            else:
                self._walk_files(child, p, out)

    def _clone(self, node):
        if node["type"] == "file":
            return {"type": "file", "size": node["size"]}
        return {"type": "dir",
                "children": {k: self._clone(v) for k, v in node["children"].items()}}

    def _log(self, path, size):
        self.file_log.setdefault(path, []).append((self.version, size))

    # ---------- Level 1 ----------
    def mkdir(self, path):
        parent, name = self._resolve_parent(path)
        if parent is None or name in parent["children"]:
            return False
        parent["children"][name] = {"type": "dir", "children": {}}
        return True

    def add_file(self, path, size):
        parent, name = self._resolve_parent(path)
        if parent is None:
            return None
        existing = parent["children"].get(name)
        if existing is not None and existing["type"] == "dir":
            return None
        self.version += 1
        parent["children"][name] = {"type": "file", "size": size}
        self._log(path, size)
        return self.version

    def get_file_size(self, path, at_version=None):
        if at_version is None:
            node = self._resolve(path)
            if node is None or node["type"] != "file":
                return None
            return node["size"]
        log = self.file_log.get(path)
        if not log:
            return None
        vs = [v for v, _ in log]
        i = bisect.bisect_right(vs, at_version) - 1
        if i < 0:
            return None
        return log[i][1]      # size, or None if that checkpoint was a delete

    # ---------- Level 2 ----------
    def get_dir_size(self, path):
        node = self._resolve(path)
        if node is None or node["type"] != "dir":
            return None
        files = []
        self._walk_files(node, path.rstrip("/"), files)
        return sum(sz for _, sz in files)

    def find(self, prefix):
        files = []
        self._walk_files(self.root, "", files)
        return sorted(p for p, _ in files if p.startswith(prefix))

    # ---------- Level 3 ----------
    def delete(self, path):
        parent, name = self._resolve_parent(path)
        if parent is None or name not in parent["children"]:
            return False
        node = parent["children"][name]
        self.version += 1
        if node["type"] == "file":
            self._log(path, None)
        else:
            files = []
            self._walk_files(node, path.rstrip("/"), files)
            for fp, _ in files:
                self._log(fp, None)
        del parent["children"][name]
        return True

    def copy(self, src, dst):
        node = self._resolve(src)
        if node is None:
            return False
        dparent, dname = self._resolve_parent(dst)
        if dparent is None or dname in dparent["children"]:
            return False
        self.version += 1
        clone = self._clone(node)
        dparent["children"][dname] = clone
        if clone["type"] == "file":
            self._log(dst, clone["size"])
        else:
            files = []
            self._walk_files(clone, dst.rstrip("/"), files)
            for fp, sz in files:
                self._log(fp, sz)
        return True

    def move(self, src, dst):
        node = self._resolve(src)
        if node is None:
            return False
        if dst == src or dst.startswith(src.rstrip("/") + "/"):
            return False
        sparent, sname = self._resolve_parent(src)
        dparent, dname = self._resolve_parent(dst)
        if sparent is None or dparent is None or dname in dparent["children"]:
            return False
        self.version += 1
        if node["type"] == "file":
            self._log(src, None)
            self._log(dst, node["size"])
        else:
            old_files = []
            self._walk_files(node, src.rstrip("/"), old_files)
            for fp, _ in old_files:
                self._log(fp, None)
            new_files = []
            self._walk_files(node, dst.rstrip("/"), new_files)
            for fp, sz in new_files:
                self._log(fp, sz)
        del sparent["children"][sname]
        dparent["children"][dname] = node
        return True
'''


# ------------------------------------------------------------------ Level 1
def l1_mkdir_addfile(C):
    fs = C()
    return [
        ("mkdir /a -> True", True, fs.mkdir("/a")),
        ("mkdir /a again -> False", False, fs.mkdir("/a")),
        ("mkdir /x/y (no parent) -> False", False, fs.mkdir("/x/y")),
        ("add /a/f size 10 -> version 1", 1, fs.add_file("/a/f", 10)),
        ("get_file_size /a/f -> 10", 10, fs.get_file_size("/a/f")),
        ("get_file_size /a (a dir) -> None", None, fs.get_file_size("/a")),
        ("get_file_size missing -> None", None, fs.get_file_size("/a/none")),
        ("add file under missing parent -> None", None, fs.add_file("/z/f", 5)),
        ("overwrite /a/f size 20 -> version 2", 2, fs.add_file("/a/f", 20)),
        ("get_file_size /a/f -> 20", 20, fs.get_file_size("/a/f")),
        ("mkdir over existing file -> False", False, fs.mkdir("/a/f")),
    ]


# ------------------------------------------------------------------ Level 2
def l2_dir_size(C):
    fs = C()
    fs.mkdir("/a")
    fs.mkdir("/a/b")
    fs.add_file("/a/f1", 10)
    fs.add_file("/a/b/f2", 20)
    fs.add_file("/a/b/f3", 5)
    return [
        ("dir_size /a -> 35", 35, fs.get_dir_size("/a")),
        ("dir_size /a/b -> 25", 25, fs.get_dir_size("/a/b")),
        ("dir_size / -> 35", 35, fs.get_dir_size("/")),
        ("dir_size of a file -> None", None, fs.get_dir_size("/a/f1")),
        ("dir_size missing -> None", None, fs.get_dir_size("/nope")),
    ]


def l2_find(C):
    fs = C()
    fs.mkdir("/a")
    fs.mkdir("/a/b")
    fs.add_file("/a/apple", 1)
    fs.add_file("/a/app", 1)
    fs.add_file("/a/b/apex", 1)
    fs.add_file("/a/banana", 1)
    return [
        ("find /a/ap -> [app, apple]", ["/a/app", "/a/apple"], fs.find("/a/ap")),
        ("find / -> all files sorted",
         ["/a/app", "/a/apple", "/a/b/apex", "/a/banana"], fs.find("/")),
        ("find /a/b/ (dir scope) -> [/a/b/apex]", ["/a/b/apex"], fs.find("/a/b/")),
        ("find /a/b -> prefix also matches banana",
         ["/a/b/apex", "/a/banana"], fs.find("/a/b")),
        ("find no match -> []", [], fs.find("/zzz")),
    ]


# ------------------------------------------------------------------ Level 3
def l3_delete(C):
    fs = C()
    fs.mkdir("/a")
    fs.add_file("/a/f", 10)
    fs.add_file("/a/g", 20)
    return [
        ("delete /a/f -> True", True, fs.delete("/a/f")),
        ("get_file_size /a/f -> None", None, fs.get_file_size("/a/f")),
        ("dir_size /a -> 20", 20, fs.get_dir_size("/a")),
        ("delete missing -> False", False, fs.delete("/a/f")),
        ("delete dir /a -> True", True, fs.delete("/a")),
        ("dir_size /a -> None", None, fs.get_dir_size("/a")),
    ]


def l3_copy(C):
    fs = C()
    fs.mkdir("/a")
    fs.add_file("/a/f", 10)
    fs.mkdir("/a/sub")
    fs.add_file("/a/sub/g", 5)
    fs.mkdir("/dst")
    return [
        ("copy /a -> /dst/a -> True", True, fs.copy("/a", "/dst/a")),
        ("copied file size -> 10", 10, fs.get_file_size("/dst/a/f")),
        ("copied nested file size -> 5", 5, fs.get_file_size("/dst/a/sub/g")),
        ("dir_size /dst -> 15", 15, fs.get_dir_size("/dst")),
        ("original still intact -> 15", 15, fs.get_dir_size("/a")),
        ("copy onto existing -> False", False, fs.copy("/a", "/dst/a")),
        ("copy missing src -> False", False, fs.copy("/nope", "/dst/x")),
        ("copy to missing parent -> False", False, fs.copy("/a", "/zzz/a")),
    ]


def l3_move(C):
    fs = C()
    fs.mkdir("/a")
    fs.add_file("/a/f", 10)
    fs.mkdir("/b")
    fs.mkdir("/c")
    return [
        ("move /a/f -> /b/f -> True", True, fs.move("/a/f", "/b/f")),
        ("src file gone -> None", None, fs.get_file_size("/a/f")),
        ("dst file present -> 10", 10, fs.get_file_size("/b/f")),
        ("move dir /a -> /b/a -> True", True, fs.move("/a", "/b/a")),
        ("moved-away dir gone -> None", None, fs.get_dir_size("/a")),
        ("move into own subtree -> False", False, fs.move("/c", "/c/inner")),
    ]


# ------------------------------------------------------------------ Level 4
def l4_versioned(C):
    fs = C()
    fs.mkdir("/a")
    v1 = fs.add_file("/a/f", 10)     # v1
    v2 = fs.add_file("/a/f", 20)     # v2 (overwrite)
    v3 = fs.add_file("/a/g", 5)      # v3
    fs.delete("/a/f")                # v4
    return [
        ("first write is version 1", 1, v1),
        ("overwrite is version 2", 2, v2),
        ("second file is version 3", 3, v3),
        ("size /a/f @v1 -> 10", 10, fs.get_file_size("/a/f", 1)),
        ("size /a/f @v2 -> 20", 20, fs.get_file_size("/a/f", 2)),
        ("size /a/f @v3 (unchanged) -> 20", 20, fs.get_file_size("/a/f", 3)),
        ("size /a/f @v4 (deleted) -> None", None, fs.get_file_size("/a/f", 4)),
        ("size /a/f now (deleted) -> None", None, fs.get_file_size("/a/f")),
        ("size /a/g @v2 (not yet created) -> None", None, fs.get_file_size("/a/g", 2)),
        ("size /a/g @v3 -> 5", 5, fs.get_file_size("/a/g", 3)),
        ("size /a/f @v0 -> None", None, fs.get_file_size("/a/f", 0)),
    ]


LEVELS = [
    {"name": "Level 1 — Directories & files",
     "tests": [l1_mkdir_addfile]},
    {"name": "Level 2 — Aggregates & search",
     "tests": [l2_dir_size, l2_find]},
    {"name": "Level 3 — Move, copy, delete",
     "tests": [l3_delete, l3_copy, l3_move]},
    {"name": "Level 4 — Versioned history",
     "tests": [l4_versioned]},
]


# ---------- filesystem visualiser (runs a fixed demo on the user's class) ----
DEMO_SCRIPT = [
    ("mkdir", "/projects"),
    ("mkdir", "/projects/ramp"),
    ("add_file", "/projects/ramp/main.py", 1200),
    ("add_file", "/projects/ramp/README.md", 340),
    ("mkdir", "/projects/ramp/tests"),
    ("add_file", "/projects/ramp/tests/test_bank.py", 800),
    ("copy", "/projects/ramp", "/backup"),
    ("add_file", "/projects/notes.txt", 50),
    ("move", "/projects/notes.txt", "/projects/ramp/notes.txt"),
]


def render_state(cls):
    """Run DEMO_SCRIPT on a fresh instance and rebuild the tree via the public
    API (find + get_file_size), so the visual reflects the user's own code."""
    fs = cls()
    log = []
    for op in DEMO_SCRIPT:
        method, args = op[0], op[1:]
        try:
            res = getattr(fs, method)(*args)
        except Exception as exc:  # noqa: BLE001
            res = f"ERR: {exc}"
        log.append(f"{method}({', '.join(map(str, args))}) -> {res}")

    try:
        files = fs.find("/")
    except Exception:  # noqa: BLE001
        files = []

    tree = {}
    for p in sorted(files):
        try:
            size = fs.get_file_size(p)
        except Exception:  # noqa: BLE001
            size = None
        parts = [x for x in p.split("/") if x]
        node = tree
        for d in parts[:-1]:
            node = node.setdefault(d, {"__dir__": True, "children": {}})["children"]
        node[parts[-1]] = {"__file__": True, "size": size}
    return {"tree": tree, "demo": log}
