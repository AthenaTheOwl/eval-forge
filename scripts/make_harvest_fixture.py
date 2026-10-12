#!/usr/bin/env python3
"""Build a small git repo whose history exercises `eval-forge harvest`.

    python scripts/make_harvest_fixture.py <dir>

The repo holds one module, interval.py, and its tests. Its history:

    init: interval helpers                          root, no parent: not a candidate
    fix: clamp ignores the upper bound              valid: test fails before, passes after
    docs: say what interval.py is for               source only: not a candidate
    fix: width of an empty interval                 passes_before: the test already passed
    test: cover width of a reversed interval        tests only: not a candidate
    fix: overlaps checks both ends                  fails_after: the fix is wrong

Author, committer and dates are pinned, so the commit shas are the same on
every machine and examples/harvested_envs.yaml can be reproduced exactly.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PYTEST_INI = "[pytest]\naddopts = -p no:cacheprovider\n"

INTERVAL_V1 = '''\
def clamp(x, lo, hi):
    return max(lo, x)


def width(lo, hi):
    return abs(hi - lo)


def overlaps(a, b):
    return a[1] > b[0]
'''

TEST_WIDTH = '''\
from interval import width


def test_width():
    assert width(2, 5) == 3
'''

TEST_CLAMP = '''\
from interval import clamp


def test_clamp_pins_both_ends():
    assert clamp(-1, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
'''

TEST_WIDTH_EMPTY = '''\
from interval import width


def test_width_of_empty_interval():
    assert width(3, 3) == 0
'''

TEST_WIDTH_REVERSED = '''\
from interval import width


def test_width_of_reversed_interval():
    assert width(5, 2) == 3
'''

TEST_OVERLAPS = '''\
from interval import overlaps


def test_disjoint_intervals_do_not_overlap():
    assert not overlaps((5, 6), (0, 1))


def test_nested_intervals_overlap():
    assert overlaps((0, 5), (2, 3))
'''


def _interval(clamp_fixed: bool, docstring: bool, width_doc: bool, overlaps_v2: bool) -> str:
    text = INTERVAL_V1
    if clamp_fixed:
        text = text.replace("return max(lo, x)", "return min(max(lo, x), hi)")
    if width_doc:
        text = text.replace(
            "def width(lo, hi):\n",
            'def width(lo, hi):\n    """Length of [lo, hi]; zero when lo == hi."""\n',
        )
    if overlaps_v2:
        # the wrong fix: compares a's start with b's end in the wrong direction
        text = text.replace("return a[1] > b[0]", "return a[1] > b[0] and a[0] > b[1]")
    if docstring:
        text = '"""Closed-interval helpers."""\n\n\n' + text
    return text


# (subject, files written in that commit)
HISTORY: list[tuple[str, dict[str, str]]] = [
    (
        "init: interval helpers",
        {
            "pytest.ini": PYTEST_INI,
            "interval.py": _interval(False, False, False, False),
            "tests/test_width.py": TEST_WIDTH,
        },
    ),
    (
        "fix: clamp ignores the upper bound",
        {
            "interval.py": _interval(True, False, False, False),
            "tests/test_clamp.py": TEST_CLAMP,
        },
    ),
    (
        "docs: say what interval.py is for",
        {"interval.py": _interval(True, True, False, False)},
    ),
    (
        "fix: width of an empty interval",
        {
            "interval.py": _interval(True, True, True, False),
            "tests/test_width_empty.py": TEST_WIDTH_EMPTY,
        },
    ),
    (
        "test: cover width of a reversed interval",
        {"tests/test_width_reversed.py": TEST_WIDTH_REVERSED},
    ),
    (
        "fix: overlaps checks both ends",
        {
            "interval.py": _interval(True, True, True, True),
            "tests/test_overlaps.py": TEST_OVERLAPS,
        },
    ),
]


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def build(path: Path | str) -> dict[str, str]:
    """Create the fixture repo at `path`; return {commit subject: sha}."""
    repo = Path(path)
    if repo.exists() and any(repo.iterdir()):
        raise SystemExit(f"refusing to build into a non-empty directory: {repo}")
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "core.autocrlf", "false")

    shas: dict[str, str] = {}
    for day, (subject, files) in enumerate(HISTORY, start=1):
        for rel, text in files.items():
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
            _git(repo, "add", "--", rel)
        stamp = f"2026-01-{day:02d}T12:00:00+00:00"
        env = dict(
            os.environ,
            GIT_AUTHOR_NAME="Fixture Author",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_AUTHOR_DATE=stamp,
            GIT_COMMITTER_NAME="Fixture Author",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_DATE=stamp,
        )
        _git(repo, "commit", "-q", "-m", subject, env=env)
        shas[subject] = _git(repo, "rev-parse", "HEAD")
    return shas


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: make_harvest_fixture.py <dir>", file=sys.stderr)
        return 2
    shas = build(argv[0])
    for subject, sha in shas.items():
        print(f"{sha[:12]}  {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
