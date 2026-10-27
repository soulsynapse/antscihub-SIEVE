"""Selector: which video the document means, by rule rather than by name. The first file under
`folder` (relative to the document, as Houdini's $HIP is to the hip file) whose name matches
`pattern`, by name or newest first, looking into subfolders if `recurse`. Wire it into the video
node; the video node's pane then shows what it picked."""
import glob
import os

SIEVE_TOOL = True
NAME, KIND, PRODUCES = "file", "selector", "path"
DEFAULTS = {"folder": ".", "pattern": "*.mp4", "recurse": False, "order": "name"}
ORDERS = ("name", "newest")


def matches(folder, params):
    base = os.path.join(folder, params["folder"])
    recurse = bool(params["recurse"])
    pattern = os.path.join(base, "**", params["pattern"]) if recurse else os.path.join(base, params["pattern"])
    found = [p for p in glob.glob(pattern, recursive=recurse) if os.path.isfile(p)]
    if params["order"] == "newest":
        found.sort(key=os.path.getmtime, reverse=True)
    else:
        found.sort(key=lambda p: os.path.basename(p).lower())
    return found


def select(folder, params):
    found = matches(folder, params)
    return found[0] if found else None


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.add_text("folder", DEFAULTS["folder"])
    w.add_text("pattern", DEFAULTS["pattern"])
    w.add_bool("recurse", DEFAULTS["recurse"])
    w.add_choice("order", ORDERS, DEFAULTS["order"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([sys.modules[__name__], gray]))
