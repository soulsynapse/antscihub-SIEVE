---
title: detect re-derives as a centered tool
step: "04.8"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_detect_tool.py tests/unit/test_detection.py tests/unit/test_wavelet.py -q"
opened: 2026-08-06
---

# detect re-derives as a centered tool

`tools/detect.py`: a centered windowed tool on the 01.3 lookahead contract,
absorbing v2's `detect/` composition (`adr/detector-is-a-node.md`). The
wavelet and detection-chain math lands inside this module — w0 constant,
threading pool, measured semantics intact — and `test_wavelet.py` and
`test_detection.py` port pointing at the new home
(`adr/ops-admission-is-two-tools.md`).

The parity target is settled and it is v2's `detect/` **package output**,
centered whole-record — what was tuned against — never the trailing kernel
(PLAN.md, Phase 4). The golden is minted by 03.7's mechanism with the
regeneration command naming the package entry point, and a run that finds
itself comparing against `filters/detect.py` has taken the wrong artifact:
that kernel is the shape the two-sided window replaced, so matching it would
certify the bug rather than the tool. If 04.5 flagged shared windowed-mean
machinery, this item designs `ops/`'s first admission with both signatures
in hand and the census test in the same commit; otherwise `ops/` stays
nonexistent.
