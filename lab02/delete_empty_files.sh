#!/usr/bin/env bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi

dir="$1"
if [ ! -d "$dir" ]; then
  echo "Directory not found: $dir"
  exit 1
fi

# -print will show the files before deletion; -delete removes them.
find "$dir" -type f -empty -print -delete
