#!/usr/bin/env bash
set -euo pipefail

# Simple file integrity checker (SHA-256).
# Idea: make a baseline of hashes once, then re-scan later and compare.
#
# Commands:
#   ./fic.sh init [listfile]     -> create baseline
#   ./fic.sh check [listfile]    -> compare with baseline
#   ./fic.sh add <path> [listfile]
#   ./fic.sh remove <path> [listfile]

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_DIR="$PROJECT_DIR/db"
LOG_DIR="$PROJECT_DIR/logs"
DEFAULT_LIST="$PROJECT_DIR/critical_files.txt"
BASELINE="$DB_DIR/baseline.sha256"
LAST_SCAN="$DB_DIR/last_scan.sha256"
LOG_FILE="$LOG_DIR/fic.log"

mkdir -p "$DB_DIR" "$LOG_DIR"

ts() { date +"%Y-%m-%d %H:%M:%S"; }

log() {
  echo "[$(ts)] $*" | tee -a "$LOG_FILE" >/dev/null
}

die() {
  log "ERROR: $*"
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

hash_one_file() {
  # Print one line like: "<hash>  <file>"
  # Prefer sha256sum, but on Windows Git Bash we can fall back to certutil.
  local f="$1"

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -- "$f"
    return 0
  fi

  if command -v certutil >/dev/null 2>&1; then
    local win
    if command -v cygpath >/dev/null 2>&1; then
      win="$(cygpath -w "$f")"
    else
      win="$f"
    fi

    local h
    h="$(certutil -hashfile "$win" SHA256 2>/dev/null | tr -d '\r' | awk 'NR==2{print $1}' | tr 'A-F' 'a-f')"
    [[ -n "$h" ]] || return 1
    printf '%s  %s\n' "$h" "$f"
    return 0
  fi

  return 1
}

sanitize_list() {
  # Read listfile and drop empty lines + comments.
  local listfile="$1"
  grep -v '^\s*$' "$listfile" | grep -v '^\s*#' || true
}

hash_files_from_list() {
  local listfile="$1"
  local tmpout="$2"

  : > "$tmpout"
  while IFS= read -r f; do
    # Support ~/ paths.
    if [[ "$f" == "~/"* ]]; then
      f="$HOME/${f#~/}"
    fi

    if [[ -f "$f" ]]; then
      # Hash the file. If hashing fails, mark it as ERROR.
      if ! hash_one_file "$f" >> "$tmpout"; then
        echo "ERROR  $f" >> "$tmpout"
      fi
    else
      # File not found.
      echo "MISSING  $f" >> "$tmpout"
    fi
  done < <(sanitize_list "$listfile")
}

ensure_default_list() {
  if [[ ! -f "$DEFAULT_LIST" ]]; then
    cat > "$DEFAULT_LIST" <<EOF
# Put one file per line. Lines starting with # are comments.
# This default list is project-local and should work on Windows/Linux.
# You can add any absolute paths you want.

# This script:
$PROJECT_DIR/fic.sh

# (Optional) Track this list itself:
$PROJECT_DIR/critical_files.txt
EOF
    log "Created default list: $DEFAULT_LIST"
    log "Edit it if needed, then run: ./fic.sh init"
  fi
}

cmd_init() {
  # First run convenience: create default list if user didn't pass one.
  if [[ -z "${1:-}" ]]; then
    ensure_default_list
  fi

  local listfile="${1:-$DEFAULT_LIST}"
  [[ -f "$listfile" ]] || die "List file not found: $listfile"

  # Need either sha256sum or Windows certutil.
  if ! command -v sha256sum >/dev/null 2>&1 && ! command -v certutil >/dev/null 2>&1; then
    die "Missing command: sha256sum (or Windows certutil)"
  fi

  local tmp="$DB_DIR/.baseline_tmp"
  hash_files_from_list "$listfile" "$tmp"

  # Save new baseline.
  mv "$tmp" "$BASELINE"
  cp "$BASELINE" "$LAST_SCAN"

  log "Baseline created: $BASELINE"
  log "List used: $listfile"
}

cmd_add() {
  local path="${1:-}"
  local listfile="${2:-$DEFAULT_LIST}"
  [[ -n "$path" ]] || die "Usage: ./fic.sh add <path> [listfile]"
  [[ -f "$listfile" ]] || die "List file not found: $listfile"

  if ! grep -Fxq "$path" "$listfile"; then
    echo "$path" >> "$listfile"
    log "Added to list: $path"
  else
    log "Already in list: $path"
  fi
}

cmd_remove() {
  local path="${1:-}"
  local listfile="${2:-$DEFAULT_LIST}"
  [[ -n "$path" ]] || die "Usage: ./fic.sh remove <path> [listfile]"
  [[ -f "$listfile" ]] || die "List file not found: $listfile"

  # Remove exact line.
  grep -Fxv "$path" "$listfile" > "$listfile.tmp" || true
  mv "$listfile.tmp" "$listfile"
  log "Removed from list: $path"
}

cmd_check() {
  local listfile="${1:-$DEFAULT_LIST}"
  [[ -f "$listfile" ]] || die "List file not found: $listfile"
  [[ -f "$BASELINE" ]] || die "Baseline not found. Run: ./fic.sh init"

  if ! command -v sha256sum >/dev/null 2>&1 && ! command -v certutil >/dev/null 2>&1; then
    die "Missing command: sha256sum (or Windows certutil)"
  fi

  local tmp="$DB_DIR/.scan_tmp"
  hash_files_from_list "$listfile" "$tmp"
  mv "$tmp" "$LAST_SCAN"

  # Compare current scan against baseline.
  log "Scan complete. Comparing with baseline..."

  # Make small lookup tables: "path<TAB>hash".
  local base_map="$DB_DIR/.base_map"
  local scan_map="$DB_DIR/.scan_map"

  # sha256sum uses either two spaces or " *" separator; handle both.
  awk '{hash=$1; $1=""; sub(/^[ *]+/,""); path=$0; print path "\t" hash}' "$BASELINE" | sort > "$base_map"
  awk '{hash=$1; $1=""; sub(/^[ *]+/,""); path=$0; print path "\t" hash}' "$LAST_SCAN" | sort > "$scan_map"

  # Walk baseline list and check what happened.
  local changes=0

  while IFS=$'\t' read -r path bhash; do
    shash="$(awk -v p="$path" '$1==p {print $2}' "$scan_map" | head -n1 || true)"

    if [[ -z "${shash:-}" ]]; then
      log "MISSING (not scanned): $path"
      changes=$((changes+1))
    elif [[ "$shash" == "MISSING" ]]; then
      log "MISSING: $path"
      changes=$((changes+1))
    elif [[ "$bhash" != "$shash" ]]; then
      log "MODIFIED: $path"
      changes=$((changes+1))
    fi
  done < "$base_map"

  # Extra entries in scan (usually because list changed).
  while IFS=$'\t' read -r path shash; do
    b="$(awk -v p="$path" '$1==p {print $2}' "$base_map" | head -n1 || true)"
    if [[ -z "${b:-}" ]]; then
      log "NEW (in list now, not in baseline): $path"
      changes=$((changes+1))
    fi
  done < "$scan_map"

  if [[ "$changes" -eq 0 ]]; then
    log "OK: No changes detected."
  else
    log "ALERT: Detected $changes change(s). See log: $LOG_FILE"
  fi
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    init)   cmd_init "$@" ;;
    check)  cmd_check "$@" ;;
    add)    cmd_add "$@" ;;
    remove) cmd_remove "$@" ;;
    ""|help|-h|--help)
      cat <<EOF
File Integrity Checker (sha256sum)

Usage:
  ./fic.sh init [listfile]      Create baseline hashes
  ./fic.sh check [listfile]     Compare current hashes vs baseline
  ./fic.sh add <path> [listfile]    Add file path to list
  ./fic.sh remove <path> [listfile] Remove file path from list

Files:
  List file default: $DEFAULT_LIST
  Baseline stored:   $BASELINE
  Log file:          $LOG_FILE
EOF
      ;;
    *)
      die "Unknown command: $cmd (use ./fic.sh help)"
      ;;
  esac
}

main "$@"
