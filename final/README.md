# File Integrity Checker (FIC)

This is a small script for my final project.
It saves SHA-256 hashes for a list of important files (baseline), and later checks if anything changed.

Tested in Git Bash on Windows, should also work on Linux/macOS.

## Quick start (Git Bash)

```bash
cd /f/infosec/final
bash ./fic.sh init
bash ./fic.sh check
```

It creates:
- `critical_files.txt` — list of files to watch
- `db/baseline.sha256` — baseline hashes
- `db/last_scan.sha256` — last scan hashes
- `logs/fic.log` — logs

## Commands

```bash
./fic.sh init [listfile]         # create baseline
./fic.sh check [listfile]        # compare current state vs baseline
./fic.sh add <path> [listfile]   # add file path to list
./fic.sh remove <path> [listfile]# remove file path from list
```

## Notes

- On first `init`, it auto-creates `critical_files.txt`.
- Hashing uses `sha256sum` if it exists. On Windows it can fall back to `certutil`.

## Example workflow

```bash
# Track another file
./fic.sh add /f/infosec/lab07/job.py

# Re-create baseline to include it
./fic.sh init

# Modify the file, then detect change
./fic.sh check

# See details
tail -n 50 logs/fic.log
```
