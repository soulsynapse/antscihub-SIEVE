"""Secret: how a named thing round-trips to a file under a directory —
repo-root resolution, the name-to-path mapping (with its escape guard), and
reading/writing text. Content encoding (JSON shape, or anything else) is
not this module's concern; it only ever sees a name and a string. Any
domain that needs "save this by name, load it back, list what's saved"
builds on this instead of walking to ``pyproject.toml`` itself.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    for candidate in (Path(__file__).resolve(), *Path(__file__).resolve().parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml found above {Path(__file__).resolve()}")


def path_for(name: str, directory: Path, suffix: str = ".json") -> Path:
    if "/" in name or "\\" in name or name in (".", ".."):
        raise ValueError(f"not a valid name: {name!r}")
    return directory / f"{name}{suffix}"


def save_text(name: str, text: str, directory: Path, suffix: str = ".json") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = path_for(name, directory, suffix)
    path.write_text(text, encoding="utf-8")
    return path


def load_text(name: str, directory: Path, suffix: str = ".json") -> str:
    return path_for(name, directory, suffix).read_text(encoding="utf-8")


def list_names(directory: Path, suffix: str = ".json") -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob(f"*{suffix}"))
