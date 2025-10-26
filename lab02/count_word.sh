#!/usr/bin/env bash

if [ $# -ne 2 ]; then
  echo "Usage: $0 <file> <word>"
  exit 1
fi

file="$1"
word="$2"

if [ ! -f "$file" ]; then
  echo "File not found: $file"
  exit 1
fi

count=$(grep -o -w "$word" "$file" | wc -l)
echo "Occurrences of '$word' in '$file': $count"
