FROM biolds/sosse:pip-base
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN virtualenv /venv
RUN /venv/bin/pip install sosse uwsgi && /venv/bin/pip cache purge
RUN mkdir -p /etc/sosse/ /etc/sosse_src/ /var/log/sosse /var/log/uwsgi
RUN /venv/bin/sosse-admin default_conf | sed -e 's/^#db_pass.*/db_pass=sosse/' -e 's/^#\(chromium_options=.*\)$/\1 --no-sandbox --disable-dev-shm-usage/' > /etc/sosse_src/sosse.conf
ADD uwsgi.* /etc/sosse_src/
ADD sosse.conf /etc/nginx/sites-enabled/default
RUN chown -R root:www-data /etc/sosse /etc/sosse_src && chmod 750 /etc/sosse_src/ && chmod 640 /etc/sosse_src/*
RUN mkdir /var/www/.cache /var/www/.mozilla
RUN chown www-data:www-data /var/www/.cache /var/www/.mozilla

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER sosse WITH PASSWORD 'sosse';" && \
    createdb -O sosse sosse

USER root
RUN echo '#!/bin/bash -x \n \
/etc/init.d/postgresql start \n \
test -e /etc/sosse/sosse.conf || (cp -p /etc/sosse_src/* /etc/sosse/) \n \
touch /var/log/sosse/{debug.log,main.log,crawler.log,uwsgi.log,webserver.log} \n \
mkdir -p /run/sosse /var/log/sosse /var/lib/sosse/html/ \n \
chown -R www-data:www-data /run/sosse /var/log/sosse/ /var/lib/sosse \n \
/venv/bin/sosse-admin migrate \n \
/venv/bin/sosse-admin collectstatic --noinput \n \
/venv/bin/sosse-admin update_se \n \
/venv/bin/sosse-admin default_admin \n \
/venv/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini --logto /var/log/sosse/uwsgi.log & \n \
/etc/init.d/nginx start \n \
/venv/bin/sosse-admin crawl & \n \
tail -F /var/log/sosse/crawler.log' > /run.sh ; chmod +x /run.sh
CMD /run.sh
