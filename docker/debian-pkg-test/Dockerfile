FROM debian:bullseye

RUN apt update
RUN apt upgrade -y
RUN apt install -y curl gpg
RUN curl http://piggledy.org/repo/apt/debian/public.gpg.key | gpg --dearmor > /usr/share/keyrings/piggledy.gpg
RUN echo 'deb [signed-by=/usr/share/keyrings/piggledy.gpg] http://piggledy.org/repo/apt/debian bullseye main' > /etc/apt/sources.list.d/piggledy.list
RUN echo 'deb http://deb.debian.org/debian bullseye-backports main' > /etc/apt/sources.list.d/bullseye-backports.list
RUN apt update
RUN apt install -y python3-django/bullseye-backports sosse && \
        apt-get clean autoclean && \
        apt-get autoremove --yes && \
        rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
ADD sosse_0.1.0-1_amd64.deb /root
RUN dpkg -i /root/sosse_0.1.0-1_amd64.deb

RUN sosse-admin default_conf > /etc/sosse/sosse.conf
RUN chown -R root:www-data /etc/sosse && chmod 750 /etc/sosse/ && chmod 640 /etc/sosse/*
RUN sed -e 's/^#db_pass.*/db_pass=sosse/' -e 's/^#\(browser_options=.*\)$/\1 --no-sandbox/' -i /etc/sosse/sosse.conf
RUN rm /etc/nginx/sites-enabled/default
RUN ln -s /etc/nginx/sites-available/sosse.conf /etc/nginx/sites-enabled/

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER sosse WITH SUPERUSER PASSWORD 'sosse';" && \
    createdb -O sosse sosse

USER root
RUN /etc/init.d/postgresql start && \
    sosse-admin migrate && \
    sosse-admin default_admin

RUN echo '#!/bin/bash -x \n \
/etc/init.d/postgresql start \n \
mkdir -p /run/sosse \n \
chown -R www-data:www-data /run/sosse \n \
sosse-admin migrate \n \
sosse-admin loaddata /usr/share/sosse/se.json \n \
sosse-admin collectstatic --noinput \n \
/usr/bin/uwsgi --uid www-data --gid www-data --ini /etc/sosse/uwsgi.ini & \n \
/etc/init.d/nginx start \n \
sosse-admin crawl & \n \
tail -F /var/log/sosse/crawler.log' > /run.sh ; chmod +x /run.sh
CMD /run.sh
