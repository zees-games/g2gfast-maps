#!/usr/bin/env python3
"""Every spawn and teleport destination of every map lands where a player can stand; the check is dot-map-convert's tools/check_playable.py.

    tools/check_playable.py                  every map (what CI runs)
    tools/check_playable.py surf_mesa ...    these maps
    tools/check_playable.py -v               list every problem

Failures not fixed yet are held by exact count in tools/playable_known.json.
dot-map-convert is a sibling checkout (`../dot-map-convert`, where dot-bootstrap clones it) or `$DOT_MAP_CONVERT_PATH`.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for _p in (os.environ.get("DOT_MAP_CONVERT_PATH", ""), os.path.join(ROOT, "..", "dot-map-convert")):
    if _p and os.path.isfile(os.path.join(_p, "tools", "check_playable.py")):
        sys.path.insert(0, os.path.join(_p, "tools"))
        break
else:
    sys.exit("check_playable: dot-map-convert was not found. Clone it beside this repository or set DOT_MAP_CONVERT_PATH.")
import check_playable  # noqa: E402

sys.exit(check_playable.main(root=ROOT))
