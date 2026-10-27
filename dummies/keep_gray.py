"""Dummy: gray to gray. Returns its input unchanged."""
SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "keep_gray", "frame", "gray", "gray"
DEFAULTS = {"enabled": True}


def run(frames, row, params):
    return frames(row)


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.add_bool("enabled", DEFAULTS["enabled"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
