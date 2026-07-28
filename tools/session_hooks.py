"""What Claude Code's session hooks run. One script, two subcommands.

Both hooks exist because of recorded incidents, which is the only bar a hook
should clear — it fires with no explanation attached, so a nice-to-have is not
enough.

**`primer`**: nothing guaranteed `.state.md` was read, and a session that
skipped it re-derived what it says — transcript mining attributed ~11% of
active time to re-orientation
(`docs/findings/2026.07.27-session-time-is-generation-not-tools.md`).

**`tree`**: a 99-file uncommitted sweep discovered on arrival, 23 commits
sitting local because "commit" was read as "done", and the work loop
self-blocking on a dirty tree after a usage halt. Silence when clean is the
point — a hook that speaks every turn is ignored on the turn it matters.

Deliberately not here: anything that runs the suite. The gate is the gate, it
is ~35 seconds, and a hook that runs it turns every stop into a wait.

The commands are jq-free on purpose. This is a Windows-first repo and Git Bash
ships no jq, so the hook that depends on it is the hook that silently does
nothing.

    python tools/session_hooks.py primer
    python tools/session_hooks.py tree
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parent.parent)

STATE = Path("docs/.state.md")

PRIMER_HEADER = "Repo state, generated into `docs/.state.md` by `uv run nox -s docs`:\n\n"


def _git(*args: str) -> str:
    """`git args`, or `""` on any failure — a hook must not fail the session."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def primer() -> dict[str, object]:
    path = REPO_ROOT / STATE
    if not path.exists():
        # Silent rather than loud: a fresh clone before the first `nox -s docs`
        # is a legitimate state, and a session that opens with an error about
        # its own primer has been made worse, not better.
        return {}
    text = path.read_text(encoding="utf-8")
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": PRIMER_HEADER + text,
        }
    }


def _unpushed() -> int:
    """Commits on HEAD that the upstream branch does not have.

    Zero when there is no upstream — a branch nobody has pushed yet has no
    answer to this question, and guessing one would report the whole history
    as unpushed on every new branch.
    """
    if not _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").strip():
        return 0
    return len([line for line in _git("log", "--oneline", "@{u}..HEAD").splitlines() if line])


def tree() -> dict[str, object]:
    dirty = [line for line in _git("status", "--short").splitlines() if line.strip()]
    ahead = _unpushed()
    if not dirty and not ahead:
        return {}

    parts: list[str] = []
    if dirty:
        shown = ", ".join(line[3:].strip() for line in dirty[:5])
        more = f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else ""
        parts.append(f"{len(dirty)} uncommitted: {shown}{more}")
    if ahead:
        parts.append(f"{ahead} commit{'s' if ahead != 1 else ''} not pushed")
    return {"systemMessage": "git: " + "; ".join(parts)}


COMMANDS = {"primer": primer, "tree": tree}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in COMMANDS:
        print(f"usage: session_hooks.py {{{'|'.join(COMMANDS)}}}", file=sys.stderr)
        return 2
    payload = COMMANDS[args[0]]()
    if payload:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
