#!/bin/bash -x
test -e /var/lib/postgresql/15 || tar -x -p -C / -f /tmp/postgres_sosse.tar.gz
chown -R 900:900 /var/lib/postgresql /etc/postgresql /var/run/postgresql
chown root:900 /var/log/postgresql
chown 900:adm /var/log/postgresql/*

/etc/init.d/postgresql start

export SOSSE_DB_HOST=localhost

exec bash /run.sh
