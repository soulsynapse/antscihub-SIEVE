# Adversary 2: folder.py against the contract on a real disk

Against `docs/playground/sim/folder.py` and `store.py` at bb0c6da0, run on Windows 11, NTFS, local
temp folder, Python 3.13 from `.venv`. Scripts are in `C:\Users\khnakam1\Documents\Code\Scratch\sieve-adversary-2\`
(outside the repo; each makes and removes its own temp folder); output lines are quoted as printed.
Most damaging first.

1. **Proved: an exception out of `drop`, `checkpoint` and a `put` that makes room, under plain
   two-process use.** `lock()` catches only `FileExistsError` from `os.mkdir` (folder.py:143-146).
   On Windows a `mkdir` that meets the other process's `rmdir` of the lock still pending raises
   `PermissionError` [WinError 5]. No crash, no stale lock needed. `s5b_lock_contention.py`: two
   processes calling `drop` for 15 s: `(exceptions, drops) per process = [({'PermissionError': 654},
   12010), ({'PermissionError': 495}, 11965)]`. Every `_lock()` caller (store.py:123, 145, 205) is
   exposed; a raise in the look at store.py:145 kills a checkpoint mid-way and leaves it pending.

2. **Proved: an exception out of `put` whenever another process lands or deletes while this one
   walks.** `used()` checks `os.path.exists` and then calls `getsize` (folder.py:116-117), and every
   `_land` of the other process makes a part and renames it away in that gap. `s6_used.py`:
   `walks of used() against a process landing and deleting: {'FileNotFoundError': 369} out of 7138`.
   It is reached from `put` under `worth=True` (store.py:76) and from `_make_room` (store.py:203, 213,
   220), and after every lock, because `lock()` clears `_counted` (folder.py:154).

3. **Proved: a checkpoint that returned is left pending, then swept, and its entries let go.** If
   any process has the pending manifest open when the finishing rename runs, `os.replace` is
   refused. `rename` passes over the refusal and deletes the finished part (folder.py:58-63).
   `checkpoint` returns normally (store.py:153), `manifest()` is None, `gone()` never names it, and
   after `GRACE` the sweep deletes it as a crash's leaving (store.py:206-209). Its entries are then
   loose. The reader can be another store's own `named()`. `s1_manifest_held.py`: `held: checkpoint
   returned, manifest()=None, after 2000s and 10 puts 3/3 named entries gone` and `raced: 4/300
   checkpoints returned but left pending while another process ran named()`. The same refusal at
   `release_checkpoint` (folder.py:92) leaves a checkpoint unreleased with no error raised.

4. **Proved: a finished checkpoint's entries are let go if this user can read its manifest but not
   change its times.** That is the case of a manifest another user owns on a shared filesystem.
   Once the manifest is 60 s old, `read` tries `os.utime`, the call fails, and the `except OSError`
   returns None (folder.py:76-79). `named()` leaves it out (store.py:167-170), `drop` deletes what it
   names, and `gone()` says nothing. `s2b_no_write_attr.py` (an ACL denying write-attributes):
   `untouchable manifest: readable fresh=True; at 61s manifest()=None, named entry on disk after
   drop=False, gone()={}`. A plain read-only attribute does not trigger it on NTFS. The same path
   makes such an entry a permanent miss.

5. **Proved: making a checkpoint again under a used name loses the first one if the second is
   refused.** The pending manifest lands over the finished one (store.py:140), and a `Refused` in
   filling deletes the name (store.py:149-150). A `Refused` out of `reserve` inside `fill` is the
   ordinary way to get there. `s2_s3_s4_sequences.py`: `same name, second refused in its filling:
   first checkpoint manifest()=None`. A crash during the second filling loses it the same way,
   after `GRACE`.

6. **Proved: one foreign or torn file makes every `put` that needs room raise, for good.**
   `entries/k/.DS_Store`: `address_of` does `int()` on it (store.py:31, via 211), giving
   `ValueError`. `checkpoints/.DS_Store`, or a manifest torn the way folder_check's `tear` tears
   entries, older than `GRACE`: `self.disk.read(name)[0]` on None (store.py:208), giving
   `TypeError`. macOS clients drop `.DS_Store` and `._*` on SMB shares. `s2_s3_s4_sequences.py`:
   `entries/k/.DS_Store (4096 bytes): put -> ValueError ...`, `checkpoints/.DS_Store ...: put ->
   TypeError ...`, `checkpoints/m (13 bytes): put -> TypeError ...`. The same `TypeError` happens if
   a release by another process lands between `age()` and `read()` at store.py:207-208. That race
   is suspected, not run.

7. **Proved: a crashed checkpoint's pending manifest never gets old, so its entries are pinned
   forever.** `named()` reads every manifest, and `read` touches any manifest older than 60 s
   (folder.py:76-77). So if anyone calls `named()` (any `drop`, any `_make_room`) at least once per
   `GRACE`, the sweep's age test at store.py:207-208 never passes. Its bytes also count in `kept` at
   store.py:134 against new checkpoints. `s2_s3_s4_sequences.py`, with a process `os._exit`ed
   mid-fill: `named() every 100s=False: ... manifest left=False` against `named() every 100s=True:
   after 3000s manifest left=True, its entry kept=True`.

8. **Proved: two processes inside the lock at once when one machine's clock runs 31 s ahead.** The
   stale test compares this machine's clock with the lock folder's mtime, which the owner's
   machine or file server set (folder.py:148). `s5_lock.py`: `skew: most inside the lock at once =
   2`. A live owner holding the lock longer than `STALE_LOCK` is the same case. The owner then
   `rmdir`s the taker's lock on leaving (folder.py:162), which is suspected to let a third process in.

9. **Proved: a lock can be left for ever, and its waiter spins at full speed.** A stale lock folder
   that `rmdir` cannot remove (one with a file in it, or one held open) hits `except OSError:
   continue`, which skips the `wait` (folder.py:149-152). `s5_lock.py`: `unremovable lock: lock() had
   not returned after 10 s`. Suspected, not run: a process killed while holding the lock stalls
   every other process's `drop`, `checkpoint` and room-making `put` for up to `STALE_LOCK`. That
   contradicts "nothing else waits on the lock". Not made to fail: 20 rounds of 8 processes taking
   a stale lock together never put two inside. The getmtime-then-rmdir gap (folder.py:148-149)
   remains a suspicion. Those rounds did raise the `PermissionError` of item 1.

10. **Proved: a refused write raises out of `put`.** `write` catches nothing (folder.py:46-50) and
    `rename`'s `makedirs` sits outside its `try` (folder.py:57). `s8_cost.py`, with `parts/` denied
    write by ACL: `refused write: PermissionError out of put`. A full disk or an exceeded quota
    (ENOSPC/EDQUOT) is suspected to take the same path; it was not run. Paths too long did not fail
    here (LongPathsEnabled=1); on a machine without it, folder.py:45 and 57 are suspected to raise.

11. **Proved: the disk budget is passed by about one budget per extra writer.** The fast path at
    store.py:203 is outside the lock and reads a `used()` that counts only this writer's doings
    between walks (folder.py:112-119, `RECOUNT` 30 s). `s6_used.py`, two processes each putting 19
    × 1 MB under a 20 MB budget: `budget 20000000: two writers left 38000988 bytes (1.90 of the
    budget)`. N writers within one `RECOUNT` can reach N × budget. The other direction, a stale
    high count, only sends a put into `_make_room`, which walks afresh under the lock: no wrong
    refusal was found, only cost. Also outside the lock: the pre-check at store.py:134. Two
    checkpoints made together are suspected to name more than the budget between them, which would
    then refuse every room-making put. Not run.

12. **Cost** (`s8_cost.py`; 3000 entries of 1 KB, 40 manifests of 50 addresses, local NTFS, ms per
    call): `size 0.13; get from disk 1 KB 0.33; get miss 0.06; put 1 KB 6.16; put 2 MB 7.31;
    names(entries) 130.56; named() 9.86; drop (lock, named, walk) 16.16; used() walk 491.07` and
    `put 1 KB into a full disk (lock, sweep, named, walk, let go): 189.5`. These will be felt. A put
    costs about 6 ms whatever its size, because of the fsync (folder.py:50): at 3000 small puts a
    minute that is about 18 s of each minute. `used()` walks the whole folder (0.5 s here), once
    per `RECOUNT` and again on the first count after every lock, so a walk that drops and puts in
    turn pays a walk per drop. Once the disk is at budget, every put pays the 190 ms. On a cluster
    filesystem the walk is suspected to cost far more, and holding the lock across it (store.py:205-219)
    makes item 8's takeover likely. `checkpoint` calls `named()` first (store.py:134), so making
    the n-th checkpoint reads all n-1 manifests. `made-*.log` is never let go, counts in `used()`,
    and is read whole at every open (folder.py:31-35). Its cost growth is suspected, not timed.
