#!/bin/bash
cd "$(dirname $0)"/../
sudo -u www-data ./sosse-admin test -v3 "$@"
