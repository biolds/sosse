FROM biolds/sosse:bookworm-debian-base
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y dpkg-dev curl gnupg jq sudo && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
COPY sosse_1.13.3-1_amd64.deb /var/local-repo/
RUN cd /var/local-repo && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz
RUN echo 'deb [trusted=yes] file:///var/local-repo ./' > /etc/apt/sources.list.d/local.list
RUN apt update
RUN apt-get install -y sosse && \
        apt-get clean autoclean && \
        apt-get autoremove --yes && \
        rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
# Install plugin dependencies
RUN jq -r '.[].dependencies[]?' /usr/lib/python3.11/dist-packages/sosse/mime_plugins.json | sort -u | xargs apt install -y && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man

# Comment out ImageMagick PDF policy restriction
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>$/<!--<policy domain="coder" rights="none" pattern="PDF" \/>-->/' /etc/ImageMagick-6/policy.xml

RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz | tar -C /usr/local/bin -x -v -z -f -

RUN sosse-admin default_conf > /etc/sosse/sosse.conf
RUN chown -R root:www-data /etc/sosse && chmod 750 /etc/sosse/ && chmod 640 /etc/sosse/*
RUN chown www-data:www-data /var/www/.cache /var/www/.mozilla
RUN sed -e 's/^#\(chromium_options=.*\)$/\1 --no-sandbox --disable-dev-shm-usage/' -e 's/^#db_pass.*/db_pass=sosse/' -i /etc/sosse/sosse.conf
RUN rm /etc/nginx/sites-enabled/default
RUN ln -s /etc/nginx/sites-available/sosse.conf /etc/nginx/sites-enabled/

WORKDIR /
USER postgres
RUN echo "listen_addresses='127.0.0.1'" >> /etc/postgresql/15/main/postgresql.conf
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER sosse WITH PASSWORD 'sosse';" && \
    createdb -O sosse sosse && \
    /etc/init.d/postgresql stop

USER root
RUN /etc/init.d/postgresql start && \
    sosse-admin migrate && \
    sosse-admin default_admin && \
    /etc/init.d/postgresql stop

RUN echo '#!/bin/bash -x \n \
/etc/init.d/postgresql start \n \
mkdir -p /run/sosse /var/log/sosse /var/lib/sosse/html/ \n \
chown -R www-data:www-data /run/sosse /var/log/sosse/ /var/lib/sosse \n \
sosse-admin migrate \n \
sosse-admin update_se \n \
sudo -u www-data sosse-admin update_mime \n \
sosse-admin collectstatic --noinput \n \
/usr/bin/uwsgi --uid www-data --gid www-data --plugin python3 --ini /etc/sosse/uwsgi.ini & \n \
/etc/init.d/nginx start \n \
sudo --preserve-env -u www-data sosse-admin crawl & \n \
tail -F /var/log/sosse/crawler.log' > /run.sh ; chmod +x /run.sh
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
CMD ["/usr/bin/bash", "/run.sh"]
