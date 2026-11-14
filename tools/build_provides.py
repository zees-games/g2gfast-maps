#!/usr/bin/env python3
"""Writes maps/<id>/provides.json, one per map pack, the Workshop listing; the logic is dot-map-convert's tools/build_provides.py.

    tools/build_provides.py            # rewrite
    tools/build_provides.py --check    # exit 1 if stale or an entry is bad

dot-map-convert is a sibling checkout (`../dot-map-convert`, where dot-bootstrap clones it) or `$DOT_MAP_CONVERT_PATH`.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = ["gamemann/game-g2gfast"]
# The Workshop page every map pack joins as a member (the site never gives one map a page of its own).
COLLECTION = "airdrift-maps"
SKIP = set()


def map_kind(mid):
    if mid.startswith("bunnyhop_"):
        return "bhop"
    for kind in ("bhop", "surf", "kz", "race"):
        if mid.startswith(kind + "_"):
            return kind
    return "surf"


for _p in (os.environ.get("DOT_MAP_CONVERT_PATH", ""), os.path.join(ROOT, "..", "dot-map-convert")):
    if _p and os.path.isfile(os.path.join(_p, "tools", "build_provides.py")):
        sys.path.insert(0, os.path.join(_p, "tools"))
        break
else:
    sys.exit("build_provides: dot-map-convert was not found. Clone it beside this repository or set DOT_MAP_CONVERT_PATH.")
import build_provides  # noqa: E402

sys.exit(build_provides.run(ROOT, GAMES, pack="each", skip=SKIP, map_kind=map_kind, collection=COLLECTION))
