---
title: detect re-derives as a centered tool
step: "04.8"
status: open
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
(`adr/ops-admission-is-two-tools.md`). The parity target is v2's `detect/`
**package output**, centered whole-record — what was tuned against — never
the trailing kernel (PLAN.md, Phase 4). If 04.5 flagged shared windowed-mean
machinery, this item designs `ops/`'s first admission with both signatures
in hand and the census test in the same commit; otherwise `ops/` stays
nonexistent.
