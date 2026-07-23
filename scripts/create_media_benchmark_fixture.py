from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the deterministic numbered lossless media fixture."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "test_videos" / "benchmark-numbered-ffv1.mkv",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not args.force:
        print(output)
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            (
                "testsrc2=size=320x180:rate=60:duration=5,"
                "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':"
                "text='%{n}':x=20:y=20:fontsize=48:"
                "fontcolor=white:box=1:boxcolor=black@0.65"
            ),
            "-frames:v",
            "300",
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-pix_fmt",
            "bgr0",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise SystemExit(completed.stderr.strip())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
