"""Fetch a Tabler Icons release into tabler.zip beside this file, with its licence beside both.

Tabler Icons is the line-icon set SIEVE vendors from (sieve_player/glyphs). tabler.zip is the
catalogue Dev > Icon reference scrolls: the package's icons/outline and icons/filled svgs,
icons.json (category and tags per icon), its LICENSE, and a VERSION file naming the release. The
zip and the licence are downloads, not sources: both are gitignored, and the sheet offers the
download when they are missing. From a shell, with no argument it fetches VERSION:

    .venv/Scripts/python -X utf8 sieve_player/dev/reference/build_icons.py [version]

Tabler is MIT: the notice is kept in the zip and written beside it as LICENSE.tabler, and must
travel with any icon copied into sieve_player/glyphs.
"""
from __future__ import annotations

import io
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ZIP, LICENSE = HERE / "tabler.zip", HERE / "LICENSE.tabler"
VERSION = "3.49.0"
RELEASE = "https://registry.npmjs.org/@tabler/icons/-/icons-{v}.tgz"   # the svgs, icons.json, LICENSE


def download(version: str = VERSION) -> None:
    with urllib.request.urlopen(RELEASE.format(v=version)) as r:
        src = tarfile.open(fileobj=io.BytesIO(r.read()), mode="r:gz")
    with src, zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as dst:
        for m in src.getmembers():
            name = m.name.removeprefix("package/")
            keep = (name.startswith("icons/") and name.endswith(".svg")) or name in ("icons.json", "LICENSE")
            if m.isfile() and keep:
                data = src.extractfile(m).read()
                dst.writestr(name, data)
                if name == "LICENSE":
                    LICENSE.write_bytes(data)
        dst.writestr("VERSION", version)


if __name__ == "__main__":
    download(sys.argv[1] if len(sys.argv) > 1 else VERSION)
    sys.path.insert(0, str(HERE.parents[2]))
    from sieve_player.dev.reference.icons import read_icons
    icons, version, _ = read_icons(ZIP)
    print(f"{ZIP.name}: Tabler Icons {version}, {len(icons)} icons, "
          f"{sum(1 for i in icons if i.filled)} also filled, {ZIP.stat().st_size // 1024} KB")
