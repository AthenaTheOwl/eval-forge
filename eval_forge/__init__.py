"""eval-forge — an eval-pack runner.

Load a typed eval pack, run its cases against a target, emit a typed run
report, and gate on it. The pack shape is the load-bearing contract; the
runner and the gate both consume it.

The deterministic check primitives mirror the semantics of the
trace-to-eval-harness sibling repo (contains / refusal / citation-span /
abstention). v0.1 vendors them so the package stands alone and deploys with
no network and no extra resolution; the lineage is documented in pyproject.toml.
"""

__version__ = "0.1.0"
