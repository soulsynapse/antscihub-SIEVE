"""Selector: which video the document means, by rule rather than by name. The first file under
`folder` (relative to the document, as Houdini's $HIP is to the hip file) whose name matches
`pattern`, by name or newest first, looking into subfolders if `recurse`; or, if `choice` names
one of the matches (relative to `folder`), that one. Its card lists the matches with the picked
one marked; clicking one makes it the choice, clicking it again clears it. Wire it into the video
node, or into a tool's path input; that node's pane then shows what it picked."""
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


def settings(parent=None):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidget, QListWidgetItem

    from sieve_player import ParamWidget
    from sieve_player.theme import ROW_H, readout

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_text("folder", DEFAULTS["folder"])
            self.add_text("pattern", DEFAULTS["pattern"])
            self.add_bool("recurse", DEFAULTS["recurse"])
            self.add_choice("order", ORDERS, DEFAULTS["order"])
            self.choice = DEFAULTS["choice"]
            self._get["choice"], self._set["choice"] = lambda: self.choice, self._set_choice
            self.list = QListWidget()
            self.list.setFixedHeight(ROW_H * 4)
            self.list.setSelectionMode(QListWidget.NoSelection)
            self.list.setFocusPolicy(Qt.NoFocus)
            self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.list.itemClicked.connect(self._clicked)
            self.status = readout()
            self.form.add_line(self.list)
            self.form.add_line(self.status)

        def _set_choice(self, v):
            if v != self.choice:
                self.choice = v
                self.changed.emit()

        def _clicked(self, item):
            name = item.data(Qt.UserRole)
            self._set_choice("" if name == self.choice else name)   # clicking the choice again clears it

        def show_matches(self, folder, found, picked):
            """The window's report: every file the rule matched and the one it picked."""
            self.list.clear()
            shown = names(folder, self.params(), found)
            for p, name in zip(found, shown):
                it = QListWidgetItem(("● " if p == picked else "   ") + name)
                it.setData(Qt.UserRole, name)
                it.setToolTip(p)
                self.list.addItem(it)
            if self.choice and self.choice not in shown:
                self.status.setText(f"{self.choice} is not among the matches; picked by {self.params()['order']}")
            elif self.choice:
                self.status.setText(f"chosen; click again to pick by {self.params()['order']}")
            else:
                self.status.setText("")

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([sys.modules[__name__], gray]))
