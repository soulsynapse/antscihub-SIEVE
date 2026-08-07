---
title: mutual/ comes over with its layer
step: "03.1"
status: done
gated_on: nothing
done_when: "uv run pytest -q && uv run lint-imports"
opened: 2026-08-07
---

# mutual/ comes over with its layer

All four modules of `mutual/` verbatim (PLAN.md, porting discipline), because
`decode/` reads three of them and 02.1 cannot be verbatim without them. The
package is 682 lines whose only dependency outside the standard library is
`psutil`, and its only internal edge is `shares -> machine`, so there is no
part of it that arrives speculatively.

It brings its seat in the stack with it, and that is the half of this item
that is not a copy:

- `.importlinter` gains `sieve.mutual` between the `decode | storage` row and
  `sieve.core`, which is where v2 seats it, and `core-purity`'s
  `source_modules` gains it — v2's contract is named "core and mutual import
  no toolkit, no codec, no processes" and the second half of that name is the
  reason `machine.py` may read `psutil` while `core/` may not.
- The comment above the layers block currently says whether `mutual` ports at
  all is Phase 5's question. PLAN.md answered it; the comment is wrong once
  this lands, not merely stale, and it goes.
- `LAYER_ORDER` in `scripts/doc_index.py` follows `.importlinter` by its own
  docstring, so it gains the same entry or `SCAFFOLD.md` refuses to render.
- `psutil` joins `pyproject.toml`'s runtime dependencies with the reason
  beside it, since `machine.py` is shipped code and not a test helper.

The three test files are v2's own and port unchanged. `test_concurrency.py`
is not among them: it imports `sieve.gui.concurrency`, so its subject is a
consumer that does not exist here.

## The blocker, and what review did with it (2026-08-07)

The port landed byte-identical and the criterion failed on one assertion, so
the run stopped here rather than edit a ported test — correctly, and the
review reproduced the failure before ruling.

`test_machine.py`'s `assert before > 64 * MIB` measures the pytest session's
import footprint, not the resolver: it passes under the whole suite and fails
under the three-file selection the original `done_when` named, and v2's bare
session cleared it by 20 KB
(`findings/2026.08.07-the-rss-floor-measures-the-test-session-not-the-resolver.md`).

Of the run's three exits, review took the one that edits neither a ported
test nor an assertion: `done_when` now names the whole suite. That is a
strictly larger selection — no case is dropped and nothing is loosened — and
it leaves the ported file byte-identical, which is the claim the port exists
to make. The floor's own worth is a decision about a v2 test rather than a
criterion defect, so it goes to `the-rss-floor-decides-its-fate.md` with the
authorization to make the edit, instead of being settled here by deletion.
