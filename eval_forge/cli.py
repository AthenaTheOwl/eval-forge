"""eval-forge CLI: init / run / gate / show.

    eval-forge init  --shape rag --config customer.yaml --out evals/
    eval-forge run   evals/pack.yaml --target examples/fixture_target --out reports/run.json
    eval-forge gate  reports/run.json [--baseline base.json] [--comment out.md]
    eval-forge show  [reports/run.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .gate import GateError, comment_markdown, gate_report, load_report
from .init import init_pack, load_config, write_pack
from .pack import PackError, load_pack
from .run import TargetError, run
from .show import render, show


def _cmd_init(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
        pack = init_pack(args.shape, config)
    except FileNotFoundError as err:
        # load_config raises with the missing config path in filename; init_pack's
        # unknown-shape message is already actionable, so pass it through as-is.
        if err.filename:
            print(f"error: config not found: {err.filename}", file=sys.stderr)
        else:
            print(f"error: {err}", file=sys.stderr)
        return 2
    except KeyError as err:
        # _fill raises KeyError when the config lacks a placeholder the template needs
        print(f"error: {err.args[0]}", file=sys.stderr)
        return 2
    except (PackError, ValueError) as err:
        # config is not a mapping, or the filled template fails validation
        print(f"error: {err}", file=sys.stderr)
        return 2
    out_path = write_pack(pack, args.out)
    print(f"wrote {out_path}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        report = run(args.pack, args.target, created_at=args.created_at)
    except (PackError, TargetError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(render(report))
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    try:
        report = load_report(args.report)
        baseline = load_report(args.baseline) if args.baseline else None
        verdict = gate_report(report, baseline=baseline, tolerance=args.tolerance)
    except GateError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    md = comment_markdown(report, verdict)
    if args.comment:
        out = Path(args.comment)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(md)
    return 0 if verdict["passed"] else 1


def _cmd_show(args: argparse.Namespace) -> int:
    return show(args.report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eval-forge", description=__doc__)
    parser.add_argument("--version", action="version", version=f"eval-forge {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="generate a pack from a template + config")
    p_init.add_argument("--shape", required=True, help="rag | agent | hybrid")
    p_init.add_argument("--config", required=True, help="customer config YAML")
    p_init.add_argument("--out", required=True, help="output dir for the pack")
    p_init.set_defaults(func=_cmd_init)

    p_run = sub.add_parser("run", help="run a pack against a fixture target")
    p_run.add_argument("pack", help="pack file or dir")
    p_run.add_argument("--target", required=True, help="fixture target file or dir")
    p_run.add_argument("--out", help="write the run report here (else print)")
    p_run.add_argument(
        "--created-at",
        default="1970-01-01T00:00:00Z",
        help="pinned timestamp for deterministic reports",
    )
    p_run.set_defaults(func=_cmd_run)

    p_gate = sub.add_parser("gate", help="pass/fail a run report; exit non-zero on fail")
    p_gate.add_argument("report", help="run report JSON")
    p_gate.add_argument("--baseline", help="baseline report for regression gating")
    p_gate.add_argument("--tolerance", type=float, default=0.0, help="allowed drop vs baseline")
    p_gate.add_argument("--comment", help="write PR-comment markdown here (else print)")
    p_gate.set_defaults(func=_cmd_gate)

    p_show = sub.add_parser("show", help="print the latest run report readably")
    p_show.add_argument("report", nargs="?", help="report path (default: latest under reports/)")
    p_show.set_defaults(func=_cmd_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # no-arg default: show the latest report
        return show(None)
    return args.func(args)
