"""Every document under a folder: what `--plan` prints of it, and, where a node of it serves a file
in the player, every node's key as a Graph plans it under the store as it stands.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-the-plans-as-they-stand.py video-tests out.md

The Graph is the player's, with no window: the video its selector picks and each path input's
loader laid on its node, as window.py's _pick_paths does."""
import contextlib
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())

from sieve_player import document  # noqa: E402
from sieve_player.__main__ import show_plan  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402


def documents(folder):
    for root, _, names in sorted(os.walk(folder)):
        for name in sorted(names):
            path = os.path.join(root, name)
            if not name.endswith(".json"):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and "nodes" in d:
                yield path


def printed(path, tools):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        show_plan(path, tools)
    return out.getvalue().rstrip("\n")


def in_the_player(path, tools):
    """[(node, key, the file it serves or "")] as a Graph plans the document, or a str saying why
    there is no Graph."""
    doc = document.load(path, tools)
    video, why = document.pick_video(doc, tools)
    if video is None or not os.path.exists(video):
        return f"no video: {why or video}"
    for n in doc.nodes:
        for name, loader in document.paths(tools.get(n.tool)).items():
            picked, _ = document.pick_path(doc, tools, n.id, name)
            if picked is not None:
                try:
                    n.params = {**n.params, **loader(picked)}
                except Exception as e:
                    return f"{n.id}'s {name} did not load: {type(e).__name__}: {e}"
    decoder = Decoder(video)
    try:
        entries = Graph(doc, decoder, tools).snapshot().entries
        return [(n.id, entries[n.id].key, "" if entries[n.id].file is None
                 else f"{os.path.basename(entries[n.id].file[0])}, print {entries[n.id].file[1]}") for n in doc.nodes]
    finally:
        decoder.close()


def main(folder, out):
    tools = {e.name: e.module for e in discover("tools") if e.ok}
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    first, second = [], []
    for path in documents(folder):
        name = path.replace(os.sep, "/")
        try:
            first += [f"### `{name}`", "", "```", printed(path, tools), "```", ""]
        except Exception as e:
            first += [f"### `{name}`", "", f"`--plan` raised {type(e).__name__}: {e}", ""]
            continue
        try:
            rows = in_the_player(path, tools)
        except Exception as e:
            rows = f"{type(e).__name__}: {e}"
        if isinstance(rows, str):
            second += [f"### `{name}`", "", f"Not planned: {rows}", ""]
        elif any(file for _, _, file in rows):
            second += [f"### `{name}`", "", "| node | key | serves |", "| --- | --- | --- |",
                       *(f"| {nid} | {key} | {file} |" for nid, key, file in rows), ""]
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join([f"Printed at `{commit}`.", "", "## What `--plan` prints", "", *first,
                           "## The keys in the player, of each document a node of which serves a file", "", *second]))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
