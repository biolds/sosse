#!/bin/bash
cd "$(dirname $0)"/../
export LANG=C
test -d /tmp/testserver || ./tests/test_app.sh
sudo -E -u www-data ./sosse-admin test --settings=sosse.settings_tests -v3 "$@"
