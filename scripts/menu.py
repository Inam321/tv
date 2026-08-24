#!/usr/bin/env python3
"""
menu.py - build a single "menu" playlist whose entries are folders.

SS IPTV supports the attribute content-type="playlist", which tells it that
an entry points at another playlist rather than a stream. Loading this one
file therefore produces a screen of folder tiles:

    menu.m3u
      |- News            -> news.m3u
      |- Music           -> music.m3u
      |- Movies          -> movies.m3u
      |- Entertainment   -> entertainment.m3u
      |- Kids            -> kids.m3u
      |- Religious       -> religious-pk.m3u
      |- Sports          -> sports.m3u

It also uses #EXTSIZE and #EXTBG, which are SS IPTV specific, to give each
folder a sized, coloured tile.

NOTE: content-type, #EXTSIZE and #EXTBG are SS IPTV extensions. Other apps
may ignore or mishandle them, which is why all.m3u (built by combine.py)
exists separately for Android TV players.

Requires docs/status.json so channel counts can go on the tiles.

USAGE
    python scripts/menu.py --base https://raw.githubusercontent.com/USER/REPO/main/docs
    python scripts/menu.py --base https://user.github.io/repo
"""

import argparse
import json
import os
import sys

# file -> (folder label, tile colour, tile size)
TILES = [
    ("news.m3u",          "News",          "#1D3B5C", "big"),
    ("sports.m3u",        "Sports",        "#1F5B3A", "big"),
    ("entertainment.m3u", "Entertainment", "#5C2A4A", "medium"),
    ("music.m3u",         "Music",         "#6B3A12", "medium"),
    ("movies.m3u",        "Movies",        "#3A2B5C", "medium"),
    ("kids.m3u",          "Kids",          "#7A4A0F", "small"),
    ("religious-pk.m3u",  "Religious",     "#2A4A4A", "small"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True,
                    help="URL folder the .m3u files are served from, no "
                         "trailing slash")
    ap.add_argument("--status", default="docs/status.json")
    ap.add_argument("--out", default="docs/menu.m3u")
    args = ap.parse_args()

    base = args.base.rstrip("/")

    counts = {}
    if os.path.isfile(args.status):
        with open(args.status, encoding="utf-8") as f:
            st = json.load(f)
        for p in st.get("playlists", []):
            counts[p["file"]] = p.get("channels_working", 0)

    lines = ["#EXTM3U"]
    total = 0
    shown = []

    for fname, label, colour, size in TILES:
        n = counts.get(fname)
        if n == 0:
            continue                       # skip an empty folder entirely
        desc = f"{n} channels" if n else "verified working channels"
        total += n or 0
        lines.append(
            f'#EXTINF:-1 content-type="playlist" description="{desc}",{label}'
        )
        lines.append(f"#EXTSIZE: {size}")
        lines.append(f"#EXTBG: {colour}")
        lines.append(f"{base}/{fname}")
        shown.append((label, n, size))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"wrote {args.out}")
    print(f"  base URL: {base}\n")
    for label, n, size in shown:
        print(f"  {label:<16} {str(n or '?'):>5} channels   tile: {size}")
    print(f"  {'TOTAL':<16} {total:>5} channels in {len(shown)} folders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
