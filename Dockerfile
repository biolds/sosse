FROM debian:bullseye

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y git python3-pip python3-dev build-essential postgresql libpq-dev libmagic1 nginx chromium chromium-driver uwsgi uwsgi-plugin-python3

RUN mkdir /root/sosse
WORKDIR /root/sosse
ADD requirements.txt .
ADD setup.py .
ADD sosse-admin .
RUN pip install -r requirements.txt && pip cache purge
RUN python3 setup.py install
ADD se.json .
ADD se/ se/
ADD sosse/ sosse/
RUN mkdir -p /etc/sosse /var/log/sosse /var/log/uwsgi
RUN sosse-admin default_conf > /etc/sosse/sosse.conf
RUN sed -e 's/^#db_pass.*/db_pass=sosse/' -e 's/^#\(browser_options=.*\)$/\1 --no-sandbox/' -i /etc/sosse/sosse.conf
ADD debian/uwsgi.* /etc/sosse/
RUN chown -R root:www-data /etc/sosse && chmod 750 /etc/sosse/ && chmod 640 /etc/sosse/*
ADD debian/sosse.conf /etc/nginx/sites-enabled/default

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER sosse WITH SUPERUSER PASSWORD 'sosse';" && \
    createdb -O sosse sosse

USER root
RUN echo '#!/bin/bash -x \n \
/etc/init.d/postgresql start \n \
mkdir -p /run/sosse \n \
touch /var/log/sosse/{debug.log,main.log,crawler.log,uwsgi.log} \n \
chown -R www-data:www-data /run/sosse /var/log/sosse/ \n \
sosse-admin migrate \n \
sosse-admin loaddata /root/sosse/se.json \n \
sosse-admin collectstatic --noinput \n \
sosse-admin default_admin \n \
/usr/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini & \n \
/etc/init.d/nginx start \n \
sosse-admin crawl & \n \
tail -F /var/log/sosse/crawler.log' > /run.sh ; chmod +x /run.sh
CMD /run.sh
