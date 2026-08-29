"""ADR-0010's tripwire: the tools' code moved and no author said so.

The ADR settles that a key folds a version its author bumps, and accepts
that nothing decides a bump for them — what it refuses is the hash as
arbiter, not as tripwire. This is the tripwire: a baseline records a hash
per top-level definition in the tools module, and the contract fails when
the code no longer matches it. The author answers by bumping the version
where the answer moved, and in either case re-records the baseline
(`uv run python -m checks.adr0010`) — both explicit acts, which is the
point. The hash decides nothing and never reaches a key.

Static on purpose: the tools module imports its solvers, and a check that
had to import them could not run where the solvers are not installed.
Hashes are taken per top-level def and class over text with carriage
returns stripped, so a checkout that changed only line endings does not
trip anything (the autocrlf note in CLAUDE.md, biting a third way).
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

from importlinter import Contract, ContractCheck, fields, output

RECORD_HINT = "uv run python -m checks.adr0010"


def snapshot(tools_file: Path) -> dict:
    """Per-definition hashes and the declared tool versions, from source.

    `functions` maps each top-level def or class to a hash of its text;
    `versions` maps each `Tool(name=..., version=...)` literal to its
    version, read so a failure can say whether a bump already happened.
    """
    source = tools_file.read_bytes().decode("utf-8")
    tree = ast.parse(source)
    functions = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            segment = ast.get_source_segment(source, node) or ""
            digest = hashlib.sha256(
                segment.replace("\r", "").encode("utf-8")).hexdigest()
            functions[node.name] = digest
    versions = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "Tool"):
            kw = {k.arg: k.value for k in node.keywords}
            name, version = kw.get("name"), kw.get("version")
            if (isinstance(name, ast.Constant)
                    and isinstance(version, ast.Constant)):
                versions[str(name.value)] = version.value
    return {"functions": functions, "versions": versions}


class KeyVersionContract(Contract):
    """Fails when the tools module no longer matches its recorded baseline."""

    tools_file = fields.StringField()
    baseline_file = fields.StringField()

    def check(self, graph, verbose):
        current = snapshot(Path(self.tools_file))
        base_path = Path(self.baseline_file)
        if not base_path.exists():
            return ContractCheck(kept=False, metadata={"unrecorded": True})
        baseline = json.loads(base_path.read_bytes().decode("utf-8"))
        names = set(current["functions"]) | set(baseline["functions"])
        changed = sorted(n for n in names if current["functions"].get(n)
                         != baseline["functions"].get(n))
        bumped = sorted(n for n, v in current["versions"].items()
                        if baseline["versions"].get(n) not in (None, v))
        return ContractCheck(kept=not changed,
                             metadata={"unrecorded": False,
                                       "changed": changed, "bumped": bumped})

    def render_broken_contract(self, check):
        if check.metadata.get("unrecorded"):
            output.print_error(
                f"ADR-0010: no baseline at {self.baseline_file}; "
                f"record one: {RECORD_HINT}")
            return
        changed = ", ".join(check.metadata["changed"])
        output.print_error(
            f"ADR-0010: the text of {changed} moved under the recorded "
            f"baseline ({self.tools_file}).")
        if check.metadata["bumped"]:
            output.print_error(
                "Versions already bumped since the baseline: "
                + ", ".join(check.metadata["bumped"]) + ".")
        else:
            output.print_error(
                "No tool's version changed with it. If an affected tool's "
                "answer moved, bump its version (ADR-0010).")
        output.print_error(
            f"Either way, affirm by re-recording: {RECORD_HINT}")


def record(tools_file: Path, baseline_file: Path) -> None:
    """Write the baseline — the author's act of affirming the current text."""
    current = snapshot(tools_file)
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    baseline_file.write_bytes(
        json.dumps(current, indent=1, sort_keys=True).encode("utf-8") + b"\n")
    versions = ", ".join(f"{k}@{v}" for k, v in
                         sorted(current["versions"].items()))
    print(f"recorded {len(current['functions'])} definitions "
          f"({versions}) -> {baseline_file}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    record(root / "experiments/tool-experiments/tools.py",
           root / "checks/adr0010-baseline.json")
    sys.exit(0)
