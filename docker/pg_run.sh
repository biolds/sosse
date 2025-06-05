#!/bin/bash -x
test -e /var/lib/postgresql/15 || tar -x -p -C / -f /tmp/postgres_sosse.tar.gz

/etc/init.d/postgresql start

export SOSSE_DB_HOST=localhost

exec bash /run.sh
