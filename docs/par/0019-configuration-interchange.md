# PAR-0019 — Configuration interchange

Status: Proposed
Date: 2026-08-03

Owed: 20260803T065949Z: rationale for configuration interchange — when two configurations the user could have authored are the same measurement, and what carries across when they swap; spans three cases the design currently treats separately: two methods answering one operation (their param surfaces need a correspondence or a swap resets the user's configuration and, worse, an equivalence measurement compares arbitrary configurations and means nothing — invariant 4 cannot pose its question without it, and Exchange 8's clustering assumes matched settings), a canonical param space per operation rather than global (a universal parameter vocabulary is Exchange 7's unchangeable-algebra failure at n=0; a knob that does not map is a finding surfaced, never dropped) — with the params themselves living on the method rather than in a partition of the tool's model, so what this record owns is the correspondence between them and never their placement, and interchange between levels of the pipeline — a 4× downsample against a block size of 4 — which is neither an implementation choice nor a param mapping but a measured equivalence between graph shapes, outside what PAR-0005 lets the executor do silently, and engineered by hand in v1 where `block_size` deliberately tracks scale rather than moving with it; the seam against PAR-0012 is this record's first question, with the candidate line being that PAR-0012 owns substitutions the user never sees while this owns equivalences the user is offered and chooses (PAR-0011 then selecting among them); governs until acceptance: DESIGN-SESSION.md Exchange 8, and PAR-0006 on Farneback/DIS/RAFT as authored params rather than one equivalence class

Stated 2026-08-03 in the tool-contract scoping session, where it surfaced from
the tool contract's `Params` shape question (whether `Params` is flat or
partitioned into an operation-level surface and an implementation-level one)
and outgrew it.
