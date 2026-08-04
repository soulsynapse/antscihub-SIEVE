"""Mine Claude Code session transcripts for where wall-clock time went.

The transcripts under `~/.claude/projects/<this repo>/` record every tool call
with a millisecond timestamp on the requesting assistant event and on the
result event. Pairing them by `tool_use_id` gives a duration per call, and
classifying calls by what they touched (source, tests, docs, the gate, git)
gives the split this repo's tooling decisions should be based on rather than
guessed at.

Accounting model, and what each number honestly is:

- **span** — first to last timestamp of a session.
- **idle** — any gap between consecutive events longer than `IDLE_CUTOFF`;
  the user walked away. Subtracted before anything is percentaged.
- **tool time** — union of the paired call intervals. A single call longer
  than `IDLE_CUTOFF` is capped and the excess counted as **waiting** (a
  permission prompt sitting unanswered is not the tool being slow).
- **residual** — active time not inside any tool interval: model thinking,
  response generation, and sub-cutoff user reading. Attributed to the phase
  of the *next* tool call, which is a heuristic and labelled as one.

Per-bucket sums count overlapping parallel calls at face value, so buckets can
sum past the union total; the union is the wall-clock truth.

    uv run python tools/transcript_stats.py           # summary to stdout
    uv run python tools/transcript_stats.py --json calls.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

#: A gap longer than this between events means the user was away, and a tool
#: call longer than this was waiting on a permission prompt, not executing.
IDLE_CUTOFF_S = 600.0

DEFAULT_ROOT = (
    Path.home() / ".claude" / "projects" / "C--Users-khnakam1-Documents-Code-antscihub-SIEVE"
)

#: Coarse phases the summary rolls buckets into. Order is display order.
PHASES = ("build", "tests", "gate", "docs", "git", "orient", "other")


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One paired tool invocation."""

    session: str
    name: str
    bucket: str
    phase: str
    start: float
    duration_s: float
    waiting_s: float
    detail: str


def _parse_ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _first_line(text: str, limit: int = 90) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line if len(line) <= limit else line[: limit - 1] + "…"


def _path_area(path: str) -> str:
    normalized = path.replace("\\", "/")
    for area in ("src", "tests", "docs"):
        if f"/{area}/" in normalized or normalized.startswith(f"{area}/"):
            return area
    return "other"


def classify(name: str, tool_input: dict[str, Any]) -> tuple[str, str, str]:
    """Return `(bucket, phase, detail)` for one tool call.

    The bucket is the fine-grained row in the report; the phase is the coarse
    build/tests/gate/docs/git/orient split residual time is attributed to.
    """
    if name in ("Bash", "PowerShell"):
        command = str(tool_input.get("command", ""))
        detail = _first_line(command)
        lowered = command.lower()
        if "doc_index" in lowered or "nox -s docs" in lowered or "nox.*docs" in lowered:
            return "shell:docs-index", "docs", detail
        if "nox" in lowered:
            return "shell:nox-gate", "gate", detail
        if any(tool in lowered for tool in ("pytest", "pyright", "ruff", "lint-imports")):
            return "shell:direct-checks", "gate", detail
        if lowered.startswith(("git", "gh ")) or " git " in f" {lowered}":
            return "shell:git", "git", detail
        if "uv sync" in lowered or "pip install" in lowered:
            return "shell:env", "other", detail
        return "shell:other", "other", detail

    if name in ("Edit", "Write", "NotebookEdit"):
        area = _path_area(str(tool_input.get("file_path", "")))
        phase = {"src": "build", "tests": "tests", "docs": "docs"}.get(area, "other")
        return f"edit:{area}", phase, str(tool_input.get("file_path", ""))

    if name == "Read":
        area = _path_area(str(tool_input.get("file_path", "")))
        phase = {"src": "build", "tests": "tests", "docs": "orient"}.get(area, "orient")
        return f"read:{area}", phase, str(tool_input.get("file_path", ""))

    if name in ("Grep", "Glob"):
        return "search", "orient", str(tool_input.get("pattern", ""))

    return f"tool:{name.lower()}", "other", ""


def _blocks(message: object) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
        return []
    content = cast(dict[Any, Any], message).get("content")
    if not isinstance(content, list):
        return []
    items = cast(list[Any], content)
    return [cast(dict[str, Any], item) for item in items if isinstance(item, dict)]


@dataclass(frozen=True, slots=True)
class SessionStats:
    """Accounting for one transcript file."""

    calls: list[ToolCall]
    timestamps: list[float]

    @property
    def span_s(self) -> float:
        return self.timestamps[-1] - self.timestamps[0] if len(self.timestamps) > 1 else 0.0

    @property
    def idle_s(self) -> float:
        pairs = zip(self.timestamps, self.timestamps[1:], strict=False)
        return sum(gap for a, b in pairs if (gap := b - a) > IDLE_CUTOFF_S)

    @property
    def active_s(self) -> float:
        return self.span_s - self.idle_s

    def tool_union_s(self) -> float:
        """Wall clock covered by at least one running tool."""
        intervals = sorted((c.start, c.start + c.duration_s) for c in self.calls)
        total, cursor = 0.0, float("-inf")
        for start, end in intervals:
            if end <= cursor:
                continue
            total += end - max(start, cursor)
            cursor = end
        return total

    def residual_by_phase(self) -> dict[str, float]:
        """Active time outside every tool interval, attributed to the phase of
        the next call — thinking about a test edit counts toward tests."""
        residual: defaultdict[str, float] = defaultdict(float)
        covered_until = self.timestamps[0] if self.timestamps else 0.0
        for call in sorted(self.calls, key=lambda c: c.start):
            gap = call.start - covered_until
            if 0.0 < gap <= IDLE_CUTOFF_S:
                residual[call.phase] += gap
            covered_until = max(covered_until, call.start + call.duration_s)
        return residual


def read_session(path: Path) -> SessionStats:
    """Pair every tool_use with its tool_result in one transcript."""
    pending: dict[str, tuple[str, float, str, str, str]] = {}
    calls: list[ToolCall] = []
    timestamps: list[float] = []

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                event = cast(dict[str, Any], json.loads(line))
            except json.JSONDecodeError:
                continue
            if event.get("type") not in ("assistant", "user"):
                continue
            raw_ts = event.get("timestamp")
            if not isinstance(raw_ts, str):
                continue
            ts = _parse_ts(raw_ts)
            timestamps.append(ts)

            for block in _blocks(event.get("message")):
                kind = block.get("type")
                if kind == "tool_use":
                    call_id = str(block.get("id", ""))
                    name = str(block.get("name", ""))
                    raw_input = block.get("input")
                    tool_input: dict[str, Any] = (
                        cast(dict[str, Any], raw_input) if isinstance(raw_input, dict) else {}
                    )
                    bucket, phase, detail = classify(name, tool_input)
                    pending[call_id] = (name, ts, bucket, phase, detail)
                elif kind == "tool_result":
                    entry = pending.pop(str(block.get("tool_use_id", "")), None)
                    if entry is None:
                        continue
                    name, start, bucket, phase, detail = entry
                    raw = max(0.0, ts - start)
                    duration = min(raw, IDLE_CUTOFF_S)
                    calls.append(
                        ToolCall(
                            session=path.stem,
                            name=name,
                            bucket=bucket,
                            phase=phase,
                            start=start,
                            duration_s=duration,
                            waiting_s=raw - duration,
                            detail=detail,
                        )
                    )

    timestamps.sort()
    return SessionStats(calls=calls, timestamps=timestamps)


def _fmt_h(seconds: float) -> str:
    return f"{seconds / 3600:.1f} h"


def summarize(sessions: list[SessionStats]) -> str:
    """Render the whole-corpus report."""
    calls = [c for s in sessions for c in s.calls]
    active = sum(s.active_s for s in sessions)
    idle = sum(s.idle_s for s in sessions)
    tool_union = sum(s.tool_union_s() for s in sessions)
    waiting = sum(c.waiting_s for c in calls)
    residual_total = max(0.0, active - tool_union)

    by_bucket: defaultdict[str, list[ToolCall]] = defaultdict(list)
    for call in calls:
        by_bucket[call.bucket].append(call)

    phase_tool: defaultdict[str, float] = defaultdict(float)
    for call in calls:
        phase_tool[call.phase] += call.duration_s
    phase_residual: defaultdict[str, float] = defaultdict(float)
    for session in sessions:
        for phase, seconds in session.residual_by_phase().items():
            phase_residual[phase] += seconds
    # The per-session residual attribution can overcount against the union
    # accounting; scale it so the phases sum to the honest residual total.
    attributed = sum(phase_residual.values())
    scale = residual_total / attributed if attributed > 0 else 0.0

    lines = [
        f"{len(sessions)} sessions, {len(calls)} paired tool calls",
        f"span {_fmt_h(active + idle)}  =  active {_fmt_h(active)}"
        f"  +  idle(>10 min gaps) {_fmt_h(idle)}",
        f"active  =  tools {_fmt_h(tool_union)}  +  model/user residual {_fmt_h(residual_total)}"
        f"   (plus {_fmt_h(waiting)} waiting on prompts, capped out of tool time)",
        "",
        "## Coarse phases (tool time + attributed residual, % of active)",
        "",
        "| Phase | Tools | Residual | Total | % |",
        "|---|---|---|---|---|",
    ]
    for phase in PHASES:
        tool_s = phase_tool.get(phase, 0.0)
        res_s = phase_residual.get(phase, 0.0) * scale
        total = tool_s + res_s
        pct = 100.0 * total / active if active else 0.0
        lines.append(
            f"| {phase} | {_fmt_h(tool_s)} | {_fmt_h(res_s)} | {_fmt_h(total)} | {pct:.0f}% |"
        )

    lines += [
        "",
        "## Buckets by tool wall-clock",
        "",
        "| Bucket | Calls | Time | Median s |",
        "|---|---|---|---|",
    ]
    ranked = sorted(by_bucket.items(), key=lambda kv: -sum(c.duration_s for c in kv[1]))
    for bucket, group in ranked:
        durations = sorted(c.duration_s for c in group)
        median = durations[len(durations) // 2]
        lines.append(f"| {bucket} | {len(group)} | {_fmt_h(sum(durations))} | {median:.1f} |")

    lines += ["", "## Longest individual calls", ""]
    for call in sorted(calls, key=lambda c: -c.duration_s)[:15]:
        lines.append(f"- {call.duration_s:6.0f} s  {call.bucket:<20} {call.detail}")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", type=Path, help="also dump every paired call as JSON")
    args = parser.parse_args(argv)

    files = sorted(cast(Path, args.root).glob("*.jsonl"))
    if not files:
        print(f"transcript_stats: no transcripts under {args.root}", file=sys.stderr)
        return 1

    sessions = [read_session(path) for path in files]
    sessions = [s for s in sessions if s.timestamps]
    print(summarize(sessions))

    if args.json:
        records = [
            {
                "session": c.session,
                "name": c.name,
                "bucket": c.bucket,
                "phase": c.phase,
                "duration_s": round(c.duration_s, 3),
                "waiting_s": round(c.waiting_s, 3),
                "detail": c.detail,
            }
            for s in sessions
            for c in s.calls
        ]
        cast(Path, args.json).write_text(json.dumps(records, indent=1), encoding="utf-8")
        print(f"transcript_stats: wrote {len(records)} calls to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
