"""ADR-0010 tripwire: hash per top-level def, static on purpose — a tool
module imports its solvers, and a check that imported it could not run where
the solvers are not installed.

Watches every file the contract names, given as paths or globs. Globs because
a contract that lists its files stops covering the next one added, silently —
which is how `tools/` went unwatched while only the experiment was named.

Keys are qualified by the file they came from, so two tools defining `_field`
are two entries rather than one that flickers.

Hashes are CR-stripped so autocrlf-only checkouts don't trip.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import tomllib
from pathlib import Path

from importlinter import Contract, ContractCheck, fields, output

RECORD_HINT = "uv run python -m checks.adr0010"

ROOT = Path(__file__).resolve().parent.parent


def expand(patterns: list[str], root: Path = ROOT) -> list[Path]:
    """The files a contract's patterns name, sorted and deduplicated.

    A pattern matching nothing is left to the caller to notice: an empty
    baseline is louder than a missing one, and both are visible at record.
    """
    found: set[Path] = set()
    for pattern in patterns:
        if any(ch in pattern for ch in "*?["):
            found.update(root.glob(pattern))
        else:
            found.add(root / pattern)
    return sorted(path for path in found if path.is_file())


def snapshot(paths: list[Path], root: Path = ROOT) -> dict:
    """{functions: {file:name -> hash}, versions: {file:tool -> version}}."""
    functions: dict[str, str] = {}
    versions: dict[str, object] = {}
    for path in paths:
        where = path.relative_to(root).as_posix()
        source = path.read_bytes().decode("utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                segment = ast.get_source_segment(source, node) or ""
                functions[f"{where}:{node.name}"] = hashlib.sha256(
                    segment.replace("\r", "").encode("utf-8")).hexdigest()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "Tool"):
                kw = {k.arg: k.value for k in node.keywords}
                name, version = kw.get("name"), kw.get("version")
                if (isinstance(name, ast.Constant)
                        and isinstance(version, ast.Constant)):
                    versions[f"{where}:{name.value}"] = version.value
    return {"functions": functions, "versions": versions}


class KeyVersionContract(Contract):
    """Fails when a watched tool no longer matches its recorded baseline."""

    tools_files = fields.ListField(subfield=fields.StringField())
    baseline_file = fields.StringField()

    def check(self, graph, verbose):
        current = snapshot(expand(list(self.tools_files)))
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
            f"baseline.")
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


def watched(root: Path = ROOT) -> tuple[list[str], Path]:
    """What the registered contract watches, read from `pyproject.toml`.

    Read rather than repeated: a recorder with its own list records a set the
    check does not test, and the two drift with nothing to say so.
    """
    config = tomllib.loads(
        (root / "pyproject.toml").read_bytes().decode("utf-8"))
    for contract in config["tool"]["importlinter"]["contracts"]:
        if contract.get("type") == "adr0010_key_version":
            return contract["tools_files"], root / contract["baseline_file"]
    raise SystemExit("no adr0010_key_version contract in pyproject.toml")


def record(patterns: list[str], baseline_file: Path) -> None:
    """Write the baseline — the author's act of affirming the current text."""
    paths = expand(patterns)
    current = snapshot(paths)
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    baseline_file.write_bytes(
        json.dumps(current, indent=1, sort_keys=True).encode("utf-8") + b"\n")
    versions = ", ".join(f"{k}@{v}" for k, v in
                         sorted(current["versions"].items()))
    print(f"recorded {len(current['functions'])} definitions across "
          f"{len(paths)} files ({versions}) -> {baseline_file}")


if __name__ == "__main__":
    record(*watched())
    sys.exit(0)
