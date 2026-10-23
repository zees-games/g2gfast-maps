#!/usr/bin/env python3
"""Writes maps/<id>/provides.json, one per map pack, the Workshop listing; the logic is dot-map's tools/build_provides.py.

    tools/build_provides.py            # rewrite
    tools/build_provides.py --check    # exit 1 if stale or an entry is bad

dot-map is a sibling checkout (`../dot-map`, where dot-bootstrap clones it) or `$DOTMAP_PATH`.
"""

import os
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


for _p in (os.environ.get("DOTMAP_PATH", ""), os.path.join(ROOT, "..", "dot-map")):
    if _p and os.path.isfile(os.path.join(_p, "tools", "build_provides.py")):
        sys.path.insert(0, os.path.join(_p, "tools"))
        break
else:
    sys.exit("build_provides: dot-map was not found. Clone it beside this repository or set DOTMAP_PATH.")
import build_provides  # noqa: E402

sys.exit(build_provides.run(ROOT, GAMES, pack="each", skip=SKIP, map_kind=map_kind))
