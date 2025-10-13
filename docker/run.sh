#!/bin/bash -x
until pg_isready --host "$SOSSE_DB_HOST"; do
  sleep 1
done

test -e /etc/sosse/sosse.conf || /venv/bin/sosse-admin default_conf | sed -e "s/^#db_pass.*/db_pass=sosse/" -e "s/^#\(chromium_options=.*\)$/\\1 --no-sandbox --disable-dev-shm-usage/" >/etc/sosse_src/sosse.conf
test -e /etc/sosse/sosse.conf || cp -p /etc/sosse_src/* /etc/sosse/
mkdir -p /run/sosse /var/log/sosse /var/lib/sosse/html/
touch /var/log/sosse/{debug.log,main.log,crawler.log,uwsgi.log,webserver.log,webhooks.log}

/venv/bin/sosse-admin collectstatic -v 0 --noinput --clear
chown -R www-data:www-data /run/sosse /var/log/sosse/ /var/lib/sosse

/venv/bin/sosse-admin migrate
/venv/bin/sosse-admin update_se
sudo -u www-data /venv/bin/sosse-admin update_mime
/venv/bin/sosse-admin default_admin
/venv/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini --logto /var/log/sosse/uwsgi.log &
/etc/init.d/nginx start
sudo --preserve-env -u www-data /venv/bin/sosse-admin crawl &
echo -e "\033[1;34m🌐 Starting web server...\033[0m \033[1;33mDefault credentials:\033[0m \033[1;36madmin\033[0m / \033[1;36madmin\033[0m"
tail -F /var/log/sosse/crawler.log
