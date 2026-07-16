"""Drill registry — discovered dynamically from this directory.

Any ``<slug>.py`` module here (not starting with ``_``) that exposes the drill
contract (SLUG, TITLE, ENTRYPOINT, MARKDOWN, STARTER, REFERENCE, LEVELS) is a
drill. Discovery is filesystem-based so agent-generated drills appear with no
server restart. The three hand-written drills are ordered first.
"""

import importlib
import os
from glob import glob

DRILLS_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_ORDER = ["banking", "filesystem", "kvstore"]


def list_slugs():
    found = []
    for path in glob(os.path.join(DRILLS_DIR, "*.py")):
        name = os.path.basename(path)[:-3]
        if name.startswith("_"):
            continue
        found.append(name)
    core = [s for s in CORE_ORDER if s in found]
    rest = sorted(s for s in found if s not in CORE_ORDER)
    return core + rest


def load(slug):
    if slug not in list_slugs():
        raise KeyError(slug)
    mod = importlib.import_module(f"drills.{slug}")
    # Reload so a regenerated/edited drill file is always current.
    return importlib.reload(mod)
