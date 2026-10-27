"""Write lucide-icons.html: every icon in a Lucide release, drawn the way sieve_player draws its glyphs.

Lucide is the line-icon set SIEVE vendors from (sieve_player/glyphs, and src/sieve/gui/icons/lucide on
v4). This page is the catalogue to pick from: one tile per icon, tinted to the theme's inks on the
theme's ground, searchable by name and by Lucide's own tags. Run with a release tag to rebuild:

    python -X utf8 mock-up/reference/build_icons.py 1.61.0

The release zip is fetched from GitHub into a temp folder; nothing but the html lands here.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
import zipfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sieve_player.theme import ACCENT, GROUND, HEAD, INK, INK_2, STEP, FONT_PX  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "lucide-icons.html"
ZIP = "https://github.com/lucide-icons/lucide/releases/download/{v}/lucide-icons-{v}.zip"
LICENSE = "https://raw.githubusercontent.com/lucide-icons/lucide/{v}/LICENSE"
STROKE = 2.25   # Lucide's 2 reads thin at 16px; v4's icons module widened it to this


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url) as r:
        return r.read()


def build(version: str) -> None:
    z = zipfile.ZipFile(io.BytesIO(fetch(ZIP.format(v=version))))
    icons: dict[str, dict] = {}
    for info in z.infolist():
        p = Path(info.filename)
        if p.suffix == ".svg":
            icons.setdefault(p.stem, {})["svg"] = z.read(info).decode("utf-8")
        elif p.suffix == ".json" and p.stem in icons or p.suffix == ".json":
            meta = json.loads(z.read(info))
            icons.setdefault(p.stem, {})["tags"] = meta.get("tags", [])
            icons[p.stem]["cats"] = meta.get("categories", [])
    icons = {k: v for k, v in sorted(icons.items()) if "svg" in v}
    try:
        licence = fetch(LICENSE.format(v=version)).decode("utf-8")
    except Exception:  # a tag without the file at that path; the ISC text is in every release
        licence = "ISC License — see https://github.com/lucide-icons/lucide/blob/main/LICENSE"

    cats = sorted({c for v in icons.values() for c in v.get("cats", [])})
    tiles = []
    for name, v in icons.items():
        body = v["svg"].split(">", 1)[1].rsplit("</svg>", 1)[0].strip()
        body = " ".join(body.split())
        tags = " ".join(v.get("tags", []))
        tiles.append(
            f'<figure data-n="{name}" data-t="{escape(tags)}" data-c="{escape(" ".join(v.get("cats", [])))}" '
            f'title="{escape(name)}\n{escape(", ".join(v.get("tags", [])))}">'
            f'<svg viewBox="0 0 24 24">{body}</svg><figcaption>{name}</figcaption></figure>'
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
Rebuild: python -X utf8 mock-up/reference/build_icons.py &lt;release&gt;

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
    print(f"{OUT}: {len(icons)} icons, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "1.61.0")
