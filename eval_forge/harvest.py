"""Harvest graded environments from a repository's own fix commits.

A fix commit that touches both source and tests carries its own grader: the
tests it adds or changes should fail on the parent commit and pass on the fix.
`harvest` checks that claim for each candidate and keeps the pairs where it
holds. Each kept pair is an environment case:

    {id, base_sha, fix_sha, fail_to_pass, test_cmd}

Start an agent at base_sha; grade it with test_cmd, which runs the
fail_to_pass tests.

For each candidate, in one temporary git worktree:

1. check out the parent, overlay the commit's test files, and run the touched
   test modules. They must fail.
2. check out the commit and run them again. They must pass.

Each side runs `runs` times. A side whose runs disagree drops the pair as
`flaky`. Otherwise the pair is kept, or dropped as `passes_before` (the tests
do not exercise the fix) or `fails_after` (the environment is broken).

Harvesting executes the target repository's tests. Point it only at
repositories you trust.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

DEFAULT_TEST_CMD = "python -m pytest -q {tests}"
TESTS_TOKEN = "{tests}"
DROP_REASONS = ("passes_before", "fails_after", "flaky")
TEST_DIRS = frozenset({"test", "tests"})


class HarvestError(RuntimeError):
    """The repo or the test command cannot be harvested at all."""


def is_test_module(path: str) -> bool:
    """A file the test runner collects: test_*.py or *_test.py."""
    name = PurePosixPath(path).name
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def is_test_path(path: str) -> bool:
    """A test module, or any file under a test/ or tests/ directory (conftest, data)."""
    parent_dirs = PurePosixPath(path).parts[:-1]
    return is_test_module(path) or any(part in TEST_DIRS for part in parent_dirs)


@dataclass
class Candidate:
    sha: str
    parent: str
    test_files: list[str]  # overlaid onto the parent: changed test-side files present at sha
    test_modules: list[str]  # what {tests} expands to


@dataclass
class HarvestResult:
    kept: list[dict[str, Any]] = field(default_factory=list)
    dropped: list[tuple[str, str]] = field(default_factory=list)  # (sha, reason)

    def summary(self) -> str:
        counts = Counter(reason for _, reason in self.dropped)
        line = f"kept {len(self.kept)}, dropped {len(self.dropped)}"
        parts = ", ".join(f"{r} {counts[r]}" for r in DROP_REASONS if counts[r])
        return f"{line} ({parts})" if parts else line


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip().splitlines()
        raise HarvestError(f"git {args[0]} failed: {detail[-1] if detail else 'no output'}")
    return proc.stdout


def _changed_paths(repo: Path, sha: str) -> list[tuple[str, str]]:
    """(status, path) for every file the commit changes against its parent."""
    out = _git(repo, "diff-tree", "-r", "-z", "--no-commit-id", "--name-status", "--no-renames", sha)
    fields = [f for f in out.split("\0") if f]
    return list(zip(fields[0::2], fields[1::2]))


def candidates(repo: Path | str, max_commits: int = 50) -> list[Candidate]:
    """Non-merge commits among the last `max_commits` that touch a source file
    and a test module, oldest first. Root commits have no parent and are skipped."""
    repo = Path(repo)
    log = _git(repo, "log", f"--max-count={max_commits}", "--no-merges", "--format=%H %P", "HEAD")
    found: list[Candidate] = []
    for line in log.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, parent = parts
        changes = _changed_paths(repo, sha)
        present = sorted(p for status, p in changes if status != "D")
        test_files = [p for p in present if is_test_path(p)]
        test_modules = [p for p in test_files if is_test_module(p)]
        touches_source = any(not is_test_path(p) for _, p in changes)
        if test_modules and touches_source:
            found.append(Candidate(sha, parent, test_files, test_modules))
    found.reverse()
    return found


def _render(template: list[str], tests: list[str]) -> list[str]:
    argv: list[str] = []
    for token in template:
        if token == TESTS_TOKEN:
            argv.extend(tests)
        else:
            argv.append(token)
    return argv


def _executable(argv: list[str]) -> list[str]:
    # a leading `python` runs under the interpreter running eval-forge, which is
    # the one that has pytest installed
    if argv and argv[0] in ("python", "python3"):
        return [sys.executable, *argv[1:]]
    return argv


def _checkout(worktree: Path, sha: str) -> None:
    _git(worktree, "checkout", "-q", "-f", "--detach", sha)
    _git(worktree, "clean", "-ffdxq")


def _run_once(worktree: Path, argv: list[str], timeout: float) -> bool:
    _git(worktree, "clean", "-ffdxq")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(
            argv,
            cwd=worktree,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False  # a hang is a failure on either side
    except OSError as err:
        raise HarvestError(f"cannot launch test command {argv[0]!r}: {err}") from err
    return proc.returncode == 0


def _side(worktree: Path, argv: list[str], runs: int, timeout: float) -> bool | None:
    """True if every run passed, False if every run failed, None if they disagreed."""
    outcomes = {_run_once(worktree, argv, timeout) for _ in range(runs)}
    return outcomes.pop() if len(outcomes) == 1 else None


def check_pair(
    worktree: Path, cand: Candidate, argv: list[str], runs: int, timeout: float
) -> str | None:
    """None if the pair is a valid environment, else the drop reason."""
    _checkout(worktree, cand.parent)
    _git(worktree, "checkout", "-q", cand.sha, "--", *cand.test_files)
    before = _side(worktree, argv, runs, timeout)
    if before is None:
        return "flaky"
    if before:
        return "passes_before"
    _checkout(worktree, cand.sha)
    after = _side(worktree, argv, runs, timeout)
    if after is None:
        return "flaky"
    if not after:
        return "fails_after"
    return None


def env_case(cand: Candidate, template: list[str]) -> dict[str, Any]:
    return {
        "id": f"fix-{cand.sha[:12]}",
        "base_sha": cand.parent,
        "fix_sha": cand.sha,
        "fail_to_pass": list(cand.test_modules),
        "test_cmd": shlex.join(_render(template, cand.test_modules)),
    }


def harvest(
    repo: Path | str,
    test_cmd: str = DEFAULT_TEST_CMD,
    max_commits: int = 50,
    runs: int = 2,
    timeout: float = 300.0,
) -> HarvestResult:
    """Check every candidate fix commit in `repo`; keep the fail-to-pass pairs."""
    try:
        template = shlex.split(test_cmd)
    except ValueError as err:
        raise HarvestError(f"cannot parse --test-cmd: {err}") from err
    if TESTS_TOKEN not in template:
        raise HarvestError(f"--test-cmd must contain {TESTS_TOKEN} as its own word")
    if max_commits < 1 or runs < 1:
        raise HarvestError("--max-commits and --runs must be at least 1")

    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise HarvestError(f"repo not found: {repo}")
    try:
        _git(repo, "rev-parse", "--git-dir")
    except HarvestError:
        raise HarvestError(f"not a git repository: {repo}") from None

    result = HarvestResult()
    found = candidates(repo, max_commits)
    if not found:
        return result

    tmp = Path(tempfile.mkdtemp(prefix="ef-harvest-"))
    worktree = tmp / "wt"
    _git(repo, "worktree", "add", "-q", "--detach", str(worktree), found[0].parent)
    try:
        for cand in found:
            argv = _executable(_render(template, cand.test_modules))
            reason = check_pair(worktree, cand, argv, runs, timeout)
            if reason:
                result.dropped.append((cand.sha, reason))
            else:
                result.kept.append(env_case(cand, template))
    finally:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            capture_output=True,
        )
        shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True)
    return result


def write_envs(cases: list[dict[str, Any]], out: Path | str) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(cases, sort_keys=False), encoding="utf-8", newline="\n")
    return out
