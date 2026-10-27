"""Fetch a Lucide release into lucide.zip beside this file, and write lucide-icons.html from it.

Lucide is the line-icon set SIEVE vendors from (sieve_player/glyphs, and src/sieve/gui/icons/lucide on
v4). lucide.zip is the catalogue the window's Dev > Reference > Icons sheet scrolls
(sieve_player/dev/reference/icons.py); the html is the same catalogue for a browser: one tile per
icon, tinted to the theme's inks on the theme's ground, searchable by name and by Lucide's own tags.
Rebuild both with a release tag; with no tag, the html is rebuilt from the zip already here:

    .venv/Scripts/python -X utf8 mock-up/reference/build_icons.py 1.61.0
"""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sieve_player.dev.reference.icons import STROKE, read_icons  # noqa: E402
from sieve_player.theme import ACCENT, FONT_PX, GROUND, HEAD, INK, INK_2, STEP  # noqa: E402

HERE = Path(__file__).parent
ZIP, OUT = HERE / "lucide.zip", HERE / "lucide-icons.html"
RELEASE = "https://github.com/lucide-icons/lucide/releases/download/{v}/lucide-icons-{v}.zip"
LICENSE = "https://raw.githubusercontent.com/lucide-icons/lucide/{v}/LICENSE"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url) as r:
        return r.read()


def download(version: str) -> None:
    """lucide.zip: the release's icons/ folder, its LICENSE, and a VERSION file naming the tag."""
    src = zipfile.ZipFile(io.BytesIO(fetch(RELEASE.format(v=version))))
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename.startswith("icons/") and info.filename.endswith((".svg", ".json")):
                dst.writestr(info.filename, src.read(info))
        dst.writestr("LICENSE", fetch(LICENSE.format(v=version)))
        dst.writestr("VERSION", version)


def build() -> None:
    icons, version, licence = read_icons(ZIP)
    cats = sorted({c for i in icons for c in i.cats})
    tiles = []
    for i in icons:
        tiles.append(
            f'<figure data-n="{i.name}" data-t="{escape(" ".join(i.tags))}" data-c="{escape(" ".join(i.cats))}" '
            f'title="{escape(i.name)}\n{escape(", ".join(i.tags))}">'
            f'<svg viewBox="0 0 24 24">{i.body}</svg><figcaption>{i.name}</figcaption></figure>'
        )

    g = lambda n: f"rgb({n},{n},{n})"
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Lucide {version} — the icons SIEVE can vendor</title>
<style>
:root {{ --ground:{g(GROUND)}; --l1:{g(GROUND+STEP)}; --l2:{g(GROUND+2*STEP)}; --l3:{g(GROUND+3*STEP)};
        --head:{g(HEAD)}; --ink:{g(INK)}; --ink2:{g(INK_2)}; --accent:{ACCENT.name()}; --ink-now:var(--ink); --size:16px; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--ground); color:var(--ink); font:{FONT_PX}px/1.5 Inter, "Segoe UI", system-ui, sans-serif }}
header {{ position:sticky; top:0; background:var(--ground); padding:16px 24px 8px; border-bottom:1px solid var(--l2); display:flex; gap:16px; align-items:center; flex-wrap:wrap }}
h1 {{ font-size:{FONT_PX}px; font-weight:600; color:var(--head); margin:0 }}
header span.n {{ color:var(--ink2); font-family:Consolas, monospace }}
input, select {{ background:var(--ground); color:var(--ink); border:1px solid var(--l3); border-radius:4px; height:22px; padding:0 8px; font:inherit }}
input {{ width:260px }} input:focus {{ outline:none; border-color:var(--accent) }}
label {{ color:var(--ink2); display:flex; gap:6px; align-items:center }}
main {{ padding:16px 24px; display:grid; grid-template-columns:repeat(auto-fill, minmax(120px, 1fr)); gap:2px }}
figure {{ margin:0; padding:8px 4px; border-radius:4px; display:flex; flex-direction:column; align-items:center; gap:6px; cursor:pointer; background:var(--l1) }}
figure:hover {{ background:var(--l2) }} figure.hide {{ display:none }}
figure.vendored {{ outline:1px solid var(--accent) }}
figure.copied figcaption {{ color:var(--accent) }}
svg {{ width:var(--size); height:var(--size); fill:none; stroke:var(--ink-now); stroke-width:{STROKE}; stroke-linecap:round; stroke-linejoin:round; flex:none }}
figcaption {{ font-family:Consolas, "Cascadia Mono", monospace; font-size:11px; color:var(--ink2); text-align:center; word-break:break-all }}
footer {{ padding:16px 24px 32px; color:var(--ink2); white-space:pre-wrap; font-family:Consolas, monospace; font-size:11px; border-top:1px solid var(--l2) }}
</style></head><body>
<header>
<h1>Lucide {version}</h1><span class="n">{len(icons)} icons · <b id="shown">{len(icons)}</b> shown</span>
<input id="q" placeholder="name or tag" autofocus>
<label>category <select id="cat"><option value="">all</option>{"".join(f'<option>{c}</option>' for c in cats)}</select></label>
<label>size <select id="size"><option>16</option><option>20</option><option>24</option><option>48</option></select></label>
<label>ink <select id="ink"><option value="ink">INK {INK}</option><option value="ink2">INK_2 {INK_2}</option><option value="head">HEAD {HEAD}</option><option value="accent">ACCENT</option></select></label>
<span class="n">click a tile to copy its name</span>
</header>
<main>{"".join(tiles)}</main>
<footer>Stroke shown at {STROKE} (Lucide ships 2; too thin at 16px). Inks and grays come from sieve_player/theme.py at build time.
Rebuild: python -X utf8 mock-up/reference/build_icons.py [release]

{escape(licence)}</footer>
<script>
const q=document.getElementById('q'), cat=document.getElementById('cat'), shown=document.getElementById('shown');
const tiles=[...document.querySelectorAll('figure')];
function filter(){{
  const s=q.value.trim().toLowerCase(), c=cat.value; let n=0;
  for (const f of tiles) {{
    const ok=(!s || f.dataset.n.includes(s) || f.dataset.t.includes(s)) && (!c || f.dataset.c.split(' ').includes(c));
    f.classList.toggle('hide', !ok); n+=ok;
  }}
  shown.textContent=n;
}}
q.oninput=cat.onchange=filter;
document.getElementById('size').onchange=e=>document.documentElement.style.setProperty('--size', e.target.value+'px');
document.getElementById('ink').onchange=e=>document.documentElement.style.setProperty('--ink-now', `var(--${{e.target.value}})`);
for (const f of tiles) f.onclick=()=>{{ navigator.clipboard.writeText(f.dataset.n); f.classList.add('copied'); setTimeout(()=>f.classList.remove('copied'), 600); }};
</script></body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name}: Lucide {version}, {len(icons)} icons, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        download(sys.argv[1])
    build()
