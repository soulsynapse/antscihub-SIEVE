"""The library of saved configurations: one folder per user, each configuration a geometry file in it
named `<name>.json`, its plate read from the file and its date the file's modification time."""
import datetime
import os
from dataclasses import dataclass

from PySide6.QtCore import QStandardPaths

from . import document

FORBIDDEN = set('<>:"/\\|?*')


@dataclass(frozen=True)
class Kept:
    name: str
    path: str
    plate: tuple    # (height, width), or None when the file no longer reads as a geometry file
    date: datetime.datetime


def default_folder():
    """Qt's per-user application data location, which the application's organization and name set."""
    return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)


def listed(folder):
    """Every configuration in `folder`, by name; none when the folder is not there yet."""
    if not os.path.isdir(folder):
        return []
    out = []
    for entry in sorted(os.listdir(folder), key=str.casefold):
        path = os.path.join(folder, entry)
        if not entry.endswith(".json") or not os.path.isfile(path):
            continue
        try:
            plate = document.load(path)[0]
        except ValueError:
            plate = None
        out.append(Kept(entry[:-5], path, plate, datetime.datetime.fromtimestamp(os.path.getmtime(path))))
    return out


def refusal(folder, name):
    """Why `name` cannot be a new configuration's name in `folder`, or None when it can."""
    if not name or name != name.strip() or name.endswith("."):
        return "a configuration's name is not empty and neither starts nor ends with a space or a dot"
    if FORBIDDEN & set(name) or any(ord(c) < 32 for c in name):
        return f"a configuration's name holds none of {''.join(sorted(FORBIDDEN))}"
    if os.path.exists(os.path.join(folder, f"{name}.json")):
        return f"a configuration named {name} is already kept"
    return None


def keep(folder, name, plate, shapes, replace=False):
    """Writes the configuration, making the folder if need be. Raises ValueError with the refusal when
    the name cannot be used, a taken name being used when `replace`."""
    why = refusal(folder, name)
    if why is not None and not (replace and os.path.isfile(os.path.join(folder, f"{name}.json"))):
        raise ValueError(why)
    os.makedirs(folder, exist_ok=True)
    document.save(os.path.join(folder, f"{name}.json"), plate, shapes)


def rename(folder, old, new):
    why = refusal(folder, new)
    if why is not None:
        raise ValueError(why)
    os.rename(os.path.join(folder, f"{old}.json"), os.path.join(folder, f"{new}.json"))


def remove(folder, name):
    os.remove(os.path.join(folder, f"{name}.json"))
