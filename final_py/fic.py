#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple


PROJECT_DIR = Path(__file__).resolve().parent
DB_DIR = PROJECT_DIR / "db"
LOG_DIR = PROJECT_DIR / "logs"
DEFAULT_LIST = PROJECT_DIR / "critical_files.txt"
BASELINE = DB_DIR / "baseline.sha256"
LAST_SCAN = DB_DIR / "last_scan.sha256"
LOG_FILE = LOG_DIR / "fic.log"


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{ts()}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def die(message: str, code: int = 1) -> None:
    log(f"ERROR: {message}")
    raise SystemExit(code)


def ensure_default_list() -> None:
    if DEFAULT_LIST.exists():
        return

    DEFAULT_LIST.write_text(
        "\n".join(
            [
                "# One file per line.",
                "# Lines starting with # are comments (ignored).",
                "# This default list is project-local, so it works on Windows/Linux.",
                "# You can add absolute paths (or relative ones if you prefer).",
                "",
                "# This script file:",
                str(PROJECT_DIR / "fic.py"),
                "",
                "# Optional: track this list file too:",
                str(DEFAULT_LIST),
                "",
            ]
        ),
        encoding="utf-8",
    )

    log(f"Created default list: {DEFAULT_LIST}")
    log("Edit it if needed, then run: python fic.py init")


def iter_list_paths(listfile: Path) -> Iterable[str]:
    """Read paths from the list file (skip empty lines and comments)."""
    try:
        text = listfile.read_text(encoding="utf-8")
    except FileNotFoundError:
        die(f"List file not found: {listfile}")

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Support ~/ at the start
        if line.startswith("~/"):
            line = str(Path.home() / line[2:])
        yield line


def sha256_of_file(path: Path) -> str:
    """Return SHA-256 hex digest for the given file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_files_from_list(listfile: Path, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for p in iter_list_paths(listfile):
        path = Path(p)
        if path.is_file():
            try:
                digest = sha256_of_file(path)
                # Same format as sha256sum: "<hash>  <path>"
                lines.append(f"{digest}  {p}")
            except OSError:
                lines.append(f"ERROR  {p}")
        else:
            lines.append(f"MISSING  {p}")

    out_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def parse_hash_file(hash_file: Path) -> Dict[str, str]:
    """Parse a baseline/scan file into a dict: path -> hash/marker."""
    if not hash_file.exists():
        die(f"File not found: {hash_file}")

    mapping: Dict[str, str] = {}
    for raw in hash_file.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\r\n")
        if not line:
            continue
        # Split once: first token is hash/marker, the rest is the path
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        h, path = parts[0], parts[1].lstrip(" *")
        mapping[path] = h
    return mapping


def cmd_init(listfile: Path) -> None:
    if listfile == DEFAULT_LIST and not listfile.exists():
        ensure_default_list()

    if not listfile.exists():
        die(f"List file not found: {listfile}")

    tmp = DB_DIR / ".baseline_tmp"
    hash_files_from_list(listfile, tmp)

    DB_DIR.mkdir(parents=True, exist_ok=True)
    tmp.replace(BASELINE)
    # Keep last_scan equal to baseline (simple copy)
    LAST_SCAN.write_text(BASELINE.read_text(encoding="utf-8"), encoding="utf-8")

    log(f"Baseline created: {BASELINE}")
    log(f"List used: {listfile}")


def cmd_add(path: str, listfile: Path) -> None:
    if listfile == DEFAULT_LIST and not listfile.exists():
        ensure_default_list()

    if not listfile.exists():
        die(f"List file not found: {listfile}")

    existing = listfile.read_text(encoding="utf-8").splitlines()
    if any(line.strip() == path for line in existing):
        log(f"Already in list: {path}")
        return

    with listfile.open("a", encoding="utf-8") as f:
        if existing and existing[-1] != "":
            f.write("\n")
        f.write(path + "\n")

    log(f"Added to list: {path}")


def cmd_remove(path: str, listfile: Path) -> None:
    if not listfile.exists():
        die(f"List file not found: {listfile}")

    lines = listfile.read_text(encoding="utf-8").splitlines()
    new_lines = [ln for ln in lines if ln.strip() != path]
    listfile.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    log(f"Removed from list: {path}")


def cmd_check(listfile: Path) -> None:
    if not listfile.exists():
        die(f"List file not found: {listfile}")
    if not BASELINE.exists():
        die("Baseline not found. Run: python fic.py init")

    tmp = DB_DIR / ".scan_tmp"
    hash_files_from_list(listfile, tmp)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    tmp.replace(LAST_SCAN)

    log("Scan complete. Comparing with baseline...")

    base = parse_hash_file(BASELINE)
    scan = parse_hash_file(LAST_SCAN)

    changes = 0

    # Compare entries from baseline
    for path, bhash in sorted(base.items()):
        shash = scan.get(path)
        if shash is None:
            log(f"MISSING (not scanned): {path}")
            changes += 1
        elif shash == "MISSING":
            log(f"MISSING: {path}")
            changes += 1
        elif shash == "ERROR":
            log(f"ERROR (could not hash): {path}")
            changes += 1
        elif bhash != shash:
            log(f"MODIFIED: {path}")
            changes += 1

    # Anything that shows up now but wasn't in baseline
    for path in sorted(scan.keys() - base.keys()):
        log(f"NEW (in list now, not in baseline): {path}")
        changes += 1

    if changes == 0:
        log("OK: No changes detected.")
    else:
        log(f"ALERT: Detected {changes} change(s). See log: {LOG_FILE}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fic.py", description="File Integrity Checker (Python, SHA-256)")
    sub = p.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="Create baseline hashes")
    p_init.add_argument("listfile", nargs="?", default=str(DEFAULT_LIST))

    p_check = sub.add_parser("check", help="Compare current hashes vs baseline")
    p_check.add_argument("listfile", nargs="?", default=str(DEFAULT_LIST))

    p_add = sub.add_parser("add", help="Add file path to list")
    p_add.add_argument("path")
    p_add.add_argument("listfile", nargs="?", default=str(DEFAULT_LIST))

    p_rm = sub.add_parser("remove", help="Remove file path from list")
    p_rm.add_argument("path")
    p_rm.add_argument("listfile", nargs="?", default=str(DEFAULT_LIST))

    return p


def main(argv: list[str] | None = None) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    parser = build_parser()
    args = parser.parse_args(argv)

    cmd = args.cmd
    if cmd is None:
        parser.print_help()
        return

    if cmd == "init":
        cmd_init(Path(args.listfile))
        return
    if cmd == "check":
        cmd_check(Path(args.listfile))
        return
    if cmd == "add":
        cmd_add(args.path, Path(args.listfile))
        return
    if cmd == "remove":
        cmd_remove(args.path, Path(args.listfile))
        return

    die(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
