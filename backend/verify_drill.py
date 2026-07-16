"""Dev tool: run a drill's REFERENCE solution against its own LEVELS.

    python verify_drill.py banking

Exits non-zero if any check fails — used to prove the test suites are correct
before shipping. Uses only the stdlib, so plain `python3` is fine.
"""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness import matches, show  # noqa: E402


def main():
    slug = sys.argv[1]
    drill = importlib.import_module(f"drills.{slug}")
    namespace = {}
    exec(compile(drill.REFERENCE, "<ref>", "exec"), namespace)
    cls = namespace[drill.ENTRYPOINT]

    total = passed = 0
    failures = []
    for level in drill.LEVELS:
        for tf in level["tests"]:
            try:
                checks = tf(cls)
            except Exception as exc:  # noqa: BLE001
                failures.append((level["name"], tf.__name__, "EXCEPTION", str(exc)))
                continue
            for label, expected, actual in checks:
                total += 1
                if matches(expected, actual):
                    passed += 1
                else:
                    failures.append((level["name"], tf.__name__, label,
                                     f"expected {show(expected)} got {show(actual)}"))

    print(f"{slug}: {passed}/{total} checks passed")
    for lvl, test, label, detail in failures:
        print(f"  FAIL [{lvl}] {test} :: {label} — {detail}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
