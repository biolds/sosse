FROM debian:bullseye

ARG OSSE_DOCKER_VER

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y git python3-pip python3-dev build-essential postgresql libpq-dev libmagic1 nginx chromium chromium-driver uwsgi uwsgi-plugin-python3
#ADD . /tmp/osse.git
#RUN if [ "$OSSE_DOCKER_VER" = local ]; then mv /tmp/osse.git /root ; fi
# to remove
RUN pwd
RUN if [ "$OSSE_DOCKER_VER" != local ]; then git clone https://github.com/biolds/osse.git /root/osse.git ; fi

WORKDIR /root/osse.git
RUN if [ "$OSSE_DOCKER_VER" != main ] && [ "$OSSE_DOCKER_VER" != local ]; then git checkout -b "$OSSE_DOCKER_VER" "$OSSE_DOCKER_VER" ; fi
RUN pip install -r requirements.txt
RUN python3 setup.py install
RUN mkdir -p /etc/osse /var/log/osse /var/log/uwsgi
RUN osse-admin default_conf > /etc/osse/osse.conf
RUN sed -e 's/^#db_pass.*/db_pass=osse/' -i /etc/osse/osse.conf
ADD debian/uwsgi.* /etc/osse/
RUN chown root:www-data /etc/osse/* && chmod 640 /etc/osse/*
ADD debian/osse.conf /etc/nginx/sites-enabled/default

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER osse WITH SUPERUSER PASSWORD 'osse';" && \
    createdb -O osse osse

USER root
RUN echo '#!/bin/bash -x \n \
/etc/init.d/postgresql start \n \
mkdir -p /run/osse \n \
touch /var/log/osse/debug.log /var/log/osse/main.log /var/log/osse/crawler.log \n \
chown www-data:www-data /run/osse /var/log/osse/* \n \
osse-admin migrate \n \
osse-admin loaddata /root/osse.git/se.json \n \
osse-admin collectstatic -noinput \n \
/usr/bin/uwsgi --daemonize2 --uid www-data --gid www-data --ini /etc/osse/uwsgi.ini \n \
/etc/init.d/nginx start \n \
osse-admin crawl' > /run.sh ; chmod +x /run.sh
CMD /run.sh
