#!/usr/bin/env python3
"""Bootstrap without resetting existing checkouts; record explicit tested revisions."""

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("engine", "desktop")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def read_lock(root):
    entries = json.loads((root / "repos.lock.json").read_text())
    if set(entries) != set(NAMES):
        raise ValueError("lock must contain engine and desktop")
    for name, entry in entries.items():
        if entry["url"] != f"https://github.com/knotra-dev/{name}.git":
            raise ValueError("unexpected repository URL: " + name)
        if not re.fullmatch(r"[0-9a-f]{40}", entry["commit"]):
            raise ValueError("lock requires a full commit SHA: " + name)
    return entries


def bootstrap(root, entries):
    (root / "repos").mkdir(exist_ok=True)
    for name, entry in entries.items():
        repo = root / "repos" / name
        if repo.exists():
            print(f"{name}: preserving existing checkout", flush=True)
            continue
        subprocess.run(["git", "clone", entry["url"], str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "checkout", "--detach", entry["commit"]],
            check=True,
        )


def current(root, clean=False):
    entries = {}
    for name in NAMES:
        repo = root / "repos" / name
        if clean and git(repo, "status", "--porcelain"):
            raise ValueError(f"commit or stash {name} changes before updating the lock")
        entries[name] = {
            "url": f"https://github.com/knotra-dev/{name}.git",
            "commit": git(repo, "rev-parse", "HEAD"),
        }
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("bootstrap", "status", "check", "lock"))
    args = parser.parse_args()
    try:
        if args.command == "bootstrap":
            bootstrap(ROOT, read_lock(ROOT))
            return
        entries = current(ROOT, clean=args.command == "lock")
        if args.command in ("check", "lock"):
            manifest = ROOT / "repos/desktop/vendor/engine/manifest.json"
            if (
                json.loads(manifest.read_text())["commit"]
                != entries["engine"]["commit"]
            ):
                raise ValueError(
                    "sync desktop's snapshot to the current engine commit first"
                )
        if args.command == "lock":
            (ROOT / "repos.lock.json").write_text(json.dumps(entries, indent=2) + "\n")
        else:
            locked = read_lock(ROOT)
            for name, entry in entries.items():
                repo = ROOT / "repos" / name
                state = "dirty" if git(repo, "status", "--porcelain") else "clean"
                matches = entry == locked[name]
                print(
                    f"{name}: {entry['commit']} {state}, lock {'matches' if matches else 'differs'}"
                )
            if args.command == "check" and entries != locked:
                raise ValueError("checkout revisions differ from repos.lock.json")
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
