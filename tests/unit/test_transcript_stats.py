"""The miner's numbers are only as good as its pairing and attribution.

Each test breaks for a distinct real reason: pairing by `tool_use_id` (not
adjacency), the idle cap that keeps a permission prompt from reading as a slow
tool, and the phase attribution that turns thinking-before-a-test-edit into
tests time. A wrong duration here silently misranks every tooling decision
the report exists to inform.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transcript_stats import IDLE_CUTOFF_S, classify, read_session


def _event(kind: str, ts: str, blocks: list[dict[str, Any]]) -> str:
    return json.dumps({"type": kind, "timestamp": ts, "message": {"content": blocks}})


def _use(call_id: str, name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    return {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}


def _result(call_id: str) -> dict[str, Any]:
    return {"type": "tool_result", "tool_use_id": call_id}


def _write(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestPairing:
    def test_duration_comes_from_the_matching_result_not_the_next_event(
        self, tmp_path: Path
    ) -> None:
        # Two calls issued together; results arrive out of order. Adjacency
        # would swap the durations, id-pairing must not.
        lines = [
            _event(
                "assistant",
                "2026-07-27T10:00:00.000Z",
                [
                    _use("a", "Bash", {"command": "uv run nox -s checks"}),
                    _use("b", "Bash", {"command": "git status"}),
                ],
            ),
            _event("user", "2026-07-27T10:00:05.000Z", [_result("b")]),
            _event("user", "2026-07-27T10:00:30.000Z", [_result("a")]),
        ]
        stats = read_session(_write(tmp_path, lines))
        by_bucket = {c.bucket: c.duration_s for c in stats.calls}
        assert by_bucket["shell:nox-gate"] == 30.0
        assert by_bucket["shell:git"] == 5.0

    def test_a_call_longer_than_the_cutoff_is_capped_into_waiting(self, tmp_path: Path) -> None:
        # 20 minutes between use and result is a permission prompt sitting
        # unanswered, not a 20-minute tool.
        lines = [
            _event(
                "assistant",
                "2026-07-27T10:00:00.000Z",
                [_use("a", "Bash", {"command": "uv run pytest"})],
            ),
            _event("user", "2026-07-27T10:20:00.000Z", [_result("a")]),
        ]
        stats = read_session(_write(tmp_path, lines))
        (call,) = stats.calls
        assert call.duration_s == IDLE_CUTOFF_S
        assert call.waiting_s == 1200.0 - IDLE_CUTOFF_S


class TestAttribution:
    def test_idle_gaps_leave_active_time_and_residual_lands_on_the_next_phase(
        self, tmp_path: Path
    ) -> None:
        # 60 s of thinking precedes a tests/ edit; then the user leaves for an
        # hour before a docs/ edit. The hour must count as idle, and a gap
        # containing idle must attribute *nothing* — thinking adjacent to an
        # absence cannot be told from the absence, so it is dropped rather
        # than guessed (rule 6 applied to the report itself).
        lines = [
            _event(
                "assistant",
                "2026-07-27T10:01:00.000Z",
                [_use("a", "Edit", {"file_path": "tests/unit/test_x.py"})],
            ),
            _event("user", "2026-07-27T10:01:01.000Z", [_result("a")]),
            _event(
                "assistant",
                "2026-07-27T11:01:11.000Z",
                [_use("b", "Edit", {"file_path": "docs/TODO.md"})],
            ),
            _event("user", "2026-07-27T11:01:12.000Z", [_result("b")]),
        ]
        # Session opens with a bare timestamped event so the first gap exists.
        lines.insert(0, _event("user", "2026-07-27T10:00:00.000Z", []))
        stats = read_session(_write(tmp_path, lines))
        assert stats.idle_s == 3610.0
        residual = stats.residual_by_phase()
        assert residual["tests"] == 60.0
        assert residual["docs"] == 0.0


class TestClassification:
    def test_the_gate_docs_and_source_buckets_are_told_apart(self) -> None:
        assert classify("Bash", {"command": "uv run nox -s checks"})[0:2] == (
            "shell:nox-gate",
            "gate",
        )
        assert classify("Bash", {"command": "uv run python tools/doc_index.py --check"})[1] == (
            "docs"
        )
        assert classify("Edit", {"file_path": "src/sieve/core/types.py"})[0:2] == (
            "edit:src",
            "build",
        )
        assert classify("Edit", {"file_path": r"C:\repo\docs\TODO.md"})[0:2] == (
            "edit:docs",
            "docs",
        )
