#!/bin/bash -x
test -e /var/lib/postgresql/15 || tar -x -p -C / -f /tmp/postgres_sosse.tar.gz

/etc/init.d/postgresql start
until pg_isready; do
  sleep 1
done

test -e /etc/sosse/sosse.conf || /venv/bin/sosse-admin default_conf | sed -e "s/^#db_pass.*/db_pass=sosse/" -e "s/^#\(chromium_options=.*\)$/\\1 --no-sandbox --disable-dev-shm-usage/" >/etc/sosse_src/sosse.conf
test -e /etc/sosse/sosse.conf || cp -p /etc/sosse_src/* /etc/sosse/
mkdir -p /run/sosse /var/log/sosse /var/lib/sosse/html/
touch /var/log/sosse/{debug.log,main.log,crawler.log,uwsgi.log,webserver.log}
chown -R www-data:www-data /run/sosse /var/log/sosse/ /var/lib/sosse

/venv/bin/sosse-admin migrate
/venv/bin/sosse-admin collectstatic --noinput
/venv/bin/sosse-admin update_se
/venv/bin/sosse-admin default_admin
/venv/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini --logto /var/log/sosse/uwsgi.log &
/etc/init.d/nginx start
/venv/bin/sosse-admin crawl &
tail -F /var/log/sosse/crawler.log
