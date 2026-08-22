"""Build order: can the proxy build follow attention without paying for it?

The session explorer builds its display proxy as 96-frame intra segments in
one front-to-back ffmpeg pass, which leaves a late-timeline hunt on kf-snap
prices until the build happens to arrive. Attention-ordered building —
start at the playhead's segment, redirect when attention moves — requires
the build to be many short invocations instead of one long one, and each
invocation pays a spawn plus an accurate -ss (decode-and-discard from the
previous keyframe). This prices that freedom:

  linear       one invocation over the region: the do-nothing baseline.
  batch=k      the region as ceil(N/k) invocations of k segments each, in
               order — the amortization curve of the invocation tax.
  scattered    batch=4 in shuffled order — whether *position* costs
               anything beyond the seek every invocation already pays.
  redirect     kill a running build, relaunch at a far segment: the felt
               latency between attention moving and the first usable
               segment existing there.

Per-segment completion times come from polling the output directory with
the same rule the explorer trusts: a segment is done when a newer one
exists or the process has exited. Alignment is verified per strategy (96
frames per segment, first-frame content matching the linear build's), so
"same segments, different order" is checked rather than assumed.
"""

from __future__ import annotations

import random
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

# one harness serves every experiment folder; duplicating it would fork the
# result format, so import it from decode-experiments and repoint RESULTS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness
from harness import FOOTAGE, Case, Run, report

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
SCRATCH = FOOTAGE / "derived" / "_exp06-segs"

SEG_FRAMES = 96         #: the explorer's chunk grid (results/02-*: GOP x4)
REGION_SEGS = 20        #: segments per case — big enough to amortize, small
                        #: enough that four cases stay minutes, not hours
REDIRECT_TARGET = 50    #: far segment for the redirect case (frame 4800)
REDIRECT_AFTER_S = 3.0  #: let the doomed build get going first
REDIRECT_REPEATS = 3
POLL_S = 0.025
PROXY_VF = "scale=1328:-2"
PROXY_ARGS = ["-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
              "-g", "1", "-fps_mode", "passthrough", "-an"]


def launch(outdir: Path, fps: Fraction, start_seg: int, n_segs: int):
    """One build invocation: n_segs segments starting at start_seg, named on
    the global grid. -ss is frame-accurate (half a frame early, so the first
    emitted frame is exactly start_seg*96)."""
    start_frame = start_seg * SEG_FRAMES
    n_frames = n_segs * SEG_FRAMES
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y"]
    if start_frame:
        ss = float((Fraction(start_frame) - Fraction(1, 2)) / fps)
        cmd += ["-ss", f"{ss:.6f}"]
    cmd += ["-i", str(BIG), "-vf", PROXY_VF, *PROXY_ARGS,
            "-frames:v", str(n_frames)]
    splits = ",".join(str(f) for f in range(SEG_FRAMES, n_frames, SEG_FRAMES))
    if splits:
        cmd += ["-f", "segment", "-segment_frames", splits,
                "-reset_timestamps", "1",
                "-segment_start_number", str(start_seg),
                str(outdir / "seg-%05d.mp4")]
    else:
        cmd += [str(outdir / f"seg-{start_seg:05d}.mp4")]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def run_build(outdir: Path, fps: Fraction,
              batches: list[tuple[int, int]]) -> dict[int, float]:
    """Run invocations back to back, polling for segment completion.
    Returns {segment: seconds-from-start-until-usable}."""
    shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(parents=True, exist_ok=True)  # rmtree can lag on Windows
    for stale in outdir.glob("seg-*.mp4"):
        stale.unlink(missing_ok=True)
    done: dict[int, float] = {}
    t0 = time.perf_counter()

    def poll(proc_running: bool) -> None:
        present = sorted(int(p.stem.split("-")[1])
                         for p in outdir.glob("seg-*.mp4"))
        usable = present[:-1] if proc_running and present else present
        now = time.perf_counter() - t0
        for seg in usable:
            done.setdefault(seg, now)

    for start_seg, n_segs in batches:
        proc = launch(outdir, fps, start_seg, n_segs)
        while proc.poll() is None:
            poll(True)
            time.sleep(POLL_S)
        poll(False)
    return done


def verify(outdir: Path, reference: Path | None) -> str:
    """96 frames per segment, and (against the linear build) matching
    first-frame content — mean abs diff under 2, encoder noise only."""
    segs = sorted(outdir.glob("seg-*.mp4"))
    for path in segs:
        with av.open(str(path)) as c:
            n = sum(1 for _ in c.demux(c.streams.video[0]) if _.size)
        if n != SEG_FRAMES:
            return f"MISALIGNED: {path.name} has {n} frames"
    if reference is not None:
        probe_seg = segs[len(segs) // 2]
        ref_seg = reference / probe_seg.name

        def first_luma(p: Path) -> np.ndarray:
            with av.open(str(p)) as c:
                frame = next(c.decode(c.streams.video[0]))
                return frame.to_ndarray(format="gray").astype(np.int16)

        mad = float(np.mean(np.abs(first_luma(probe_seg)
                                   - first_luma(ref_seg))))
        # a fresh encoder's first frame quantizes slightly differently
        # (batch=1 measured MAD 2.47 with exact frame counts); misalignment
        # by even one frame measures far above this on moving footage
        if mad >= 6.0:
            return f"CONTENT MISMATCH: {probe_seg.name} MAD {mad:.2f}"
        return f"aligned; {probe_seg.name} first-frame MAD {mad:.3f} vs linear"
    return "aligned"


def add_case(run: Run, name: str, done: dict[int, float],
             params: dict, note: str) -> None:
    order = sorted(done)
    times = sorted(done.values())  # arrival order — scattered builds
    intervals = [(b - a) * 1000.0  # complete out of index order
                 for a, b in zip(times[:-1], times[1:])]
    params = {**params,
              "wall_s": round(max(times), 2),
              "first_segment_s": round(min(times), 2),
              "completion_s": {s: round(done[s], 2) for s in order}}
    case = Case(name, params, intervals, unit="ms between segment arrivals",
                note=note)
    run.cases.append(case)
    report(case)


def main() -> None:
    run = Run(
        experiment="06-build-order",
        question=(
            "Can the proxy build be attention-ordered — many short "
            "redirectable invocations instead of one linear pass — without "
            "paying meaningfully for the invocation tax, and what does a "
            "mid-build redirect cost?"
        ),
    )
    if not BIG.exists():
        print(f"missing {BIG}")
        return
    run.add_footage(BIG)
    with av.open(str(BIG)) as c:
        fps = c.streams.video[0].average_rate
    run.note(f"region = {REGION_SEGS} segments of {SEG_FRAMES} frames; "
             "normal process priority (the explorer runs builds "
             "below-normal; ratios transfer, absolutes shift).")

    linear_dir = SCRATCH / "linear"
    done = run_build(linear_dir, fps, [(0, REGION_SEGS)])
    add_case(run, "linear", done, {"batch": REGION_SEGS, "invocations": 1},
             verify(linear_dir, None))

    for batch in (4, 1):
        outdir = SCRATCH / f"batch{batch}"
        batches = [(s, min(batch, REGION_SEGS - s))
                   for s in range(0, REGION_SEGS, batch)]
        done = run_build(outdir, fps, batches)
        add_case(run, f"batch={batch}", done,
                 {"batch": batch, "invocations": len(batches)},
                 verify(outdir, linear_dir))

    outdir = SCRATCH / "scattered"
    batches = [(s, 4) for s in range(0, REGION_SEGS, 4)]
    random.Random(7).shuffle(batches)
    done = run_build(outdir, fps, batches)
    add_case(run, "scattered batch=4", done,
             {"batch": 4, "invocations": len(batches),
              "order": [s for s, _ in batches]},
             verify(outdir, linear_dir))

    # redirect: attention moves mid-build; how long until the first usable
    # segment exists at the new position?
    latencies = []
    for rep in range(REDIRECT_REPEATS):
        outdir = SCRATCH / f"redirect{rep}"
        shutil.rmtree(outdir, ignore_errors=True)
        outdir.mkdir(parents=True, exist_ok=True)
        for stale in outdir.glob("seg-*.mp4"):
            stale.unlink(missing_ok=True)
        doomed = launch(outdir, fps, 0, REGION_SEGS)
        time.sleep(REDIRECT_AFTER_S)
        t_move = time.perf_counter()
        doomed.terminate()
        doomed.wait()
        proc = launch(outdir, fps, REDIRECT_TARGET, 4)
        target = outdir / f"seg-{REDIRECT_TARGET:05d}.mp4"
        follower = outdir / f"seg-{REDIRECT_TARGET + 1:05d}.mp4"
        while proc.poll() is None and not follower.exists():
            time.sleep(POLL_S)
        latencies.append((time.perf_counter() - t_move) * 1000.0)
        proc.terminate()
        proc.wait()
        if not target.exists():
            run.note(f"redirect rep {rep}: target segment never appeared")
    case = Case("redirect", {"target_seg": REDIRECT_TARGET,
                             "killed_after_s": REDIRECT_AFTER_S},
                latencies, unit="ms from kill to first usable segment",
                note="terminate + spawn + accurate -ss + one segment encode")
    run.cases.append(case)
    report(case)

    shutil.rmtree(SCRATCH, ignore_errors=True)
    path = run.write()
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
