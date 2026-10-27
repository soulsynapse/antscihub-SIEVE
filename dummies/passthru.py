"""Dummy: pass-through. Hands out what it reads, whatever type that is."""
SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "passthru", "frame", ("bgr", "gray"), "same"
DEFAULTS = {"delay": 0}


def run(frames, row, params):
    return frames(max(0, row - params["delay"]))


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.add_int("delay", 0, 30, DEFAULTS["delay"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
