#!/bin/bash -x
test -e /var/lib/postgresql/15 || tar -x -p -C / -f /tmp/postgres_sosse.tar.gz

/etc/init.d/postgresql start
until pg_isready; do
  sleep 1
done

exec bash /run.sh
