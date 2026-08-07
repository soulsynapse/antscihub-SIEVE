"""Extract the dependency graph of src/sieve into graph-system/data.js.

Stdlib-only, run as: uv run python graph-system/extract.py

Emits window.GRAPH_DATA for viewer.html: the containment tree
(package -> module -> symbol), module->module import edges carrying the
imported names, intra-module symbol edges, layer bands parsed live from
.importlinter (so they never drift), per-module annotations scraped from
docs/SCAFFOLD.md, and the Projected section as ghost nodes.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
OUT = Path(__file__).resolve().parent / "data.js"


def parse_importlinter(path: Path) -> tuple[list[list[str]], set[tuple[str, str]]]:
    """Return (layer bands, top first) and the ignore_imports exception pairs.

    Manual parse: configparser would fold the indented comment lines inside
    multiline values into the values themselves.
    """
    bands: list[list[str]] = []
    exceptions: set[tuple[str, str]] = set()
    section = ""
    key = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            section = stripped.strip("[]")
            key = ""
            continue
        if not raw[0].isspace() and "=" in raw:
            key, _, rest = stripped.partition("=")
            key = key.strip()
            stripped = rest.strip()
            if not stripped:
                continue
        if section.endswith(":layers") and key == "layers":
            bands.append([m.strip().strip("()") for m in stripped.split("|")])
        elif key == "ignore_imports" and "->" in stripped:
            a, _, b = stripped.partition("->")
            exceptions.add((a.strip(), b.strip()))
    return bands, exceptions


def parse_scaffold(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Return {module path: annotation} for the Built and Projected trees."""
    built: dict[str, str] = {}
    projected: dict[str, str] = {}
    target: dict[str, str] | None = None
    in_fence = False
    line_re = re.compile(r"^(src/sieve/\S+\.py)\s+#\s+(.*)$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## Built"):
            target = built
        elif raw.startswith("## Projected"):
            target = projected
        elif raw.startswith("## "):
            target = None
        elif raw.startswith("```"):
            in_fence = not in_fence
        elif in_fence and target is not None and (m := line_re.match(raw)):
            target[m.group(1)] = m.group(2).strip()
    return built, projected


def module_id(rel: Path) -> str:
    return ".".join(rel.with_suffix("").parts)


def band_of(mod: str, bands: list[list[str]]) -> int | None:
    """Band index (0 = top) of the longest matching layer prefix."""
    best: tuple[int, int] | None = None
    for i, band in enumerate(bands):
        for layer in band:
            if (mod == layer or mod.startswith(layer + ".")) and (
                best is None or len(layer) > best[1]
            ):
                best = (i, len(layer))
    return best[0] if best else None


def band_package(mod: str, bands: list[list[str]]) -> str | None:
    for band in bands:
        for layer in band:
            if mod == layer or mod.startswith(layer + "."):
                return layer
    return None


class ModuleInfo:
    def __init__(self, mid: str, rel: Path, source: str) -> None:
        self.id = mid
        self.rel = rel
        self.loc = source.count("\n") + 1
        self.tree = ast.parse(source)
        self.doc = (ast.get_docstring(self.tree) or "").split("\n", 1)[0]
        # alias in this module's namespace -> (resolved target module, original name)
        self.import_names: dict[str, tuple[str, str]] = {}
        self.imports: dict[str, list[str]] = {}  # target module -> imported names
        self.external: set[str] = set()
        self.symbols: list[dict[str, Any]] = []
        self.calls: list[list[str]] = []
        self.uses: list[list[str]] = []


def resolve(target: str, mod_ids: set[str]) -> str | None:
    if target in mod_ids:
        return target
    if f"{target}.__init__" in mod_ids:
        return f"{target}.__init__"
    return None


def collect_imports(info: ModuleInfo, mod_ids: set[str]) -> None:
    for node in ast.walk(info.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("sieve"):
                    tgt = resolve(alias.name, mod_ids)
                    if tgt:
                        leaf = alias.name.rsplit(".", 1)[-1]
                        info.imports.setdefault(tgt, []).append(leaf)
                        info.import_names[alias.asname or alias.name] = (tgt, leaf)
                else:
                    info.external.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level or not base.startswith("sieve"):
                if base and base != "__future__":
                    info.external.add(base.split(".")[0])
                continue
            for alias in node.names:
                tgt = resolve(f"{base}.{alias.name}", mod_ids) or resolve(base, mod_ids)
                if tgt:
                    info.imports.setdefault(tgt, []).append(alias.name)
                    info.import_names[alias.asname or alias.name] = (tgt, alias.name)


def collect_symbols(info: ModuleInfo) -> None:
    defs = [
        n
        for n in info.tree.body
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]
    def_names = {n.name for n in defs}
    for node in defs:
        info.symbols.append(
            {
                "name": node.name,
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "line": node.lineno,
                "loc": (node.end_lineno or node.lineno) - node.lineno + 1,
                "doc": (ast.get_docstring(node) or "").split("\n", 1)[0],
            }
        )
        called: set[str] = set()
        used: set[tuple[str, str]] = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                if sub.id in def_names and sub.id != node.name:
                    called.add(sub.id)
                elif sub.id in info.import_names:
                    tgt, orig = info.import_names[sub.id]
                    used.add((tgt, orig))
        info.calls.extend([node.name, c] for c in sorted(called))
        info.uses.extend([node.name, tgt, orig] for tgt, orig in sorted(used))


def main() -> int:
    bands, exceptions = parse_importlinter(REPO / ".importlinter")
    built_notes, projected_notes = parse_scaffold(REPO / "docs" / "SCAFFOLD.md")

    infos: dict[str, ModuleInfo] = {}
    for py in sorted((SRC / "sieve").rglob("*.py")):
        rel = py.relative_to(SRC)
        mid = module_id(rel)
        infos[mid] = ModuleInfo(mid, rel, py.read_text(encoding="utf-8"))
    mod_ids = set(infos)

    for info in infos.values():
        collect_imports(info, mod_ids)
        collect_symbols(info)

    modules: dict[str, Any] = {}
    edges: list[dict[str, Any]] = []
    for info in infos.values():
        pkg = info.id.rsplit(".", 1)[0]
        modules[info.id] = {
            "package": pkg,
            "layerPackage": band_package(info.id, bands),
            "band": band_of(info.id, bands),
            "loc": info.loc,
            "isInit": info.id.endswith(".__init__"),
            "ghost": False,
            "doc": info.doc,
            "annotation": built_notes.get(info.rel.as_posix(), ""),
            "external": sorted(info.external),
            "symbols": info.symbols,
            "calls": info.calls,
            "uses": info.uses,
        }
        src_band = band_of(info.id, bands)
        src_pkg = band_package(info.id, bands)
        for tgt, names in sorted(info.imports.items()):
            src_key = info.id.removesuffix(".__init__")
            tgt_key = tgt.removesuffix(".__init__")
            dst_band = band_of(tgt, bands)
            dst_pkg = band_package(tgt, bands)
            status = "ok"
            if (src_key, tgt_key) in exceptions:
                status = "exception"
            elif (
                src_band is not None
                and dst_band is not None
                and src_pkg != dst_pkg
                and dst_band <= src_band
            ):
                status = "up"
            edges.append(
                {"src": info.id, "dst": tgt, "names": sorted(set(names)), "status": status}
            )

    ghosts: dict[str, Any] = {}
    for path, note in projected_notes.items():
        mid = module_id(Path(path).relative_to("src"))
        ghosts[mid] = {
            "package": mid.rsplit(".", 1)[0],
            "layerPackage": band_package(mid, bands),
            "band": band_of(mid, bands),
            "loc": 0,
            "isInit": False,
            "ghost": True,
            "doc": "",
            "annotation": note,
            "external": [],
            "symbols": [],
            "calls": [],
            "uses": [],
        }

    data = {
        "meta": {
            "root": "sieve",
            "bands": bands,
            "moduleCount": len(modules),
            "ghostCount": len(ghosts),
            "edgeCount": len(edges),
        },
        "modules": modules,
        "ghosts": ghosts,
        "edges": edges,
    }
    OUT.write_text("window.GRAPH_DATA = " + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
    n_exc = sum(1 for e in edges if e["status"] == "exception")
    n_up = sum(1 for e in edges if e["status"] == "up")
    print(
        f"{OUT.name}: {len(modules)} modules, {len(ghosts)} ghosts, {len(edges)} edges "
        f"({n_exc} exception, {n_up} up)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
