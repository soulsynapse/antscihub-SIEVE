"""Does opening a recording cost one container open, and stay the same project?

The project machinery: one recording, the document SIEVE writes beside it, and
the per-user list of which have been opened. Not a phase of
`docs/archive/2026.08-substrate-port.md` — it sits above the substrate rather than in it —
but it is checked the same way and for the same reason.

**A project is a recording.** An earlier version made it a folder, and this file
is most of what that cost: a card summarising a set nobody was going to work on
as a unit, a folder walk that found SIEVE's own chunks and proxy segments and
reported seventy-four of them as footage, and an exclusion mechanism to undo
that. All of it followed from the model rather than from anything hard. The unit
of work is a recording — the crop, the window and the tuning are about *that*
video — so the file is the project and the folder is just where it sits.

Two properties.

**Opening is cheap and reversible.** One container open for the headers,
nothing decoded, nothing moved, nothing copied. If adding a recording cost a
demux it would be an import, and somebody would think twice before pointing at a
file to see what was in it.

**A recording that has changed is read again; one that has not is not.** The
fingerprint is what makes reopening a library of fifty cost fifty `stat` calls
rather than fifty container opens — and what stops a re-exported recording being
served at the shape it used to be. This is the case `--broken` fails.

Seven cases. The footage is generated: tiny clips encoded on the spot, so the
check does not depend on what happens to be in `video-tests/`.

**adopt** — a recording nobody has opened gets a document, an identity and a
name, and reopening it is the same project rather than a second one.

**headers** — codec, shape and duration are recorded; a file that will not open
as video is refused rather than becoming an empty project.

**derived** — the default sits beside the recording under its own stem, two
recordings in one folder do not collide, and an absolute location is honoured.

**identity** — a recording moved to a new path stays one row in the library.

**library** — most-recently-opened first, adding twice does not duplicate,
forgetting removes the row and not the file, and a recording that is not mounted
stays listed and says it is unavailable.

**carry** — an unchanged recording is not re-read; a changed one is.

**bulk** — several recordings in one gesture, with the ones that could not be
read handed back rather than raising.

`--broken` trusts whatever the document last recorded, without checking the file
against it.

Run:
    uv run --group experiments python experiments/substrate-checks/09-project.py
    uv run --group experiments python experiments/substrate-checks/09-project.py --broken
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.project import footage as headers  # noqa: E402
from sieve.project.document import Document  # noqa: E402
from sieve.project.library import Library  # noqa: E402
from sieve.project.project import Project  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"


def trusting_open(cls, video: Path):
    """`open` without checking the file against what was written down.

    Kept here as the thing being argued against, and it is the tempting
    version: the document already says what the recording is, so why open it
    again. Because the file may not be the file any more — a recording
    re-exported at a different size keeps its name and its place, and a project
    that trusted its own note serves every later session the shape the video
    used to be.
    """
    video = Path(video).resolve()
    document = Document.load(video)
    if document is not None and document.footage is not None:
        project = Project(video=video, document=document.touched())
        project.save()
        return project
    # the captured original is the undecorated function, so it still wants
    # the class it was a classmethod of
    return _real_open(Project, video)


def clip(path: Path, frames: int = 6, width: int = 64, height: int = 48) -> Path:
    """A tiny real recording, so the headers have something honest to say."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w") as out:
        stream = out.add_stream("libx264", rate=24)
        stream.width, stream.height = width, height
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "30", "preset": "ultrafast", "g": "1"}
        for index in range(frames):
            array = np.full((height, width, 3), index * 20 % 255, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(array, format="bgr24")
            for packet in stream.encode(frame.reformat(format="yuv420p")):
                out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    return path


def not_video(path: Path) -> Path:
    """What a half-copied download looks like: the name, and none of the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40)
    return path


def case_adopt(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = clip(root / "adopt" / "take-01.mp4")
    project = Project.open(video)
    if project is None:
        bad.append("a real recording would not open")
        return "adopt (a document, and one identity)", 0, bad

    if not Document.path_for(video).exists():
        bad.append("opening a recording wrote no document")
    if project.name != "take-01":
        bad.append(f"the project named itself {project.name!r}")
    if not project.document.project_id:
        bad.append("the project has no identity")

    again = Project.open(video)
    if again.document.project_id != project.document.project_id:
        bad.append("reopening a recording minted a second identity")
    if again.document.created != project.document.created:
        bad.append("reopening a recording reset when it was created")
    if again.document.opened <= project.document.opened:
        bad.append("reopening a recording did not move the opened time")
    where = Document.path_for(video).relative_to(video.parent).as_posix()
    run.note(f"adopt: {project.name!r} id {project.document.project_id[:8]}, "
             f"document at {where}")
    return "adopt (a document, and one identity)", 2, bad


def case_headers(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = clip(root / "headers" / "take.mp4", frames=48, width=128,
                 height=96)
    project = Project.open(video)
    held = project.footage if project else None
    if held is None:
        bad.append("a real recording recorded no headers")
    else:
        if (held.width, held.height) != (128, 96):
            bad.append(f"recorded {held.width}x{held.height}, not 128x96")
        if held.codec != "h264":
            bad.append(f"recorded codec {held.codec!r}")
        if not 1.5 < held.duration_s < 2.5:
            bad.append(f"48 frames at 24 fps recorded as "
                       f"{held.duration_s:.2f}s")
        if not project.summary().startswith("128×96"):
            bad.append(f"the summary reads {project.summary()!r}")

    broken_file = not_video(root / "headers" / "half-copied.mp4")
    if Project.open(broken_file) is not None:
        bad.append("a file that is not video became a project")
    if Document.path_for(broken_file).exists():
        bad.append("a refused file still had a document written for it")
    run.note(f"headers: {project.summary()!r}; a half-copied file was refused "
             "rather than becoming an empty project")
    return "headers (read, or refused)", 4, bad


def case_derived(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "derived"
    first = Project.open(clip(folder / "take-01.mp4"))
    second = Project.open(clip(folder / "take-02.mp4"))

    if first.derived == second.derived:
        bad.append(f"two recordings in one folder share {first.derived}")
    if first.derived.name != "take-01":
        bad.append(f"the default derived location is {first.derived.name!r}, "
                   "not the recording's stem")
    if first.derived.parent.name != ".sieve":
        bad.append(f"derived work sits in {first.derived.parent.name!r}")
    if Document.path_for(first.video) == Document.path_for(second.video):
        bad.append("two recordings in one folder share a document")

    elsewhere = root / "cache-elsewhere"
    first.document.derived = str(elsewhere)
    if first.derived != elsewhere:
        bad.append(f"an absolute derived path resolved to {first.derived}")
    run.note(f"derived: {first.derived.parent.name}/{first.derived.name} and "
             f"{second.derived.parent.name}/{second.derived.name} — named for "
             "the recording, so a folder of footage cannot collide")
    return "derived (one per recording)", 4, bad


def case_identity(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "moving"
    video = clip(folder / "take.mp4")
    library = Library(root / "lib-identity.json")
    project = library.add(video)

    moved = folder / "renamed.mp4"
    shutil.move(str(video), str(moved))
    shutil.move(str(Document.path_for(video)), str(Document.path_for(moved)))
    after = library.add(moved)

    if after is None:
        bad.append("the moved recording would not open")
    elif after.document.project_id != project.document.project_id:
        bad.append("a moved recording became a different project")
    if len(library) != 1:
        bad.append(f"a moved recording made {len(library)} library rows")
    if library.entries[0].video != str(moved.resolve()):
        bad.append(f"the library still points at {library.entries[0].video}")
    run.note("identity: a recording renamed on disk is one row, under the id "
             "in its own document")
    return "identity (survives a rename)", 1, bad


def case_library(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    library = Library(root / "lib-many.json")
    made = []
    for name in ("alpha", "beta", "gamma"):
        made.append(library.add(clip(root / "many" / f"{name}.mp4")))
        time.sleep(0.01)      # so the opened times order

    if [entry.name for entry in library.entries] != ["gamma", "beta", "alpha"]:
        bad.append(f"the library is ordered "
                   f"{[e.name for e in library.entries]}")
    library.add(root / "many" / "alpha.mp4")
    if len(library) != 3:
        bad.append(f"adding a known recording made {len(library)} rows")
    if library.entries[0].name != "alpha":
        bad.append("re-adding a project did not move it to the front")

    reread = Library(root / "lib-many.json")
    if len(reread) != 3:
        bad.append(f"the library came back with {len(reread)} rows")
    if not reread.entries[0].summary:
        bad.append("an entry came back without its summary")

    gone = made[1]
    gone.video.unlink()
    entry = reread.find(gone.document.project_id)
    if entry is None:
        bad.append("a project whose recording is gone was dropped")
    elif entry.available:
        bad.append("a project whose recording is gone reports available")

    if not reread.forget(gone.document.project_id):
        bad.append("forgetting a known project reported nothing removed")
    if reread.find(gone.document.project_id) is not None:
        bad.append("a forgotten project is still listed")
    if not made[0].video.exists():
        bad.append("forgetting removed a recording")
    run.note(f"library: {len(reread)} rows, newest first, a missing recording "
             "kept and marked, forgetting a row leaving the file alone")
    return "library (a list, not a filesystem)", 3, bad


def case_carry(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = clip(root / "carry" / "take.mp4", width=64, height=48)
    Project.open(video)

    opened: list[str] = []
    real_read = headers.read

    def counting(path):
        opened.append(path.name)
        return real_read(path)

    headers.read = counting
    try:
        Project.open(video)
        if opened:
            bad.append(f"reopening an unchanged recording re-read {opened}")
        opened.clear()

        # the same name, a different file: what a re-export looks like
        clip(video, frames=12, width=96, height=72)
        project = Project.open(video)
        if not opened:
            bad.append("a changed recording was not re-read")
        held = project.footage if project else None
        if held is not None and (held.width, held.height) != (96, 72):
            bad.append(f"after a re-export the project still says "
                       f"{held.width}x{held.height}")
    finally:
        headers.read = real_read
    run.note("carry: an unchanged recording costs a stat, and a re-exported "
             "one is read again rather than served at the shape it used to be")
    return "carry (fingerprint, not a re-read)", 2, bad


def case_bulk(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "bulk"
    wanted = [clip(folder / f"take-{index:02d}.mp4") for index in range(5)]
    wanted.append(not_video(folder / "half-copied.mp4"))
    wanted.append(folder / "never-existed.mp4")

    library = Library(root / "lib-bulk.json")
    opened, refused = library.add_all(wanted)
    if len(opened) != 5:
        bad.append(f"{len(opened)} of 5 real recordings opened")
    if len(refused) != 2:
        bad.append(f"{len(refused)} refusals, expected the half-copied file "
                   "and the missing one")
    if len(library) != 5:
        bad.append(f"the library holds {len(library)} rows")
    run.note(f"bulk: {len(opened)} opened and {len(refused)} handed back in "
             "one gesture — one unreadable file is not a reason for the rest "
             "to fail")
    return "bulk (several at once)", len(wanted), bad


_real_open = Project.open.__func__


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        Project.open = classmethod(trusting_open)

    run = Run(
        experiment="project" + ("-broken" if broken else ""),
        question="Does opening a recording cost one container open, and stay "
                 "the same project when it moves?",
    )
    run.note("footage is generated: tiny clips encoded on the spot, so this "
             "does not depend on what is in video-tests/")
    if broken:
        run.note("RUN WITH --broken: a project trusts whatever its document "
                 "last recorded without checking the file against it. `carry` "
                 "is expected to FAIL.")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = [
            case_adopt(run, root),
            case_headers(run, root),
            case_derived(run, root),
            case_identity(run, root),
            case_library(run, root),
            case_carry(run, root),
            case_bulk(run, root),
        ]

    ok = True
    print(f"{'case':<40} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<40} {checked:>9}  "
              f"{'ok' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} checked, {len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))

    print()
    for line in run.notes:
        print(f"  · {line}")

    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken run tripped nothing: the substitution is not "
              "being reached and `carry` is not demonstrating what it claims.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
