#!/usr/bin/env python3
"""g2gmaps -- the maps game-g2gfast plays, as a repository, a manifest and a CDN.

    tools/g2gmaps manifest [--game ../game-g2gfast]
        Rewrite maps.json from maps/ and the credits in the game's maps/zones/.

    tools/g2gmaps link [--game ../game-g2gfast]
        Make the game's maps/imported a link to this repository's maps/, so the game
        loads, imports and publishes the maps from here.

    tools/g2gmaps publish --key PEM [--game ../game-g2gfast] [--out dist] [--upload] [ID...]
        Sign each map as its own pack, `<owner>/<id>`, with the game's publisher, and
        with --upload put dist/ on the content origin (games bucket, GAMES_S3_* in the
        environment).

    tools/g2gmaps fetch [--origin URL] [--out DIR] [--pub PEM] [ID...]
        Mirror every published map pack in maps.json from the CDN into DIR, verbatim:
        manifest.json and objects/, each object checked against the hash the manifest
        names, the manifest's signature checked against --pub when given. DIR is then a
        content origin of its own -- a LAN mirror, an offline box, a server that should
        not wait on the CDN the first time somebody votes for a map.

Why each map is its own pack rather than one pack for all of them: a player joining a
server downloads the map that is running, not 577 MB of maps they may never see, and
one map can be withdrawn without republishing the others.

Standard library only. `publish` needs Godot (through the game's own tool) and
`--upload` needs curl and openssl (through dot-server-deploy's uploader).
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps"
MANIFEST = ROOT / "maps.json"
DEFAULT_GAME = ROOT.parent / "game-g2gfast"
DEFAULT_ORIGIN = "https://dotgames.org/content"
DEFAULT_OWNER = "gamemann"


def die(message: str, code: int = 1) -> None:
    print(f"g2gmaps: {message}", file=sys.stderr)
    sys.exit(code)


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        die("no maps.json; run: tools/g2gmaps manifest")
    return json.loads(MANIFEST.read_text())


def map_ids() -> list[str]:
    return sorted(p.name for p in MAPS.iterdir() if p.is_dir() and (p / f"{p.name}.json").is_file())


def dir_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


# --- manifest ----------------------------------------------------------------


def cmd_manifest(args: argparse.Namespace) -> None:
    """Every map in maps/, with the credit the game's zones file records for it.

    The credit lives in the GAME's maps/zones/<id>.json because the importer writes it
    there and the game shows it on screen at a map change; this file copies it so the
    repository that ships a map also says whose it is, next to it.
    """
    zones = Path(args.game) / "maps" / "zones"
    old = json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {}
    maps = []
    uncredited = []

    for mid in map_ids():
        zone = zones / f"{mid}.json"
        credit = {}
        if zone.is_file():
            zdoc = json.loads(zone.read_text())
            if zdoc.get("kind") == "arena":
                # Combat surf lives in arena-surf-dm-maps; refused rather than skipped so
                # a stray copy is noticed and deleted instead of quietly left unpublished.
                die(f"{mid} is kind \"arena\": combat surf maps belong in ../arena-surf-dm-maps, not here", 2)
            credit = zdoc.get("attribution") or {}
        if not credit.get("author"):
            uncredited.append(mid)
        maps.append({
            "id": mid,
            "author": credit.get("author", ""),
            # The first thing in the source note is the page; the rest is how it was
            # confirmed, which the zones file keeps in full.
            "source": str(credit.get("source", "")).split(" ", 1)[0],
            "bytes": dir_bytes(MAPS / mid),
        })

    doc = {
        "owner": old.get("owner", DEFAULT_OWNER),
        "origin": old.get("origin", DEFAULT_ORIGIN),
        "maps": maps,
    }
    MANIFEST.write_text(json.dumps(doc, indent=2) + "\n")
    total = sum(m["bytes"] for m in maps)
    print(f"maps.json: {len(maps)} maps, {total / 1048576:.0f} MB")
    if uncredited:
        # Refused rather than written quietly: every map here is somebody's work.
        die(f"no author recorded for: {' '.join(uncredited)} (maps/zones/<id>.json)", 2)


# --- link --------------------------------------------------------------------


def same_tree(a: Path, b: Path) -> bool:
    out = subprocess.run(["diff", "-rq", str(a), str(b)], capture_output=True)
    return out.returncode == 0


def cmd_link(args: argparse.Namespace) -> None:
    """The game's maps/imported becomes a relative link to this repository's maps/.

    Relative, so the two checkouts can move together; refused over a real directory that
    differs from maps/, because that directory is the only copy of whatever differs.
    """
    target = Path(args.game) / "maps" / "imported"
    rel = os.path.relpath(MAPS, target.parent)

    if target.is_symlink():
        if target.resolve() == MAPS.resolve():
            print(f"{target} already links here")
            return
        target.unlink()
    elif target.exists():
        if not same_tree(target, MAPS):
            die(f"{target} is a real directory that differs from maps/; "
                "copy what you want to keep into maps/ first", 2)
        shutil.rmtree(target)

    target.symlink_to(rel)
    print(f"{target} -> {rel}")


# --- publish -----------------------------------------------------------------


def cmd_publish(args: argparse.Namespace) -> None:
    doc = load_manifest()
    game = Path(args.game)
    tool = game / "tools" / "publish_maps.sh"
    if not tool.is_file():
        die(f"no {tool}; publish runs through the game's own publisher")

    imported = game / "maps" / "imported"
    if not (imported.is_symlink() and imported.resolve() == MAPS.resolve()):
        die(f"{imported} is not linked to this repository; run: tools/g2gmaps link", 2)

    ids = args.ids or [m["id"] for m in doc["maps"]]
    out = Path(args.out).resolve()
    cmd = [str(tool), "--owner", doc["owner"], "--key", str(Path(args.key).resolve()),
           "--out", str(out), *ids]
    print("+", " ".join(cmd))
    if subprocess.run(cmd, cwd=game).returncode != 0:
        die("the game's publisher failed; see above", 3)

    if not args.upload:
        print(f"\npublished into {out}; --upload puts it on the content origin")
        return

    uploader = ROOT.parent / "dot-server-deploy" / "deploy" / "publish-web-s3.sh"
    env = dict(os.environ)
    for need in ("GAMES_S3_BUCKET", "GAMES_S3_REGION", "GAMES_S3_ACCESS_KEY", "GAMES_S3_ACCESS_SECRET"):
        if not env.get(need):
            die(f"--upload needs {need} in the environment", 2)
    env["S3_ACCESS_KEY"] = env["GAMES_S3_ACCESS_KEY"]
    env["S3_ACCESS_SECRET"] = env["GAMES_S3_ACCESS_SECRET"]
    env["TMC_S3_REGION"] = env["GAMES_S3_REGION"]
    # The bucket key carries `game/` and the URL does not: the CDN's origin path adds it.
    cmd = [str(uploader), "--content", "--bucket", env["GAMES_S3_BUCKET"],
           "--region", env["GAMES_S3_REGION"], "--prefix", "game/content/", "--source", str(out)]
    print("+", " ".join(cmd))
    if subprocess.run(cmd, env=env).returncode != 0:
        die("the upload failed; see above", 3)


# --- fetch -------------------------------------------------------------------


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "g2gmaps"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def b64(text: str) -> bytes:
    return base64.b64decode(text + "=" * (-len(text) % 4))


def verify_signature(envelope: dict, pub: str) -> bool:
    """RS256 over the DECODED payload bytes, which is what dot-cloud signs."""
    with tempfile.TemporaryDirectory() as tmp:
        payload = Path(tmp) / "payload"
        sig = Path(tmp) / "sig"
        payload.write_bytes(b64(envelope["payload"]))
        sig.write_bytes(b64(envelope["signature"]))
        out = subprocess.run(["openssl", "dgst", "-sha256", "-verify", pub,
                              "-signature", str(sig), str(payload)], capture_output=True)
        return out.returncode == 0


def fetch_one(origin: str, owner: str, mid: str, out: Path, pub: str | None) -> tuple[str, int, int]:
    base = f"{origin.rstrip('/')}/{owner}/{mid}"
    raw = get(f"{base}/manifest.json")
    envelope = json.loads(raw)

    if pub and not verify_signature(envelope, pub):
        raise RuntimeError(f"{owner}/{mid}: the manifest is not signed by {pub}")

    files = json.loads(b64(envelope["payload"]))["files"]
    dest = out / owner / mid
    fetched = 0

    for f in files:
        digest = f["sha256"]
        obj = dest / "objects" / digest[:2] / digest
        if obj.is_file() and hashlib.sha256(obj.read_bytes()).hexdigest() == digest:
            continue
        body = get(f"{base}/objects/{digest[:2]}/{digest}")
        if hashlib.sha256(body).hexdigest() != digest:
            raise RuntimeError(f"{owner}/{mid}: {f['path']} does not match its hash")
        obj.parent.mkdir(parents=True, exist_ok=True)
        obj.write_bytes(body)
        fetched += 1

    # Written last, so a mirror interrupted mid-download never has a manifest naming
    # objects it does not hold.
    (dest / "manifest.json").write_bytes(raw)
    return mid, len(files), fetched


def cmd_fetch(args: argparse.Namespace) -> None:
    doc = load_manifest()
    origin = args.origin or doc["origin"]
    owner = doc["owner"]
    ids = args.ids or [m["id"] for m in doc["maps"]]
    out = Path(args.out)
    failed = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(fetch_one, origin, owner, mid, out, args.pub): mid for mid in ids}
        for job in concurrent.futures.as_completed(jobs):
            mid = jobs[job]
            try:
                _, total, fetched = job.result()
                print(f"  {owner}/{mid}: {total} files, {fetched} downloaded")
            except Exception as e:  # noqa: BLE001 -- reported per map, the rest carry on
                failed.append(mid)
                print(f"  {owner}/{mid}: FAILED {e}", file=sys.stderr)

    if failed:
        die(f"{len(failed)} of {len(ids)} failed: {' '.join(sorted(failed))}", 3)
    print(f"{len(ids)} maps mirrored into {out}; point content_urls at it to serve them")


def main() -> None:
    p = argparse.ArgumentParser(prog="g2gmaps", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("manifest")
    m.add_argument("--game", default=str(DEFAULT_GAME))

    l = sub.add_parser("link")
    l.add_argument("--game", default=str(DEFAULT_GAME))

    pb = sub.add_parser("publish")
    pb.add_argument("--key", required=True)
    pb.add_argument("--game", default=str(DEFAULT_GAME))
    pb.add_argument("--out", default=str(ROOT / "dist"))
    pb.add_argument("--upload", action="store_true")
    pb.add_argument("ids", nargs="*")

    f = sub.add_parser("fetch")
    f.add_argument("--origin")
    f.add_argument("--out", default=str(ROOT / "mirror"))
    f.add_argument("--pub")
    f.add_argument("ids", nargs="*")

    args = p.parse_args()
    {"manifest": cmd_manifest, "link": cmd_link, "publish": cmd_publish, "fetch": cmd_fetch}[args.cmd](args)


if __name__ == "__main__":
    main()
