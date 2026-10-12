import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from eval_forge.cli import main
from eval_forge.harvest import candidates, is_test_module, is_test_path

REPO = Path(__file__).resolve().parent.parent
ENV_SCHEMA = json.loads((REPO / "schemas" / "env_case.schema.json").read_text(encoding="utf-8"))
EXAMPLE = REPO / "examples" / "harvested_envs.yaml"

VALID = "fix: clamp ignores the upper bound"
PASSES_BEFORE = "fix: width of an empty interval"
FAILS_AFTER = "fix: overlaps checks both ends"


def _load_builder():
    path = REPO / "scripts" / "make_harvest_fixture.py"
    spec = importlib.util.spec_from_file_location("make_harvest_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fixture_repo(tmp_path_factory):
    path = tmp_path_factory.mktemp("harvest") / "repo"
    shas = _load_builder().build(path)
    return path, shas


def _harvest_cli(repo, out, *extra):
    return subprocess.run(
        [sys.executable, "-m", "eval_forge", "harvest", "--repo", str(repo), "--out", str(out), *extra],
        cwd=REPO,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def harvested(fixture_repo):
    repo, shas = fixture_repo
    out = repo.parent / "envs.yaml"
    proc = _harvest_cli(repo, out)
    return proc, yaml.safe_load(out.read_text(encoding="utf-8")), shas


def test_harvest_keeps_one_and_names_why_two_dropped(harvested):
    proc, _, _ = harvested
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines()[-1] == "kept 1, dropped 2 (passes_before 1, fails_after 1)"


def test_each_dropped_commit_carries_its_reason(harvested):
    proc, _, shas = harvested
    assert f"dropped {shas[PASSES_BEFORE][:12]}  passes_before" in proc.stdout
    assert f"dropped {shas[FAILS_AFTER][:12]}  fails_after" in proc.stdout


def test_kept_case_starts_at_the_parent_and_grades_with_the_failing_test(harvested):
    _, envs, shas = harvested
    assert envs == [
        {
            "id": f"fix-{shas[VALID][:12]}",
            "base_sha": shas["init: interval helpers"],
            "fix_sha": shas[VALID],
            "fail_to_pass": ["tests/test_clamp.py"],
            "test_cmd": "python -m pytest -q tests/test_clamp.py",
        }
    ]


def test_envs_validate_against_the_schema(harvested):
    _, envs, _ = harvested
    jsonschema.validate(instance=envs, schema=ENV_SCHEMA)
    for case in envs:
        jsonschema.validate(instance=case, schema=ENV_SCHEMA)


def test_schema_rejects_a_case_with_no_fail_to_pass_tests(harvested):
    _, envs, _ = harvested
    broken = dict(envs[0], fail_to_pass=[])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=[broken], schema=ENV_SCHEMA)


def test_committed_example_matches_a_fresh_harvest(harvested):
    # the fixture pins author and dates, so its shas are the same everywhere
    _, envs, _ = harvested
    assert yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")) == envs


def test_candidates_need_both_a_source_change_and_a_test_module(fixture_repo):
    repo, shas = fixture_repo
    found = candidates(repo)
    assert [c.sha for c in found] == [shas[VALID], shas[PASSES_BEFORE], shas[FAILS_AFTER]]
    assert found[0].parent == shas["init: interval helpers"]


def test_max_commits_limits_the_scan(fixture_repo):
    repo, shas = fixture_repo
    assert [c.sha for c in candidates(repo, max_commits=1)] == [shas[FAILS_AFTER]]


def test_harvest_leaves_the_repo_as_it_found_it(harvested, fixture_repo):
    repo, shas = fixture_repo
    worktrees = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert worktrees.count("worktree ") == 1
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert head == shas[FAILS_AFTER]
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout
    assert status == ""


def test_runs_that_disagree_drop_the_pair_as_flaky(fixture_repo, tmp_path):
    # a test command that alternates fail, pass, fail, pass: no side is stable
    repo, _ = fixture_repo
    flip = tmp_path / "flip.py"
    state = tmp_path / "state"
    flip.write_text(
        "import pathlib, sys\n"
        f"p = pathlib.Path({state.as_posix()!r})\n"
        "n = int(p.read_text()) if p.exists() else 0\n"
        "p.write_text(str(n + 1))\n"
        "sys.exit(0 if n % 2 else 1)\n",
        encoding="utf-8",
    )
    proc = _harvest_cli(repo, tmp_path / "envs.yaml", "--test-cmd", f"python {shlex.quote(flip.as_posix())} {{tests}}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines()[-1] == "kept 0, dropped 3 (flaky 3)"
    assert yaml.safe_load((tmp_path / "envs.yaml").read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "path, module, test_side",
    [
        ("tests/test_clamp.py", True, True),
        ("pkg/clamp_test.py", True, True),
        ("tests/conftest.py", False, True),
        ("test/data/cases.json", False, True),
        ("interval.py", False, False),
        ("src/testing_utils.py", False, False),
    ],
)
def test_test_path_classification(path, module, test_side):
    assert is_test_module(path) is module
    assert is_test_path(path) is test_side


def test_harvest_rejects_a_directory_that_is_not_a_repo(tmp_path, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    code = main(["harvest", "--repo", str(plain), "--out", str(tmp_path / "envs.yaml")])
    assert code == 2
    assert "not a git repository" in capsys.readouterr().err


def test_harvest_requires_a_tests_slot_in_the_command(fixture_repo, tmp_path, capsys):
    repo, _ = fixture_repo
    code = main(
        ["harvest", "--repo", str(repo), "--test-cmd", "python -m pytest -q",
         "--out", str(tmp_path / "envs.yaml")]
    )
    assert code == 2
    assert "{tests}" in capsys.readouterr().err
