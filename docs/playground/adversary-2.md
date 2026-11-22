# Adversary 2: folder.py against the contract on a real disk

`docs/playground/sim/folder.py` and `store.py` at bb0c6da0; Windows 11, local NTFS, `.venv`'s Python
3.13. Scripts: `C:\Users\khnakam1\Documents\Code\Scratch\sieve-adversary-2\` (outside the repo, each
removes its temp folder); quoted lines are their output. Most damaging first.

1. **Proved: exceptions out of `drop`, `checkpoint` and a room-making `put` under plain two-process
   use.** `lock()` catches only `FileExistsError` from `os.mkdir` (folder.py:143-146); a `mkdir`
   meeting the other process's pending `rmdir` raises `PermissionError` [WinError 5]. No crash or
   stale lock needed. `s5b_lock_contention.py`, two processes calling `drop` for 15 s:
   `(exceptions, drops) per process = [({'PermissionError': 654}, 12010), ({'PermissionError': 495},
   11965)]`. Every `_lock()` caller (store.py:123, 145, 205) is exposed; at 145 it leaves the
   checkpoint pending.

2. **Proved: exceptions out of `put` while another process lands or deletes.** `used()` tests
   `exists` then `getsize` (folder.py:116-117); every `_land` elsewhere makes and renames away a part
   in that gap. `s6_used.py`: `walks of used() against a process landing and deleting:
   {'FileNotFoundError': 369} out of 7138`. Reached from `put` under `worth=True` (store.py:76) and
   `_make_room` (store.py:203, 213, 220), and after every lock, which clears `_counted` (folder.py:154).

3. **Proved: a checkpoint that returned is left pending, then swept with its entries.** A process
   holding the pending manifest open makes `os.replace` refuse; `rename` passes over it and deletes
   the finished part (folder.py:58-63), `checkpoint` returns (store.py:153), `manifest()` is None,
   `gone()` is silent, and past `GRACE` the sweep deletes it (store.py:206-209). The holder can be
   another store's `named()`. `s1_manifest_held.py`: `held: checkpoint returned, manifest()=None,
   after 2000s and 10 puts 3/3 named entries gone`; `raced: 4/300 checkpoints returned but left
   pending while another process ran named()`. The same refusal makes `release_checkpoint` silently
   release nothing (folder.py:92).

4. **Proved: a finished checkpoint's entries are let go when its manifest is readable but its times
   are not settable** (one another user owns on a shared filesystem). At 60 s old `read` tries
   `os.utime`, fails, and returns None (folder.py:76-79); `named()` omits it (store.py:167-170) and
   `drop` deletes what it named. `s2b_no_write_attr.py` (ACL denying write-attributes):
   `untouchable manifest: readable fresh=True; at 61s manifest()=None, named entry on disk after
   drop=False, gone()={}`. The NTFS read-only attribute alone does not trigger it. Such an entry is
   a permanent miss.

5. **Proved: re-making a checkpoint under its name loses the first when the second is refused.**
   The pending manifest lands over the finished one (store.py:140); a `Refused` in filling, as
   `reserve` inside `fill` raises, deletes the name (store.py:149-150). `s2_s3_s4_sequences.py`:
   `same name, second refused in its filling: first checkpoint manifest()=None`. A crash mid-fill
   loses it too, after `GRACE`.

6. **Proved: one foreign or torn file makes every room-making `put` raise, for good.**
   `entries/k/.DS_Store` reaches `int()` in `address_of` (store.py:31 via 211): `ValueError`.
   `checkpoints/.DS_Store`, or a manifest torn as folder_check's `tear` tears entries, older than
   `GRACE`: `read(name)[0]` on None (store.py:208), `TypeError`. macOS clients leave `.DS_Store` on
   SMB shares. `s2_s3_s4_sequences.py`: `entries/k/.DS_Store (4096 bytes): put -> ValueError ...`,
   `checkpoints/.DS_Store ...: put -> TypeError ...`, `checkpoints/m (13 bytes): put -> TypeError`.
   Suspected, not run: another process's release between `age()` and `read()` (store.py:207-208).

7. **Proved: a crashed checkpoint's pending manifest never ages, pinning its entries for ever.**
   `named()` reads, so touches, every manifest older than 60 s (folder.py:76-77); any `named()`
   within each `GRACE` keeps store.py:207-208 from passing, and its bytes count in `kept`
   (store.py:134). `s2_s3_s4_sequences.py`, filler `os._exit`ed: `named() every 100s=False: ...
   manifest left=False` against `named() every 100s=True: after 3000s manifest left=True, its entry
   kept=True`.

8. **Proved: two processes hold the lock when one clock runs 31 s ahead.** The stale test sets this
   machine's clock against the lock folder's mtime (folder.py:148). `s5_lock.py`: `skew: most inside
   the lock at once = 2`. A live owner holding past `STALE_LOCK` is the same case; it then removes
   the taker's lock on leaving (folder.py:162), suspected to admit a third.

9. **Proved: a lock left for ever, its waiter spinning unthrottled.** A stale lock folder `rmdir`
   cannot remove (non-empty, held open) hits `except OSError: continue`, skipping `wait`
   (folder.py:149-152). `s5_lock.py`: `unremovable lock: lock() had not returned after 10 s`.
   Suspected, not run: a process killed holding the lock stalls others' `drop`, `checkpoint` and
   room-making `put` for `STALE_LOCK`, against "nothing else waits on the lock". Not made to fail:
   20 rounds of 8 processes on a stale lock never put two inside (gap at folder.py:148-149).

10. **Proved: a refused write raises out of `put`.** `write` catches nothing (folder.py:46-50) and
    `rename`'s `makedirs` is outside its `try` (folder.py:57). `s8_cost.py`, `parts/` denied write:
    `refused write: PermissionError out of put`. Suspected, not run: a full disk or quota takes this
    path. Long paths did not fail here (LongPathsEnabled=1); without it folder.py:45, 57 would raise.

11. **Proved: the disk budget passes by about a budget per extra writer.** store.py:203 is outside
    the lock and `used()` counts only this writer between walks (folder.py:112-119). `s6_used.py`, two
    processes of 19 × 1 MB under 20 MB: `budget 20000000: two writers left 38000988 bytes (1.90 of the
    budget)`. A stale high count only sends a put to `_make_room`, which recounts: cost, no wrong
    refusal found. Suspected: two checkpoints past store.py:134 at once name more than the budget.

12. **Cost** (`s8_cost.py`, ms per call, 3000 entries of 1 KB, 40 manifests of 50): `size 0.13; get
    from disk 1 KB 0.33; get miss 0.06; put 1 KB 6.16; put 2 MB 7.31; names(entries) 130.56; named()
    9.86; drop (lock, named, walk) 16.16; used() walk 491.07`; `put 1 KB into a full disk (lock,
    sweep, named, walk, let go): 189.5`. Felt: a put is ~6 ms whatever its size (the fsync,
    folder.py:50), 18 s a minute at 3000 puts; the 0.5 s walk recurs each `RECOUNT` and after every
    lock; at budget every put pays 190 ms, under a lock held across the walk (store.py:205-219),
    which on a cluster filesystem makes item 8 likely. `checkpoint` reads every manifest first
    (store.py:134). Suspected, not timed: `made-*.log` is never let go, counts in `used()`, and is
    read whole at each open (folder.py:31-35).
