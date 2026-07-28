"""What Claude Code's session hooks run. One script, three subcommands.

Both hooks exist because of recorded incidents, which is the only bar a hook
should clear — it fires with no explanation attached, so a nice-to-have is not
enough.

**`primer`**: nothing guaranteed `.state.md` was read, and a session that
skipped it re-derived what it says — transcript mining attributed ~11% of
active time to re-orientation
(`docs/findings/2026.07.27-session-time-is-generation-not-tools.md`).

**`subagent`**: a subagent's report lands in the caller's context whole, so a
loose return contract is paid for on every call. Three critics returned ~25k
tokens between them on 2026.07.28 by reporting the comments that *passed* and
appending ten open questions each. `SubagentStop` carries no token counts, so
size of `last_assistant_message` is the proxy — it is also the number that
actually matters, being the context cost rather than the billing one. This
logs every return and speaks only above the threshold, because "remember to
refine this" fired on every call is the nag `tree` is written to avoid.

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
    python tools/session_hooks.py subagent   # reads the hook payload on stdin
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

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


#: Characters of returned text above which a subagent's contract is too loose.
#: A report that names only its findings and writes the detail to a file comes
#: back in one line; 2000 is generous against that and well under the ~9000 a
#: single unconstrained critic returned.
RETURN_BUDGET = 2000

RETURNS_LOG = Path(".claude/subagent-returns.jsonl")


def subagent(payload: dict[str, object] | None = None) -> dict[str, object]:
    if payload is None:
        # `json.loads` is typed as returning `Any`; the cast is what keeps this
        # inside the repo's no-ignores rule, and the isinstance is what keeps a
        # payload shape the harness changes from raising in a hook.
        loaded = cast(object, json.loads(sys.stdin.read() or "{}"))
        payload = cast(dict[str, object], loaded) if isinstance(loaded, dict) else {}
    text = str(payload.get("last_assistant_message", ""))
    kind = str(payload.get("agent_type", "?"))

    log = REPO_ROOT / RETURNS_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"agent": kind, "chars": len(text)}) + "\n")

    if len(text) <= RETURN_BUDGET:
        return {}
    return {
        "systemMessage": (
            f"{kind} returned {len(text)} chars (budget {RETURN_BUDGET}). "
            "Tighten its return contract: report failures only, write detail to a file."
        )
    }


COMMANDS = {"primer": primer, "tree": tree, "subagent": subagent}


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
