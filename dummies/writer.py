"""Dummy exporter: passes gray through and, on Export, writes a one-line text file beside the video."""
import os
import sys

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "writer", "frame", "gray", "gray"
DEFAULTS = {"copies": 1}


def run(frames, row, params):
    return frames(row)


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.add_int("copies", 1, 5, DEFAULTS["copies"])
    return w


def output_name(src, params):
    return os.path.splitext(str(src))[0] + "_writer.txt"


def export_command(src, dst, params, fps):
    line = f"{os.path.basename(str(src))} {fps:.2f} fps\n" * params["copies"]
    return [sys.executable, "-c", f"open({str(dst)!r}, 'w').write({line!r})"]


def describe_output(src, params, fps):
    return f"{params['copies']} line(s) of text"


if __name__ == "__main__":
    from sieve_player import play
    from dummies import to_gray

    sys.exit(play([to_gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
