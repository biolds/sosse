#!/bin/bash
PROJECT_NAME=biolds1/sosse
PROJECT_URL=https://gitlab.com/$PROJECT_NAME

cd "$(dirname $0)/.."
echo '# Changelog'
cat CHANGELOG.md | \
    sed -e "s#(${PROJECT_NAME}@\([0-9a-f]\+\))#(${PROJECT_URL}/-/commit/\1)#g" \
        -e "s#(${PROJECT_NAME}!\([0-9]\+\))#(${PROJECT_URL}/-/merge_requests/\1)#g" \
