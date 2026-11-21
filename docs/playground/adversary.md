# Where the contract's scheme does not hold

An adversary's reading of `contract.md`, `sim/store.py` and `sim/sim.py` at the commit this file lands in. Proofs are
scratch copies of the two scripts outside the repo (`Code/Scratch/sieve-adversary/p*.py`); line numbers are this commit's.

## Proved

1. **A second writer's checkpoint is lost to this writer's letting go.** `_make_room` lists manifests once
   (store.py:188), checks each victim against that stale set (:197), gives another writer a turn in `disk.size` (:199),
   then deletes (:202). Sequence (laptop, disk 700 MB): store B walks `energy`; store A walks `gray` with `keep`;
   inside A's letting go, after its listing, B checkpoints the entry A is about to delete. B's `checkpoint` returns,
   having found it on disk (:144); afterwards `B.gone()` holds that address. Breaks contract:48. `race`
   (sim.py:501-518) cannot express it: its other writer lists and deletes in one turn (:504-509) and never
   checkpoints. `drop` has the same window (store.py:135-136). Landing the manifest first protects only against a
   deleter that re-lists between its last look and its delete, and no list-then-delete is atomic on a folder.
2. **The chunk grid is not in the key, and O1 cannot see it.** The grid is the widest row of all tools (sim.py:201);
   `key` (:264-274) does not hold it; `truth` (:260) digests the chunk's index, not its rows. With `truth` also
   digesting the rows held (`chunk * rows`, `rows`): walk `energy`; add a tool with 8 MB rows reading `gray` (which
   contract:78-80 says changes nothing); rows a chunk go 10 to 8, `energy`'s key stays `a63115bd9f00`;
   `demand("energy", 3)` and `look("energy", 30)` both break O1. Contract:16 says the grid is fixed for the key.
3. **`Ask.flight` holds results outside the store, past the memory budget.** Every value one demand makes stays in
   `self.flight` (sim.py:300, :309) until the next demand; the reservation for it is released at :335 while the value
   stays alive; a whole tool reserves its output and one input (:318), but all its inputs stay in `flight`. A look at
   `track` row 1023 on a cold laptop: the store's peak is 3.00 GB of 3.0, values alive in `flight` or held come to
   10.37 GB. O5 (:538) counts only held and reserved. Breaks contract:23-24, :28, :61.
4. **The shipped run never makes room on disk, so nothing that lets go of disk is tested.** Over `torture`'s 150
   seeds (laptop, sim.py:562) the most disk asked for was 21.6 GB of 40 GB and `_make_room` let go 0 times. These
   mutants pass all 150 seeds: `_make_room` returning True (budget ignored); `_make_room` ignoring manifests (at a
   1 GB disk it is caught, seed 88, O3 on `mark-44` at op 50); `drop` deleting named entries (the sim never drops
   from disk: `evict`, :478, passes `"memory"`); `put` ignoring `spare` (contract:29-30). No oracle compares
   `disk.used()` with the budget (contract:32). One-line fix: `torture`'s profile
   `replace(PROFILES["laptop"], disk=1 * GB)`; at 1, 2 and 4 GB the unmutated contract and LRU schemes still pass.
5. **Restoring after a code or footage edit brings nothing back, and O3 hides it.** The snapshot is params only
   (sim.py:208-209). Checkpoint `track`, bump `detect`'s code (or change the footage), restore: 20 addresses named,
   0 checked, because O3 skips every address not in `good` (:526, :529). Contract:52-53 says restoring brings back
   the keys they answer. Nothing un-names a manifest (store.py has no call for it), so such entries hold disk budget
   for good, and contract:49's refusal is where enough of them end.
6. **A checkpoint the disk cannot hold is refused without the figures; that branch is dead.** `need` (store.py:145)
   sums named entries on disk, which already fit `used <= budget`, so `need > disk_budget` (:146, :150) cannot hold
   under one budget. Checkpoint `gray` (2.01 GB) on a 1 GB disk: "56 of 103 entries are not on disk", after 113 s of
   the three recompute rounds (sim.py:411), each letting go of loose entries. The price table already shows the case
   for a checkpoint that fits: laptop LRU "checkpoint the tracks" refused, "1658 of 2132 entries are not on disk",
   for about 26 MB of tracks on a 40 GB disk. Contract:46-47, :49-50.
7. **Parts a crash tears leak for good.** A crash between a write's two steps leaves `parts/<writer>-n` torn; nothing
   lists `parts/` (store.py:195 lists `entries/` only); its bytes count in `used()`. Forty crashed checkpoints of
   `gray`: 40 torn parts hold 800 MB of 800 MB used. O6 (sim.py:540) looks only at `entries/`.
8. **A plane is taken to disk at once.** Contract:31-32 says what disk takes at once is "a table or a signal and not
   a plane"; store.py:75 takes anything costing `SURE` times its write. In the 5.3K price, desktop takes 8 and hpc 5
   chunks of planes at once on first make.

## Lines of contract.md nothing does or nothing checks (proved by reading)

- :35-36, the append-to-a-log landing: store.py has no log.
- :54, gone at open: `Store.__init__` (store.py:42-50) does not look, nor does `reopen` (sim.py:486-488); `gone()`
  (store.py:165-167) tests presence, not wholeness, and gives addresses, not the checkpoint's name.
- :40-41, the monitor: `drop` (store.py:131-134) lets go of memory unsaid; `Refused` from `reserve` (:102) and
  `checkpoint` (:149-150) is not emitted; the sim hands no `emit` (sim.py:448), so nothing checks any of it.
- :14-15, the print's sampling: the sim's strong print is the content itself (sim.py:270); the odds a sampled print
  misses an edit are never drawn and its cost is not modelled.
- :64 and :65-67: `Ask` has no queue for what the user looks at; cores enter only as `speed` (sim.py:397).
- :66 against :71: pieces are a process each, and each reads memory off the machine, so N pieces hold N times the
  machine's memory. The sim's second stores (sim.py:497) each get all of `profile.memory`; none is checked alongside.
- :39 against :71: two stores on one folder may carry two overridden disk budgets; each `_make_room` keeps its own.

## Where the simulated disk is kinder than a real one (suspected)

- `Disk.rename` (sim.py:88-89) never fails. On Windows a rename over, or a delete of, a file another process holds open
  raises `PermissionError`; `_land` (store.py:176) and `_make_room` (:202) do not catch it, so `put` and `checkpoint`
  raise. Two writers that both saw `size` None (store.py:77) rename over each other, and `rename` does not take the old
  file's bytes off `total` (sim.py:81 against :89), so `used` drifts up.
- A crash falls only between a write's steps (sim.py:82-86), never after the rename with the data not yet flushed. NTFS
  journals metadata, not data; without a flush, power loss can leave a whole-looking name over zeros. `get`
  (store.py:57-64) trusts any file under `entries/`: no length or checksum is read back.
- What writers share is free and exact: `used()` (sim.py:145), the marks (:121-125), the floor (:133-137), and a rank
  rewritten on every read (:98). A real folder needs a walk or a per-process count for `used`, files for marks and
  floor, and a write per read for rank (last-access updates are off on many Windows volumes and on noatime mounts);
  ticks from two machines are not comparable. Budget and policy lean on these; the manifest guarantee does not.
- A write never meets a full disk (sim.py:80-86); a real one raises out of `put` and leaves a part as in 7.
- `names()` (sim.py:115-116) is an instant snapshot. SMB and NFS cache directory listings for seconds, so another
  machine's fresh manifest can be invisible to `named()`, widening 1 from an interleaving to a window of seconds.

## The price table

- The "worth" and "lru" columns change admission and eviction together (store.py:45, :71-76, :114, :123, :190). Keeping
  worth's admission and swapping GreedyDual-Size ranking for recency leaves the first walk and the disk held unchanged
  on all four profiles; GDS gains only "the same walk again" (laptop 0 against 16.9 s, usb-hdd 0 against 99.5) and loses
  the first nudge on usb-hdd (302.5 against 287.0) and hpc (275.8 against 262.4). The table supports not writing planes
  on first make; it does not support GreedyDual-Size over recency.
- No headline flipped under the guessed figures tried: hpc read 1000 and 3000 MB/s, write 1000, `file_s` 0.0015;
  laptop at desktop's disk figures; usb-hdd read 120. Under hpc read 3000 LRU's first nudge is half worth's (86.2
  against 172.7 s), a gap that already favours LRU at the guessed 300 (214.1 against 275.8).
- Suspected: on laptop at NVMe figures, worth's nudges grow 201, 237, 261 s repeating one act; not chased.
