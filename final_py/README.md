# File Integrity Checker (Python version)

This is the same idea as the Bash `final/fic.sh`, just written in Python.

- `init` makes a baseline of SHA-256 hashes
- `check` re-calculates hashes and compares to the baseline
- `add/remove` edits the list of watched files

## Run (Git Bash)

```bash
cd /f/infosec/final_py
python fic.py init
python fic.py check
```

## Commands

```bash
python fic.py init [listfile]
python fic.py check [listfile]
python fic.py add <path> [listfile]
python fic.py remove <path> [listfile]
```

## Files it creates

- `critical_files.txt` — list of files to watch
- `db/baseline.sha256` — baseline hashes
- `db/last_scan.sha256` — last scan hashes
- `logs/fic.log` — logs

## Demo (quick)

```bash
# add a file
python fic.py add /f/infosec/final_py/README.md

# rebuild baseline
python fic.py init

# change something
echo "demo" >> /f/infosec/final_py/README.md

# detect change
python fic.py check
```
