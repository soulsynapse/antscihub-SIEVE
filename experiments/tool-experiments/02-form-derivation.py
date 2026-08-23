"""Does a held frame answer a wanted form more cheaply than a decode?

The fork the whole folder turned on. If deriving a step's form from something
a store already holds is in the noise beside decoding it fresh, then form
belongs in the key and a store keeps several shapes of one instant; if it is
not, a form change stays the wipe it is in the session explorer today, and
the tool tier gets a store of its own.

It is a tuning-loop question before it is a batch one. If a step's form is
not what the loop already holds, every displayed position pays a second
production inside the frame period, and that is what decides whether a live
overlay is affordable at all.

Three things are measured, and the third is the one easy to forget.

**Derive against decode**, per wanted form, on the files the loop actually
runs against. Derivation goes through `forms.derive`, so it is the canonical
construction with the crop rebased — the same bytes a build from source
produces, which is asserted here rather than assumed.

**What the dominating form costs to hold.** A full source frame answers every
crop of it for almost nothing and weighs a great deal; an analysis-form crop
weighs little and answers only itself and coarser versions of itself.
Derivation cost alone would say "cache the biggest thing you can", which is
the wrong conclusion, so bytes-per-held-frame is reported beside every case.

**How wrong the approximate route is**, on real content rather than in
principle. The `lo` placeholder — a crop pulled from an already-downscaled
proxy — is barred from being recorded but it *is* shown, and how visibly
wrong it is decides whether showing it beats holding the last frame. Reported
as error against the true crop, which is a property of the footage and
belongs in a result rather than in anybody's judgement.

Two decode baselines are timed rather than one, and reading the derive cases
against the wrong one would flatter them by an order of magnitude. Converting
through `to_ndarray` pays a scaler setup per call, which the decode shelf
already records as avoidable; taking the luma plane and slicing it is what
the session explorer does today, and only that is a fair opponent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE, Run, report, time_case  # noqa: E402

import forms  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
CUT = FOOTAGE / "derived" / "cut-crf18-intra.mp4"
PROXY = FOOTAGE / "derived" / "proxy-1328-intra.mp4"

CROP = (2144, 982, 1024, 1024)   #: the session explorer's own crop
HELD = 5                         #: full source frames to hold at once
REPS = 40


def _luma_crop(frame, rect):
    """Plane zero, sliced, no scaler — the loop's own route.

    The crop is sliced before the copy so the contiguous buffer is the size
    of the crop rather than of the whole plane.
    """
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    x, y, w, h = rect
    return np.ascontiguousarray(arr[y:y + h, x:x + w])


def _decode(path: Path, count: int, pix: str = "bgr24"):
    out = []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in container.decode(stream):
            out.append(frame.to_ndarray(format=pix))
            if len(out) >= count:
                break
    return out


def repeat(fn, n=REPS):
    def work():
        yield "start"
        for i in range(n):
            fn(i)
            yield True
    return work


def main() -> None:
    run = Run(
        experiment="02-form-derivation",
        question="Is deriving a wanted form from a held frame cheaper than "
                 "decoding it, and what does holding the dominating form "
                 "cost?",
    )
    run.add_footage(BIG, CUT, PROXY)
    run.note(f"crop={CROP} held={HELD}")
    run.note("two decode baselines are timed. `to_ndarray` pays a scaler "
             "setup per call, which the decode shelf records as avoidable; "
             "`luma-crop` takes plane zero and slices it, which is what the "
             "session explorer does. Only the second is a fair opponent for "
             "a derivation, and reading the derive cases against the first "
             "would flatter them by an order of magnitude.")

    probe = _decode(BIG, 1)[0]
    src_h, src_w = probe.shape[:2]
    source_bgr = forms.source_form(src_w, src_h, "bgr")
    source_gray = forms.Form((0, 0, src_w, src_h), (src_w, src_h), "gray")
    analysis = forms.Form(CROP, (CROP[2], CROP[3]), "gray")
    coarse = forms.Form(CROP, (CROP[2] // 2, CROP[3] // 2), "gray")

    print(f"source {src_w}x{src_h}; analysis form {analysis.key()}")
    print(f"held bytes: source-bgr {source_bgr.nbytes/1e6:.1f} MB, "
          f"source-gray {source_gray.nbytes/1e6:.1f} MB, "
          f"analysis {analysis.nbytes/1e6:.1f} MB")

    # ── decode and build, the no-cache baselines ─────────────────────────
    print("\ndecode + build the analysis form, per frame:")
    for path, label in ((BIG, "uncut source"), (CUT, "intra cut")):
        if not path.exists():
            run.note(f"{label}: {path.name} absent, cases not run")
            continue
        for route in ("to_ndarray bgr24", "plane 0, no scaler"):
            def go(_i, path=path, route=route):
                # not setdefault: its default argument is evaluated on
                # every call, so that opens a container per frame and
                # times the opening rather than the decoding
                key = (path, route)
                state = go_state.get(key)
                if state is None:
                    state = go_state[key] = _stream(path)
                frame = next(state)
                rect = (CROP if path is BIG else
                        (0, 0, min(CROP[2], frame.width),
                         min(CROP[3], frame.height)))
                if route.startswith("plane"):
                    return _luma_crop(frame, rect)
                arr = frame.to_ndarray(format="bgr24")
                want = forms.Form(rect, (rect[2], rect[3]), "gray")
                return forms.build(arr, want)
            name = ("decode+build (bgr24)" if route.startswith("to_ndarray")
                    else "decode+luma-crop")
            case = time_case(run, f"{name} {label}", repeat(go),
                             params={"file": path.name, "route": route,
                                     "wanted": analysis.key(),
                                     "held_bytes": 0},
                             unit="ms per frame")
            report(case)

    # ── derive from a held frame, no decode ──────────────────────────────
    print("\nderive from a held frame (no decode):")
    held_bgr = _decode(BIG, HELD, "bgr24")
    held_gray = [forms.build(f, source_gray) for f in held_bgr]
    held_analysis = [forms.build(f, analysis) for f in held_bgr]

    truth = forms.build(held_bgr[0], analysis)
    check, how = forms.derive(held_bgr[0], source_bgr, analysis)
    assert how == forms.EXACT and np.array_equal(truth, check)
    run.note("derive(source-bgr -> analysis) is byte-identical to a build "
             "from source on real frames, as forms.py claims")

    for label, held, have, want, holding in (
        ("source-bgr -> analysis", held_bgr, source_bgr, analysis, source_bgr),
        ("source-gray -> analysis", held_gray, source_gray, analysis, source_gray),
        ("analysis -> half-res", held_analysis, analysis, coarse, analysis),
    ):
        case = time_case(
            run, f"derive {label}",
            repeat(lambda i, held=held, have=have, want=want:
                   forms.derive(held[i % len(held)], have, want)),
            params={"have": have.key(), "want": want.key(),
                    "held_bytes": holding.nbytes},
            unit="ms per frame")
        report(case)

    # ── how wrong the approximate route is, on real content ──────────────
    print("\napproximate route (proxy -> crop), against the truth:")
    if not PROXY.exists():
        run.note("proxy absent; the approximate-route error case was not run")
    else:
        proxy_frames = _decode(PROXY, HELD, "bgr24")
        p_h, p_w = proxy_frames[0].shape[:2]
        proxy_form = forms.Form((0, 0, src_w, src_h), (p_w, p_h), "bgr")
        assert forms.grade(proxy_form, analysis) == forms.APPROX
        errors = []
        for held, prox in zip(held_bgr, proxy_frames):
            lo, _ = forms.derive(prox, proxy_form, analysis)
            hi = forms.build(held, analysis)
            errors.append(np.abs(lo.astype(np.int16) - hi.astype(np.int16)))
        stack = np.concatenate([e.ravel() for e in errors])
        run.note(
            f"approximate route at shortfall "
            f"{forms.shortfall(proxy_form, analysis):.3f}: mean abs error "
            f"{stack.mean():.1f}/255, p95 {np.percentile(stack, 95):.1f}, "
            f"max {stack.max()}/255 over {len(errors)} frames — what the "
            f"placeholder is wrong by on this footage, which is what decides "
            f"whether showing it beats holding the last frame")
        print(f"  mean {stack.mean():.1f}/255  "
              f"p95 {np.percentile(stack, 95):.1f}  max {stack.max()}/255")

        case = time_case(
            run, "derive proxy -> analysis (approx)",
            repeat(lambda i, held=proxy_frames, have=proxy_form:
                   forms.derive(held[i % len(held)], have, analysis)),
            params={"have": proxy_form.key(), "want": analysis.key(),
                    "held_bytes": proxy_form.nbytes, "grade": forms.APPROX},
            unit="ms per frame")
        report(case)

    path = run.write()
    print(f"\nwrote {path}")


go_state: dict = {}


def _stream(path: Path):
    container = av.open(str(path))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    return container.decode(stream)


if __name__ == "__main__":
    main()
