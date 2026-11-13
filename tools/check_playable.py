#!/usr/bin/env python3
"""check_playable -- every spawn and every teleport destination of every map lands somewhere a player can be.

Reads only what the game loads (maps/<id>/<id>.json and the collision block of <id>.bin), so it
checks the converted map, not the importer's own opinion of it. Per map it fails when:

    no_spawn          the manifest has no `spawn` or an empty `spawns`
    no_audit          the manifest predates the importer's teleport audit (regenerate the map)
    audit_broken      the importer's `teleport_audit.broken` lists a teleport
    no_destination    a TELEPORT, STAGE, START or SPAWN zone, or a door block, has no destination
    out_of_bounds     a destination or spawn lies outside the map's bounds
    in_solid          a destination or spawn is inside a collision hull (feet or crouched middle)
    no_floor          nothing at all is under a destination or spawn: the player falls out of the world
    lands_in_pit      a destination is inside a pit or teleport sending somewhere else

    tools/check_playable.py                  every map (what CI runs)
    tools/check_playable.py surf_mesa ...    these maps
    tools/check_playable.py -v               list every problem, not the first few per map

A map listed in tools/playable_known.json with exactly the failure counts it records is
reported as `known` and does not fail the run; each entry names its reason and the nightly
item fixing it. A known map that now passes, or fails differently, fails the run until the
entry is removed or updated, so the list can only shrink by a fix.
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UP = 1                      # manifests are in map units on Godot axes: y is up
PROBES = (8.0, 36.0)        # just above the feet and a crouched player's middle, as the importer probes
DEPTH = 4.0                 # a probe this far inside every face of a hull is stuck, not touching it
BOUNDS_SLACK = 64.0
CELL = 512.0
SAME = 2.0                  # two destinations this close are the same place
DESTINATION_LIFT = 24.0     # dot-map-convert bsp_import.py: destinations sit this far above the authored point
DESTINED = ("TELEPORT", "STAGE", "START", "SPAWN")


def read_hulls(blob, col):
    hulls, off = [], col["hull_offset"]
    for _ in range(col["hull_count"]):
        n = struct.unpack_from("<I", blob, off)[0]
        flat = struct.unpack_from("<%df" % (3 * n), blob, off + 4)
        hulls.append([flat[i:i + 3] for i in range(0, len(flat), 3)])
        off += 4 + 12 * n
    return hulls


def read_displacements(blob, col):
    nv, ni = col.get("displacement_vertex_count", 0), col.get("displacement_index_count", 0)
    if not nv or not ni:
        return []
    flat = struct.unpack_from("<%df" % (3 * nv), blob, col["displacement_vertex_offset"])
    verts = [flat[i:i + 3] for i in range(0, len(flat), 3)]
    idx = struct.unpack_from("<%dI" % ni, blob, col["displacement_index_offset"])
    return [(verts[idx[i]], verts[idx[i + 1]], verts[idx[i + 2]]) for i in range(0, ni - 2, 3)]


def planes_of(pts):
    """The face planes of a convex point cloud, as (normal, d) with points satisfying n.p <= d."""
    out, n = [], len(pts)
    for i in range(n):
        a = pts[i]
        for j in range(i + 1, n):
            b = pts[j]
            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            for k in range(j + 1, n):
                c = pts[k]
                ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                nx, ny, nz = ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]
                ln = math.sqrt(nx * nx + ny * ny + nz * nz)
                if ln < 1e-6:
                    continue
                nx, ny, nz = nx / ln, ny / ln, nz / ln
                d = nx * a[0] + ny * a[1] + nz * a[2]
                above = below = False
                for p in pts:
                    s = nx * p[0] + ny * p[1] + nz * p[2] - d
                    if s > 0.01:
                        above = True
                    elif s < -0.01:
                        below = True
                    if above and below:
                        break
                if above and below:
                    continue
                if above:
                    nx, ny, nz, d = -nx, -ny, -nz, -d
                if not any(abs(q[0] - nx) < 1e-4 and abs(q[1] - ny) < 1e-4 and abs(q[2] - nz) < 1e-4
                           and abs(q[3] - d) < 0.01 for q in out):
                    out.append((nx, ny, nz, d))
    return out


class Map:
    def __init__(self, mid, doc, blob):
        self.id, self.doc = mid, doc
        col = doc.get("collision", {})
        self.hulls = read_hulls(blob, col) if col.get("hull_count") else []
        self.boxes = [([min(p[a] for p in h) for a in range(3)], [max(p[a] for p in h) for a in range(3)])
                      for h in self.hulls]
        self.planes = {}
        self.grid = {}
        for i, (lo, hi) in enumerate(self.boxes):
            for cell in self._cells(lo, hi):
                self.grid.setdefault(cell, []).append(i)
        self.disp = read_displacements(blob, col)
        self.disp_grid = {}
        for t in self.disp:
            lo = [min(v[a] for v in t) for a in range(3)]
            hi = [max(v[a] for v in t) for a in range(3)]
            for cell in self._cells(lo, hi):
                self.disp_grid.setdefault(cell, []).append(t)
        b = doc.get("bounds", {})
        if b.get("min") and b.get("max"):
            self.bounds = ([min(b["min"][a], b["max"][a]) - BOUNDS_SLACK for a in range(3)],
                           [max(b["min"][a], b["max"][a]) + BOUNDS_SLACK for a in range(3)])
        else:
            self.bounds = None
        self.zones = doc.get("zones", [])

    @staticmethod
    def _cells(lo, hi):
        for x in range(int(math.floor(lo[0] / CELL)), int(math.floor(hi[0] / CELL)) + 1):
            for z in range(int(math.floor(lo[2] / CELL)), int(math.floor(hi[2] / CELL)) + 1):
                yield (x, z)

    def _cell(self, p):
        return (int(math.floor(p[0] / CELL)), int(math.floor(p[2] / CELL)))

    def in_solid(self, p):
        for i in self.grid.get(self._cell(p), ()):
            lo, hi = self.boxes[i]
            if not all(lo[a] + DEPTH <= p[a] <= hi[a] - DEPTH for a in range(3)):
                continue
            pl = self.planes.get(i)
            if pl is None:
                pl = self.planes[i] = planes_of(self.hulls[i])
            if pl and all(q[0] * p[0] + q[1] * p[1] + q[2] * p[2] - q[3] <= -DEPTH for q in pl):
                return True
        return False

    def has_floor(self, p):
        for i in self.grid.get(self._cell(p), ()):
            lo, hi = self.boxes[i]
            if lo[0] <= p[0] <= hi[0] and lo[2] <= p[2] <= hi[2] and lo[UP] <= p[UP]:
                return True
        for t in self.disp_grid.get(self._cell(p), ()):
            if _under(t, p):
                return True
        for z in self.zones:
            if z["kind"] == "RESPAWN" and z["min"][0] <= p[0] <= z["max"][0] and z["min"][2] <= p[2] <= z["max"][2] \
                    and min(z["min"][UP], z["max"][UP]) <= p[UP]:
                return True
        return False

    def out_of_bounds(self, p):
        return self.bounds is not None and not all(self.bounds[0][a] <= p[a] <= self.bounds[1][a] for a in range(3))

    def relay_at(self, p):
        """A zone with its own destination around p: it moves the player on (or holds them) at
        once, so a destination inside one is a hop, not a landing. bhop_arcane_v2's stage
        "stop" cells sit inside a player clip slab and pass straight on; that zone's own
        destination is checked as a landing in its turn."""
        for z in self.zones:
            if z.get("destination") is not None and "min" in z \
                    and all(min(z["min"][a], z["max"][a]) <= p[a] <= max(z["min"][a], z["max"][a]) for a in range(3)):
                return z
        return None

    def pit_at(self, p, track, dest):
        """The pit or teleport a player standing at p is caught by, if it sends somewhere else."""
        for z in self.zones:
            if z["kind"] not in ("RESPAWN", "TELEPORT") or z.get("track", 0) != track:
                continue
            if not all(min(z["min"][a], z["max"][a]) <= p[a] <= max(z["min"][a], z["max"][a]) for a in range(3)):
                continue
            to = z.get("destination")
            if to is not None and dest is not None and all(abs(to[a] - dest[a]) <= SAME for a in range(3)):
                continue    # a holding cell: it sends back to where the player already is
            if z["kind"] == "TELEPORT":
                continue    # a door: it sends the player on, which its own entry checks
            return z
        return None


def _under(t, p):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
    if abs(d) < 1e-9:
        return False
    l1 = ((bz - cz) * (p[0] - cx) + (cx - bx) * (p[2] - cz)) / d
    l2 = ((cz - az) * (p[0] - cx) + (ax - cx) * (p[2] - cz)) / d
    l3 = 1.0 - l1 - l2
    if min(l1, l2, l3) < -1e-6:
        return False
    return l1 * ay + l2 * by + l3 * cy <= p[UP]


def check(m):
    doc, problems = m.doc, []

    def place(what, at, track=0, pits=False):
        p = list(at)
        if m.out_of_bounds(p):
            problems.append(("out_of_bounds", what, p))
            return
        feet = list(p)
        feet[UP] += PROBES[0]
        if m.relay_at(feet) is not None:
            return
        # The importer lifts destinations DESTINATION_LIFT above the authored point, so a
        # crawlway that fits a ducked player (bhop_exodus) is probed from both heights.
        def stuck(base):
            return any(m.in_solid([base[a] + (lift if a == UP else 0.0) for a in range(3)]) for lift in PROBES)
        if stuck(p) and stuck([p[a] - (DESTINATION_LIFT if a == UP else 0.0) for a in range(3)]):
            problems.append(("in_solid", what, p))
            return
        if not m.has_floor(p):
            problems.append(("no_floor", what, p))
            return
        if pits:
            q = list(p)
            q[UP] += PROBES[0]
            z = m.pit_at(q, track, p)
            if z is not None:
                problems.append(("lands_in_pit", what, p))

    spawn = doc.get("spawn") or {}
    if not spawn.get("origin") or not doc.get("spawns"):
        problems.append(("no_spawn", "spawn", None))
    if spawn.get("origin"):
        place("spawn", spawn["origin"])
    for i, s in enumerate(doc.get("spawns") or []):
        place("spawns[%d]" % i, s["origin"])

    audit = doc.get("teleport_audit")
    if audit is None:
        problems.append(("no_audit", "teleport_audit", None))
    else:
        for b in audit.get("broken", []):
            problems.append(("audit_broken", "%s %s -> %s" % (b.get("problem"), b.get("targetname") or "#%s" % b.get("entity"),
                                                              b.get("target")), None))

    seen = set()
    for i, z in enumerate(m.zones):
        to = z.get("destination")
        if to is None:
            # A pit without one sends to the track's spawn; a door or stage start must say where.
            if z["kind"] in DESTINED and not (z["kind"] == "START" and "min" in z):
                problems.append(("no_destination", "zones[%d] %s" % (i, z["kind"]), None))
            continue
        key = (tuple(round(v) for v in to), z.get("track", 0))
        if key in seen:
            continue
        seen.add(key)
        place("zones[%d] %s" % (i, z["kind"]), to, z.get("track", 0), pits=True)

    for i, b in enumerate(doc.get("mechanics", {}).get("blocks", [])):
        if b.get("class") == "func_door" and b.get("destination") is None:
            problems.append(("no_destination", "blocks[%d] %s" % (i, b.get("class")), None))
        elif b.get("destination") is not None:
            key = (tuple(round(v) for v in b["destination"]), "block")
            if key not in seen:
                seen.add(key)
                place("blocks[%d] %s" % (i, b.get("class")), b["destination"])
    return problems, len(seen)


def map_ids(maps_dir):
    return sorted(d.name for d in maps_dir.iterdir() if (d / (d.name + ".json")).is_file())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("maps", nargs="*")
    ap.add_argument("--maps-dir", default=str(ROOT / "maps"))
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--known", default=str(ROOT / "tools" / "playable_known.json"))
    a = ap.parse_args()
    maps_dir = Path(a.maps_dir)
    ids = a.maps or map_ids(maps_dir)
    known = json.loads(Path(a.known).read_text()) if Path(a.known).is_file() else {}
    failed = held = 0
    for mid in ids:
        base = maps_dir / mid / mid
        try:
            doc = json.loads(base.with_suffix(".json").read_text())
            blob = base.with_suffix(".bin").read_bytes()
        except (OSError, ValueError) as e:
            print("FAIL %s: unreadable: %s" % (mid, e))
            failed += 1
            continue
        problems, places = check(Map(mid, doc, blob))
        kinds = {}
        for p in problems:
            kinds[p[0]] = kinds.get(p[0], 0) + 1
        want = known.get(mid, {}).get("fails")
        if not problems and want is None:
            print("ok   %s: %d destinations, %d spawns" % (mid, places, len(doc.get("spawns") or [])))
            continue
        if want is not None and want == kinds:
            held += 1
            print("known %s: %s (%s)" % (mid, ", ".join("%s %d" % kv for kv in sorted(kinds.items())),
                                        known[mid].get("reason", "")))
            continue
        failed += 1
        if want is not None:
            print("FAIL %s: playable_known.json expects %s, got %s: update or remove the entry"
                  % (mid, want, kinds or "no failures"))
            continue
        print("FAIL %s: %s" % (mid, ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
        for kind, what, at in problems if a.verbose else problems[:5]:
            print("       %s %s%s" % (kind, what, "" if at is None else " at (%.0f, %.0f, %.0f)" % tuple(at)))
    print("check_playable: %d maps, %d ok, %d known, %d failed" % (len(ids), len(ids) - failed - held, held, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
