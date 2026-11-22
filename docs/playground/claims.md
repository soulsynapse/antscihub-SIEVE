# Claims the playground leans on

Facts about the tree as it was observed, each with the files it is a fact about, what rests on
it, and the commit it was seen at. A list to recall by, checked by nothing: a claim is reread
against the tree before anything is built on it. A claim is an observation and not a wish.

- [held-appends] `held.py` appends to the held file in place when every record is kept and writes beside then replaces only on a rebuild; `load` stops at the first record that does not read. | files: sieve_player/held.py | leans: the contract allowing a tolerantly read log; the held file's slice onto the store | checked: baa3b208
- [ram-reported-only] Before `budget.py`, nothing sized a holder from the machine's RAM; `machine.py` reads it to report. | files: sieve_player/machine.py, sieve_player/budget.py | leans: slice 2 being the only place a limit meets the machine | checked: 75d866c6
- [store-names-nothing] `store.py` resolves the store's folder and sums what it holds; the names of files in it are made by `tools/_cutfile.py` and the decoder. | files: sieve_player/store.py | leans: where the on-disk store's folder sits beside what is there already | checked: baa3b208
- [bare-not-timed] `bare.py` never reads the plan's `timed`. | files: sieve_player/bare.py, sieve_player/plan.py | leans: the slice for a bare walk over cuts in time | checked: 75d866c6
- [footage-sampled] `footage_print` digests the size, the first and last `SLICE` bytes and `SAMPLES` slices at offsets fixed by the size. | files: sieve_player/decoder.py | leans: the torture's weak-print scheme no longer being today's; the whole-file hash to follow | checked: 69c9743b
- [limits-shared] `budget.limits` gives each holder today's constant where half the RAM has room for all and shrinks all in proportion where it has not; an env override sets its own holder's limit and shrinks no other. | files: sieve_player/budget.py | leans: O5 on a small machine until the holders are one store | checked: 12e8e0e0
