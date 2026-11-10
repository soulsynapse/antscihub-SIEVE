"""Selector: which video the document means, by rule rather than by name. The first file under
`folder` (relative to the document, as Houdini's $HIP is to the hip file) whose name matches
`pattern`, by name or newest first, looking into subfolders if `recurse`; or, if `choice` names
one of the matches (relative to `folder`), that one. Its card lists the matches with the picked
one marked; clicking one makes it the choice, clicking it again clears it, and Browse opens a file
dialog whose pick becomes the rule: its folder, a pattern it matches and it as the choice. Wire it
into the video node, or into a tool's path input; that node's pane then shows what it picked."""
import fnmatch
import glob
import os

SIEVE_TOOL = True
NAME, KIND, PRODUCES = "file", "selector", "path"
DEFAULTS = {"folder": ".", "pattern": "*.mp4", "recurse": False, "order": "name", "choice": ""}
ORDERS = ("name", "newest")


def names(folder, params, found):
    """Each match as the card shows it and `choice` stores it: relative to the rule's folder."""
    base = os.path.join(folder, params["folder"])
    return [os.path.relpath(p, base) for p in found]


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
    if not found:
        return None
    choice = os.path.normcase(params.get("choice") or "")
    for p, name in zip(found, names(folder, params, found)):
        if choice and os.path.normcase(name) == choice:
            return p
    return found[0]


def rule_for(path, base, params):
    """The params that pick `path`, a file, as a rule written against `base`, the document's folder:
    `folder` the file's folder relative to `base`, or absolute when no relative path reaches it,
    `pattern` kept when the file's name matches it and else `*` plus the file's suffix, `choice`
    the file's name, and `recurse` off, since the folder is the file's own."""
    path = os.path.abspath(path)
    folder, name = os.path.split(path)
    try:
        folder = os.path.relpath(folder, base) or "."
    except ValueError:              # another drive on Windows: no relative path reaches it
        pass
    pattern = params["pattern"] if fnmatch.fnmatch(name, params["pattern"]) else "*" + os.path.splitext(name)[1]
    return {**params, "folder": folder, "pattern": pattern, "recurse": False, "choice": name}


def settings(parent=None):
    from PySide6.QtWidgets import QFileDialog, QPushButton

    from sieve_player import ParamWidget

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_text("folder", DEFAULTS["folder"])
            self.add_text("pattern", DEFAULTS["pattern"])
            self.add_bool("recurse", DEFAULTS["recurse"])
            self.add_choice("order", ORDERS, DEFAULTS["order"])
            self.base = os.getcwd()         # the document's folder, as the window last reported it
            self.browse = QPushButton("Browse…")
            self.browse.clicked.connect(self._browse)
            self.form.add_row("file", self.browse)
            self.chooser = self.add_list("choice", DEFAULTS["choice"])

        def _browse(self):
            start = os.path.join(self.base, self.params()["folder"])
            path, _ = QFileDialog.getOpenFileName(self, "Choose the file the rule picks", start, "All files (*)")
            if path:
                self.choose(path)

        def choose(self, path):
            """Make `path` the rule's pick, as one change."""
            self.blockSignals(True)
            try:
                self.set_params(rule_for(path, self.base, self.params()))
            finally:
                self.blockSignals(False)
            self.changed.emit()

        def show_matches(self, folder, found, picked):
            """The window's report: every file the rule matched and the one it picked."""
            self.base = folder
            shown = names(folder, self.params(), found)
            choice, order = self.chooser.value, self.params()["order"]
            status = (f"{choice} is not among the matches; picked by {order}" if choice and choice not in shown
                      else f"chosen; click again to pick by {order}" if choice else "")
            self.chooser.show([(name, name, p) for p, name in zip(found, shown)],
                              next((name for p, name in zip(found, shown) if p == picked), None), status)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([sys.modules[__name__], gray]))
