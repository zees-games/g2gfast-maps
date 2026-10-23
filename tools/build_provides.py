#!/usr/bin/env python3
"""Writes maps/<id>/provides.json, the Workshop listing of each map's pack.

    tools/build_provides.py            # rewrite every provides.json
    tools/build_provides.py --check    # exit 1 if one is stale, missing or names a file the pack lacks

Each map is its own pack (dot-ci's package-subpacks.sh puts the folder's files at the pack root),
so each folder carries its own file and `scene` is the map document beside it.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = ["gamemann/game-g2gfast"]
SKIP = {"buses_from_hell_fixed"}  # maps no accepted map_kind describes


def map_kind(mid):
    if mid.startswith("bunnyhop_"):
        return "bhop"
    for kind in ("bhop", "surf", "kz", "race"):
        if mid.startswith(kind + "_"):
            return kind
    return "surf"


def provides_for(mid):
    name = " ".join(w if w.isdigit() else w.capitalize() for w in mid.split("_"))
    return {
        "schema": 1,
        "title": name,
        "kinds": ["map"],
        "games": GAMES,
        "entries": [{"kind": "map", "id": mid, "name": name, "scene": mid + ".json", "map_kind": map_kind(mid)}],
    }


def main():
    check = "--check" in sys.argv
    bad = []
    count = 0
    for mid in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        folder = os.path.join(ROOT, "maps", mid)
        if not os.path.isdir(folder) or mid in SKIP or not os.listdir(folder):
            continue
        if not re.fullmatch(r"[a-z0-9_]+", mid):
            bad.append("bad id " + mid)
        if not os.path.isfile(os.path.join(folder, mid + ".json")):
            bad.append("missing " + mid + "/" + mid + ".json")
            continue
        text = json.dumps(provides_for(mid), indent=4) + "\n"
        path = os.path.join(folder, "provides.json")
        count += 1
        if check:
            if not os.path.exists(path) or open(path).read() != text:
                bad.append("stale or missing " + mid + "/provides.json")
        else:
            with open(path, "w") as f:
                f.write(text)
    if check:
        print("\n".join(bad) if bad else "every map has its provides.json (%d)" % count)
    else:
        print("\n".join(bad) if bad else "wrote %d provides.json" % count)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
