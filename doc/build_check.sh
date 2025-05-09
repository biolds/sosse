#!/bin/bash

files=$(find build/ -name '*.html')

bad_files=0

for file in $files; do
  if ! grep -q '\<uma\.sosse\.io\>' "$file"; then
    echo "$file is missing Umami javascript snippet" >&2
    bad_files=1
  fi
done

exit "$bad_files"
