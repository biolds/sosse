#!/bin/bash
cd "$(dirname $0)"/../
sudo -E -u www-data ./sosse-admin test -v3 "$@"
