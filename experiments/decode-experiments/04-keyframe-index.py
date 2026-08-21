"""Building the keyframe index by demuxing only: read packets, decode nothing.

ideas.md claims this retires 'the GOP is variable so we cannot know' in
seconds on a 60 Mbps file. This demuxes both files end to end, flags
keyframes, and records the packet rate plus what the index actually shows:
how many keyframes, and how regular the spacing is — which is also the datum
the seek experiment's 'decode forward from keyframe' cost hangs on.
"""

from __future__ import annotations

import time
from pathlib import Path

import av

from harness import FOOTAGE, Run, report, time_case


def demux_case(run: Run, path: Path, tag: str) -> None:
    keyframes: list[int] = []
    count = [0]

    def work():
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            yield "open"
            for index, packet in enumerate(container.demux(stream)):
                if packet.size == 0:  # flush packet
                    continue
                if packet.is_keyframe:
                    keyframes.append(index)
                count[0] = index + 1
                yield True

    before = time.perf_counter()
    case = time_case(
        run, f"{tag}/demux-all", work,
        params={"file": path.name}, unit="ms per packet",
    )
    wall = time.perf_counter() - before
    gaps = [b - a for a, b in zip(keyframes, keyframes[1:])]
    case.params.update(
        packets=count[0], keyframes=len(keyframes),
        gop_min=min(gaps, default=0), gop_max=max(gaps, default=0),
        gop_median=sorted(gaps)[len(gaps) // 2] if gaps else 0,
        wall_s=round(wall, 3),
    )
    case.note = (
        f"{count[0]} packets, {len(keyframes)} keyframes, GOP "
        f"{min(gaps, default=0)}-{max(gaps, default=0)} "
        f"(median {case.params['gop_median']}), whole file in {wall:.2f}s"
    )


def main() -> None:
    run = Run(
        experiment="04-keyframe-index",
        question=(
            "What does a demux-only keyframe index cost end to end, and how "
            "variable is the GOP it reveals?"
        ),
    )
    big = FOOTAGE / "GX010047c2_02_17_26.MP4"
    small = FOOTAGE / "rep3_intermittent_crop.MP4"
    run.add_footage(big, small)
    demux_case(run, big, "big")
    demux_case(run, small, "small")
    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
