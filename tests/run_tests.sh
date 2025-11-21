#!/bin/bash
cd "$(dirname $0)"/../
export LANG=C
sudo -E -u www-data ./sosse-admin test -v3 "$@"
