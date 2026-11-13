#!/usr/bin/env python3
"""check_names -- no doc or config names the maps collection by its old id.

The collection is gamemann/airdrift-maps; gamemann/g2gfast-maps is its alias until the
removal date in CLAUDE.md. A tracked file may name the old name only where it documents
that: within 80 characters of each occurrence it names airdrift-maps, or says alias /
former / renamed / old name / checked out as. A sibling-folder path (../g2gfast-maps) is
allowed too: bootstrap keeps the old folder name as a link.

    tools/check_names.py                        this repository (what CI runs)
    tools/check_names.py --family ..            also game-g2gfast and dot-server-deploy beside it
    tools/check_names.py ../wt/game-g2gfast-x   also these checkouts (worktrees)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

OLD = "g2gfast-maps"
ALLOWED = re.compile(r"airdrift-maps|alias|former|renamed|old name|checked out as", re.IGNORECASE)
WINDOW = 80
FAMILY = ("game-g2gfast", "dot-server-deploy")
ROOT = Path(__file__).resolve().parent.parent


def offenders(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "grep", "-n", "-I", "-i", "-F", OLD, "--", ".", ":!tools/check_names.py"],
        capture_output=True, text=True)
    if out.returncode not in (0, 1):
        sys.exit(f"check_names: git grep failed in {repo}: {out.stderr.strip()}")
    return [f"{repo.name}/{line}" for line in out.stdout.splitlines()
            if not allowed(line.split(":", 2)[2])]


def allowed(text: str) -> bool:
    """Every occurrence on the line is a folder path or has an alias note beside it."""
    for m in re.finditer(re.escape(OLD), text, re.IGNORECASE):
        if text[max(0, m.start() - 3):m.start()] == "../":
            continue
        if not ALLOWED.search(text[max(0, m.start() - WINDOW):m.end() + WINDOW]):
            return False
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--family", type=Path, help="directory holding the family checkouts")
    p.add_argument("repos", nargs="*", type=Path, help="more checkouts to check")
    args = p.parse_args()
    repos = [ROOT, *args.repos]
    if args.family:
        for name in FAMILY:
            if (args.family / name / ".git").exists():
                repos.append(args.family / name)
            else:
                print(f"check_names: SKIP {name}: not checked out in {args.family}")
    bad = [line for repo in repos for line in offenders(repo)]
    for line in bad:
        print(f"OLD NAME  {line}")
    print(f"check_names: {len(repos)} repositories, {len(bad)} lines name {OLD} outside the alias")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
