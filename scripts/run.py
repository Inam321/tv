#!/usr/bin/env python3
"""
run.py - run the whole pipeline with one command.

    python scripts/run.py

Runs, in order:
    1. build.py       fetch iptv-org, apply config rules
    2. verify.py      test every stream, keep only what plays
    3. combine.py     build all.m3u  (Android TV, group folders)
    4. menu.py        build menu.m3u (SS IPTV, folder tiles)
    5. make_index.py  build the status page

The repo name comes from "repo" in config.json, so no arguments are needed.
Stops immediately if a step fails.

OPTIONS
    --repo USER/REPO     override the repo name from config.json
    --workers N          parallel stream checks   (default from verify.py)
    --timeout N          seconds per request
    --retries N          extra attempts for timeouts
    --skip-verify        reuse the previous verification results
    --only FILE.m3u      verify just one playlist (quick test)
"""

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sh(label, args):
    """Run a step. Returns elapsed seconds, or exits on failure."""
    print()
    print("=" * 68)
    print(f"  {label}")
    print("=" * 68, flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable] + args, cwd=ROOT)
    el = time.time() - t0
    if r.returncode != 0:
        print(f"\n!! {label} failed (exit {r.returncode}). Stopping.",
              file=sys.stderr)
        sys.exit(r.returncode)
    return el


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--repo")
    ap.add_argument("--workers")
    ap.add_argument("--timeout")
    ap.add_argument("--retries")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()

    cfg_path = os.path.join(ROOT, args.config)
    if not os.path.isfile(cfg_path):
        print(f"!! {args.config} not found. Run this from the project folder.",
              file=sys.stderr)
        return 1
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    repo = args.repo or cfg.get("repo") or os.environ.get("GITHUB_REPOSITORY")
    if not repo or "/" not in repo:
        print('!! No repo name. Add "repo": "USER/REPO" to config.json '
              "or pass --repo USER/REPO.", file=sys.stderr)
        return 1

    base = f"https://raw.githubusercontent.com/{repo}/main/docs"
    print(f"repo : {repo}")
    print(f"base : {base}")

    times = {}
    t_all = time.time()

    times["build"] = sh("1/5  Building playlists from iptv-org",
                        ["scripts/build.py", "--config", args.config])

    if args.skip_verify:
        print("\n(skipping verification, reusing previous docs/)")
        times["verify"] = 0.0
    else:
        v = ["scripts/verify.py", "--config", args.config]
        for flag, val in (("--workers", args.workers),
                          ("--timeout", args.timeout),
                          ("--retries", args.retries),
                          ("--only", args.only)):
            if val:
                v += [flag, str(val)]
        times["verify"] = sh("2/5  Testing every stream", v)

    times["combine"] = sh("3/5  Building all.m3u for Android TV",
                          ["scripts/combine.py", "--config", args.config])

    times["menu"] = sh("4/5  Building menu.m3u for SS IPTV",
                       ["scripts/menu.py", "--config", args.config,
                        "--base", base])

    times["index"] = sh("5/5  Building the status page",
                        ["scripts/make_index.py", "--repo", repo])

    # ---- summary
    status = os.path.join(ROOT, "docs", "status.json")
    print()
    print("=" * 68)
    print("  DONE")
    print("=" * 68)

    if os.path.isfile(status):
        with open(status, encoding="utf-8") as f:
            st = json.load(f)
        total = 0
        for p in st.get("playlists", []):
            total += p["channels_working"]
            print(f"  {p['title'][:38]:<38} {p['channels_working']:>5} "
                  f"of {p['streams_tested']:>5} streams")
        print(f"  {'TOTAL':<38} {total:>5} working channels")

    print(f"\n  elapsed: {time.time() - t_all:.0f}s "
          f"(verify {times['verify']:.0f}s)")

    print("\n  Your links:")
    print(f"    SS IPTV      {base}/menu.m3u")
    print(f"    Android TV   {base}/all.m3u")

    print("\n  Next: upload the docs folder to GitHub, or let the daily")
    print("        workflow publish it for you.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
