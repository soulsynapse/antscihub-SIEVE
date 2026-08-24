"""Does pointing at a folder find the footage, and only the footage?

The project machinery: a folder somebody pointed at, the document SIEVE writes
beside it, and the per-user list of which projects exist. Not a phase of
`docs/substrate/port-plan.md` — it sits above the substrate rather than in it —
but it is checked the same way and for the same reason.

Two properties.

**Adding a folder is cheap and reversible.** Headers and `stat` calls, nothing
decoded, nothing moved, nothing copied. If adding a project cost a demux per
file it would be an import, and somebody would think twice before pointing at a
folder to see what was in it.

**A project does not find its own output.** This is the one with teeth, and it
is the defect this file was written after hitting. *Everything SIEVE produces is
a video file* — a chunk, a proxy segment and a cut are all `.mp4` — so a
detector that skips a directory by name finds them all again the moment the
derived location is somewhere else. Pointed at a folder that had been worked in
under an older layout, the first version reported **seventy-six sources, of
which seventy-four were its own output**. Detection is now handed what to
ignore, and the project computes that from its own document.

Seven cases. The footage is generated: a handful of tiny clips encoded on the
spot, which is the only way to check detection without depending on what
happens to be in `video-tests/`.

**adopt** — a folder nobody has pointed at gets a document, an identity and a
name, and reopening it is the same project rather than a second one.

**detect** — video is found, non-video is not, and a file that will not open is
counted rather than raising or vanishing.

**derived** — the derived location is ignored by detection wherever the document
puts it, including somewhere the name `.sieve` would never have caught. This is
the case `--broken` fails.

**exclude** — a folder of exports can be excluded, the exclusion persists in the
document, and re-adding the project honours it.

**identity** — a project moved to a new path stays one row in the library, under
the id in its own document.

**library** — most-recently-opened first, adding twice is not duplicating,
forgetting removes the row and not the folder, and a folder that is not mounted
stays listed and says it is unavailable.

**carry** — a second scan reuses what the fingerprints still match and re-reads
only what changed, so the tenth open of a big folder is not the first one again.
That includes the files that *would not* open: an earlier version fingerprinted
only the successes, so every scan retried every failure, and the folder this
tree works in holds fifty-one of them.

`--broken` makes detection ignore nothing, which is where the seventy-four came
from.

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

from sieve.project import sources as sources_mod  # noqa: E402
from sieve.project.document import Document  # noqa: E402
from sieve.project.library import Library  # noqa: E402
from sieve.project.project import Project  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"


_real_detect = sources_mod.detect


def ignore_nothing(folder: Path, known=None, ignore=None, skipped=None):
    """Detection as it was before it was handed what to skip.

    Kept here as the thing being argued against. It is the obvious version —
    walk the folder, keep the video — and what it actually does is report a
    project's own chunks and proxy segments back to it as footage.
    """
    return _real_detect(folder, known, None, skipped)


def clip(path: Path, frames: int = 6, width: int = 64, height: int = 48) -> Path:
    """A tiny real video file, so detection has something honest to open."""
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


def furnish(folder: Path) -> None:
    """A folder shaped like one somebody would point at."""
    folder.mkdir(parents=True, exist_ok=True)
    clip(folder / "take-01.mp4")
    clip(folder / "take-02.mp4")
    clip(folder / "camera-b" / "take-03.mp4")
    (folder / "notes.txt").write_text("not footage", encoding="utf-8")
    (folder / "sheet.csv").write_text("also not footage", encoding="utf-8")
    # a file that looks like video and is not: what a half-finished copy is
    (folder / "truncated.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40)


def case_adopt(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "adopt"
    furnish(folder)

    project = Project.open(folder)
    if not Document.path_in(folder).exists():
        bad.append("opening a folder wrote no document")
    if project.name != "adopt":
        bad.append(f"the project named itself {project.name!r}")
    if not project.document.project_id:
        bad.append("the project has no identity")

    again = Project.open(folder)
    if again.document.project_id != project.document.project_id:
        bad.append("reopening a folder minted a second identity")
    if again.document.created != project.document.created:
        bad.append("reopening a folder reset when it was created")
    if again.document.opened <= project.document.opened:
        bad.append("reopening a folder did not move the opened time")
    where = Document.path_in(folder).relative_to(folder).as_posix()
    run.note(f"adopt: {project.name!r} id {project.document.project_id[:8]}, "
             f"document at {where}")
    return "adopt (a document, and one identity)", 2, bad


def case_detect(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "detect"
    furnish(folder)
    project = Project.open(folder)

    found = {source.path for source in project.sources}
    if found != {"take-01.mp4", "take-02.mp4", "camera-b/take-03.mp4"}:
        bad.append(f"detected {sorted(found)}")
    if project.unreadable != 1:
        bad.append(f"{project.unreadable} files failed to open, expected the "
                   "one truncated file")
    for source in project.sources:
        if not (source.width and source.height and source.codec):
            bad.append(f"{source.path} recorded without its headers")
        if source.duration_s <= 0:
            bad.append(f"{source.path} recorded no duration")
    if not project.summary().startswith("3 sources"):
        bad.append(f"the summary reads {project.summary()!r}")
    run.note(f"detect: {project.summary()!r} from a folder also holding two "
             "text files and a truncated one")
    return "detect (video, and nothing else)", 3, bad


def case_derived(run: Run, root: Path) -> tuple[str, int, list[str]]:
    """A project must not find its own output. The seventy-four."""
    bad: list[str] = []
    folder = root / "derived"
    furnish(folder)
    project = Project.open(folder)
    before = len(project.sources)

    # what a session leaves behind, in the default location
    for index in range(4):
        clip(project.derived / "chunks" / f"chunk-{index:04d}.mp4")
    project.rescan()
    if len(project.sources) != before:
        extra = [s.path for s in project.sources][before:]
        bad.append(f"the project found {len(project.sources) - before} of its "
                   f"own chunks as footage: {extra[:3]}")

    # and in a location the name `.sieve` would never have caught
    elsewhere = folder / "renders"
    project.document.derived = "renders"
    project.save()
    for index in range(3):
        clip(elsewhere / f"seg-{index:04d}.mp4")
    project.rescan()
    if len(project.sources) != before:
        bad.append(f"with derived at {elsewhere.name!r} the project found "
                   f"{len(project.sources) - before} of its own files")

    # an absolute derived location, which is the read-only-media escape hatch
    outside = root / "cache-elsewhere"
    project.document.derived = str(outside)
    if project.derived != outside:
        bad.append(f"an absolute derived path resolved to {project.derived}")
    run.note(f"derived: {before} sources before and after its own output "
             "appeared, in the default location and in one named nothing "
             "special")
    return "derived (never its own output)", before, bad


def case_exclude(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "exclude"
    furnish(folder)
    exports = folder / "exports"
    for index in range(3):
        clip(exports / f"render-{index}.mp4")

    project = Project.open(folder)
    if len(project.sources) != 6:
        bad.append(f"{len(project.sources)} sources before excluding, "
                   "expected six")
    if not project.exclude(exports):
        bad.append("excluding a folder reported no change")
    if len(project.sources) != 3:
        bad.append(f"{len(project.sources)} sources after excluding exports")
    if project.exclude(exports):
        bad.append("excluding the same folder twice reported a change")

    reopened = Project.open(folder)
    if reopened.document.excluded != ["exports"]:
        bad.append(f"the exclusion did not survive: "
                   f"{reopened.document.excluded}")
    if len(reopened.sources) != 3:
        bad.append("a reopened project stopped honouring its exclusion")
    run.note(f"exclude: exports/ excluded, {len(reopened.sources)} sources, "
             "and the document remembers")
    return "exclude (asked once, remembered)", 6, bad


def case_identity(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "moving"
    furnish(folder)
    library = Library(root / "lib-identity.json")
    project = library.add(folder)

    moved = root / "moved-here"
    shutil.move(str(folder), str(moved))
    after = library.add(moved)

    if after.document.project_id != project.document.project_id:
        bad.append("a moved folder became a different project")
    if len(library) != 1:
        bad.append(f"a moved folder made {len(library)} library rows")
    if library.entries[0].folder != str(moved.resolve()):
        bad.append(f"the library still points at {library.entries[0].folder}")
    run.note("identity: a folder moved on disk is one row, under the id in "
             "its own document")
    return "identity (survives a move)", 1, bad


def case_library(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    library = Library(root / "lib-many.json")
    made = []
    for name in ("alpha", "beta", "gamma"):
        folder = root / name
        furnish(folder)
        made.append(library.add(folder))
        time.sleep(0.01)      # so the opened times order

    if [entry.name for entry in library.entries] != ["gamma", "beta", "alpha"]:
        bad.append(f"the library is ordered "
                   f"{[e.name for e in library.entries]}")
    library.add(root / "alpha")
    if len(library) != 3:
        bad.append(f"adding a known folder made {len(library)} rows")
    if library.entries[0].name != "alpha":
        bad.append("re-adding a project did not move it to the front")

    reread = Library(root / "lib-many.json")
    if len(reread) != 3:
        bad.append(f"the library came back with {len(reread)} rows")
    if not reread.entries[0].summary:
        bad.append("an entry came back without its summary")

    gone = made[1]
    shutil.rmtree(gone.folder)
    entry = reread.find(gone.document.project_id)
    if entry is None:
        bad.append("a project whose folder is gone was dropped from the list")
    elif entry.available:
        bad.append("a project whose folder is gone reports available")

    if not reread.forget(gone.document.project_id):
        bad.append("forgetting a known project reported nothing removed")
    if reread.find(gone.document.project_id) is not None:
        bad.append("a forgotten project is still listed")
    if made[0].folder.exists() is False:
        bad.append("forgetting removed a folder")
    run.note(f"library: {len(reread)} rows, newest first, an unmounted folder "
             "kept and marked, forgetting a row leaving the folder alone")
    return "library (a list, not a filesystem)", 3, bad


def case_carry(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    folder = root / "carry"
    furnish(folder)
    project = Project.open(folder)
    first = {s.path: s for s in project.sources}

    opened = []
    real_read = sources_mod.read

    def counting(path, base):
        opened.append(path.name)
        return real_read(path, base)

    sources_mod.read = counting
    try:
        project.rescan()
        if opened:
            bad.append(f"a rescan reopened {opened}, though nothing changed")
        opened.clear()
        if project.unreadable != 1:
            bad.append(f"the skipped file was forgotten: unreadable is "
                       f"{project.unreadable}")

        target = folder / "take-01.mp4"
        clip(target, frames=9)          # same name, different file
        project.rescan()
        if "take-01.mp4" not in opened:
            bad.append("a changed file was not re-read")
        if len(opened) != 1:
            bad.append(f"a single changed file caused {len(opened)} reads")
    finally:
        sources_mod.read = real_read

    changed = {s.path: s for s in project.sources}
    if changed["take-01.mp4"].bytes == first["take-01.mp4"].bytes:
        bad.append("the changed file's fingerprint did not move")
    run.note("carry: an unchanged folder costs a stat per file, and only what "
             "changed is opened again")
    return "carry (fingerprints, not re-reads)", 4, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        sources_mod.detect = ignore_nothing

    run = Run(
        experiment="project" + ("-broken" if broken else ""),
        question="Does pointing at a folder find the footage in it, and never "
                 "the files SIEVE put there itself?",
    )
    run.note("footage is generated: a handful of tiny clips encoded on the "
             "spot, so detection is checked against a folder this file made "
             "rather than whatever is in video-tests/")
    if broken:
        run.note("RUN WITH --broken: detection ignores nothing, which is where "
                 "the seventy-four came from. `derived` is expected to FAIL.")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = [
            case_adopt(run, root),
            case_detect(run, root),
            case_derived(run, root),
            case_exclude(run, root),
            case_identity(run, root),
            case_library(run, root),
            case_carry(run, root),
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
        print("the --broken run tripped nothing: detection is not being "
              "reached and `derived` is not demonstrating what it claims.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
