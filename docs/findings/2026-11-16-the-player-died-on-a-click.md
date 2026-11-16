# The player died on a click

2026-11-16, on v5-systems-review, the code under `sieve_player/` and `tools/` as `75616e2d` left
it. No experiment: this is what one crash left behind, written down the hour it happened so that
the log's next two launches do not write over it. Nothing here was reproduced, and the cause is not
known.

## What happened

The player was started at 11:46:01 by `main.py` on
`video-tests/Thermal hysteresis 4 days/Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps.mp4`,
1920x1080, 345,595 rows claimed, the memo and the cache at 4 GB each. At 14:09:27 a click on the
canvas that selected a node ended the process. The window stood unanswering for some twenty
seconds, which was Windows writing the dump, and closed.

Python 3.13.5, the GIL on; OpenCV 5.0.0, numpy 2.5.4, av 19.0.2, PySide6 6.12.0.

## What it left

`%LOCALAPPDATA%\SIEVE\stderr.log`, which `sieve_player/dev/console.py` keeps for one launch more
as `stderr.prev.log`. Between the line that says the video opened and this, the log holds nothing:

    Windows fatal exception: access violation

    Thread 0x00009334 (most recent call first):
      File "sieve_player\density.py", line 49 in fold
      File "sieve_player\graph.py", line 744 in density
      File "sieve_player\walk.py", line 197 in fold
      File "sieve_player\walk.py", line 213 in refold
      File "sieve_player\worker.py", line 177 in _serve
      File "sieve_player\worker.py", line 152 in run

    Thread 0x0000f66c (most recent call first):
      File "Lib\threading.py", line 363 in wait
      File "Lib\threading.py", line 659 in wait
      File "sieve_player\machine.py", line 163 in run
      File "Lib\threading.py", line 1043 in _bootstrap_inner
      File "Lib\threading.py", line 1014 in _bootstrap

    Current thread 0x0001e72c (most recent call first):
      File "sieve_player\ledger.py", line 282 in _view
      File "sieve_player\ledger.py", line 313 in _settle
      File "sieve_player\ledger.py", line 379 in _fold
      File "sieve_player\ledger.py", line 251 in view
      File "sieve_player\window.py", line 1429 in _show_takes
      File "sieve_player\window.py", line 655 in _select
      File "sieve_player\window.py", line 439 in <lambda>
      File "sieve_player\canvas.py", line 130 in select
      File "sieve_player\canvas.py", line 789 in mousePressEvent
      File "sieve_player\canvas.py", line 923 in event
      File "sieve_player\__init__.py", line 52 in play
      File "main.py", line 16 in <module>
    Timeout (0:00:05)!

The watchdog's dump five seconds on has the three threads in the same lines.

Windows' Application log, event 1000 at 14:09:27: faulting module `python313.dll`, exception
`0xc0000005`, offset `0x325ff`, process id `0x24320`. Its dump is
`%LOCALAPPDATA%\CrashDumps\python.exe.148256.dmp`, 6.2 GB, finished at 14:09:50. It was not
opened: no debugger is on this machine's PATH.

## What can be said of it

The thread that faulted is the GUI thread, and where it stood, `ledger.py:Ledger._view` at the line
that lists the buckets, is Python and no extension's. Python under the GIL does not fault on its
own, so the interpreter met an object that code outside it had freed or written over, and the line
is where that was met and not where it was done. What did it the log does not say. The worker was
then inside `cv2.calcHist` on a uint8 plane, folding a density on a range already walked; that is
what else the process was doing and is no more than that.

## The others

Every crash of a `python.exe` the Application log holds from 2026-11-10 on. Windows names the
program and not what it was running, so which of these were the player, and which a test or a
session's script, is not known; today's first was at 11:44:31 and `stderr.prev.log` begins at
11:45:16.

| when | faulting module | exception | offset |
| --- | --- | --- | --- |
| 11-16 14:09:27 | `python313.dll` | `0xc0000005` | `0x325ff` |
| 11-16 11:44:31 | `_multiarray_umath.cp313-win_amd64.pyd` | `0xc000001d` | `0xc7e21` |
| 11-15 17:06:51 | `opencv_videoio_ffmpeg500_64.dll` | `0xc0000005` | `0x13790ef` |
| 11-15 11:47:56 | `opencv_videoio_ffmpeg500_64.dll` | `0xc0000005` | `0x13790ef` |
| 11-14 16:31:19 | unknown | `0xc0000005` | `0x1d586fa7d80` |
| 11-14 16:24:49 | `opencv_videoio_ffmpeg500_64.dll` | `0xc0000005` | `0x13790ef` |
| 11-14 15:58:53 | `python313.dll` | `0xc0000005` | `0x2b2d50` |
| 11-13 23:00:54 | unknown | `0xc0000005` | `0x19f42048630` |
| 11-13 17:39:59 | `python313.dll` | `0xc0000005` | `0x2b2d50` |
| 11-13 17:16:20 | `Qt6Core.dll` | `0xc0000409` | `0x1ce68` |
| 11-10 19:31:21 | `python313.dll` | `0xc0000005` | `0x2b2e15` |

Three are one fault, in the plugin's reader, at one offset. The rest land in the interpreter, in
numpy and at addresses in no module, which is how a freed or overwritten object is met: wherever
it is next touched. That reading is of the table alone.

From PowerShell:

    Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error';
        StartTime=(Get-Date).AddDays(-14)} | Where-Object { $_.Message -match 'python' }

## What is not known

- The cause, and whether the eleven are one cause, two or more.
- Which of the eleven were the player.
- What `0x325ff` in `python313.dll` is, and which object the GUI thread met there: the dump holds
  both, and Windows keeps a dump only until newer ones push it out.
- Whether it comes again on the same file and the same click. It was not tried.

## What it bears on

The friction ledger, `2026-11-16-what-came-back.md`, was being read class by class when this
happened. Of its F04, a failure not shown or shown as something else: the player said nothing, and
what it wrote was a stack of a thread that had done nothing wrong. Of its F02, one thread reading
or writing what another was changing: the monitor times what the threads do and has no way to see
this.
