#!/usr/bin/env python3
"""
combine.py - merge the verified playlists into a single all.m3u with folders.

Players that honour `group-title` (TiviMate, IPTV Smarters, OTT Navigator,
VLC, Kodi) show one folder per category, so a single link behaves like:

    IPTV
     |- News
     |- Music
     |- Movies
     |- Entertainment
     |- Kids
     |- Religious
     |- Sports

SS IPTV ignores group-title, so it will show one flat list instead. For SS
IPTV, add the seven separate playlists as external playlists - each becomes
its own tile on the main screen, which gives the same result.

Run after verify.py.

USAGE
    python scripts/combine.py
    python scripts/combine.py --out docs/all.m3u
"""

import argparse
import json
import os
import re
import sys

def load_folders(config_path):
    """Read (file, folder label) pairs from config.json, in config order."""
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    out = []
    for pl in cfg["playlists"]:
        label = (pl.get("folder")
                 or (pl["categories"][0].title() if pl.get("categories")
                     else pl["title"]))
        out.append((pl["file"], label))
    return out


# Country code -> readable name, used to sub-label channels inside a folder.
CC = {"PK": "Pakistan", "IN": "India"}


def parse(path):
    """Return list of (extinf, [opt lines], url)."""
    if not os.path.isfile(path):
        return []
    txt = open(path, encoding="utf-8", errors="replace").read()
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    out, ext, opts = [], None, []
    for line in txt.split("\n"):
        line = line.strip()
        if not line or line.startswith("#EXTM3U") or (
                line.startswith("#") and not line.startswith("#EXT")):
            continue
        if line.startswith("#EXTINF"):
            ext, opts = line, []
        elif line.startswith("#EXT"):
            if ext:
                opts.append(line)
        elif line.startswith(("http://", "https://")):
            if ext:
                out.append((ext, opts[:], line))
            ext, opts = None, []
    return out


def country_of(extinf):
    m = re.search(r'tvg-country="([^"]*)"', extinf)
    if m and m.group(1):
        return m.group(1).split(";")[0].strip().upper()
    m = re.search(r'tvg-id="[^"]*\.([a-z]{2})', extinf)
    return m.group(1).upper() if m else ""


def name_of(extinf):
    return extinf.split(",", 1)[1].strip() if "," in extinf else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--indir", default="docs")
    ap.add_argument("--out", default="docs/all.m3u")
    ap.add_argument("--prefix-country", action="store_true", default=True,
                    help="show country in the channel name inside each folder")
    args = ap.parse_args()

    lines = ["#EXTM3U"]
    total = 0
    report = []

    for fname, folder in load_folders(args.config):
        entries = parse(os.path.join(args.indir, fname))
        if not entries:
            report.append((folder, 0))
            continue

        # Pakistan first inside each folder, then India, then the rest.
        def sort_key(e):
            cc = country_of(e[0])
            rank = {"PK": 0, "IN": 1}.get(cc, 2)
            return (rank, name_of(e[0]).lower())

        entries.sort(key=sort_key)

        for extinf, opts, url in entries:
            cc = country_of(extinf)
            # replace whatever group-title was there with the folder name
            new = re.sub(r'\s*group-title="[^"]*"', "", extinf)
            head, _, chan = new.partition(",")
            if args.prefix_country and cc in CC:
                chan = f"[{cc}] {chan}"
            lines.append(f'{head} group-title="{folder}",{chan}')
            lines.extend(opts)
            lines.append(url)
            total += 1

        report.append((folder, len(entries)))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"wrote {args.out}")
    for folder, n in report:
        print(f"  {folder:<16} {n:>4} channels")
    print(f"  {'TOTAL':<16} {total:>4} channels in {len(report)} folders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
