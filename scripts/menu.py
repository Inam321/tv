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

DEFAULT_COLOURS = ["#1D3B5C", "#1F5B3A", "#5C2A4A", "#6B3A12",
                   "#3A2B5C", "#7A4A0F", "#2A4A4A"]


def load_tiles(config_path):
    """Read (file, label, colour, size) from config.json, in config order."""
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    tiles = []
    for i, pl in enumerate(cfg["playlists"]):
        label = (pl.get("folder")
                 or (pl["categories"][0].title() if pl.get("categories")
                     else pl["title"]))
        colour = pl.get("colour") or DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)]
        size = pl.get("size") or ("big" if i < 2 else
                                  "medium" if i < 5 else "small")
        tiles.append((pl["file"], label, colour, size))
    return tiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True,
                    help="URL folder the .m3u files are served from, no "
                         "trailing slash")
    ap.add_argument("--config", default="config.json")
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

    for fname, label, colour, size in load_tiles(args.config):
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
