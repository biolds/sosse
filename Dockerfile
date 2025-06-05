FROM biolds/sosse:pip-base
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN mkdir /root/sosse
WORKDIR /root/sosse
ADD requirements.txt .
ADD pyproject.toml .
ADD MANIFEST.in .
ADD Makefile .
ADD package.json .
ADD swagger-initializer.js .
ADD README.md .
ADD se/ se/
ADD sosse/ sosse/
RUN apt-get update && apt-get install -y postgresql && apt-get clean
RUN make install_js_deps
RUN virtualenv /venv
RUN /venv/bin/pip install ./ && /venv/bin/pip install uwsgi && /venv/bin/pip cache purge
ADD debian/sosse.conf /etc/nginx/sites-enabled/default
RUN mkdir -p /etc/sosse/ /etc/sosse_src/ /var/log/sosse /var/log/uwsgi /var/www/.cache /var/www/.mozilla
ADD debian/uwsgi.* /etc/sosse_src/
RUN chown -R root:www-data /etc/sosse /etc/sosse_src && chmod 750 /etc/sosse_src/ && chmod 640 /etc/sosse_src/*
RUN chown www-data:www-data /var/log/sosse /var/www/.cache /var/www/.mozilla
ADD docker/run.sh docker/pg_run.sh /
RUN chmod 755 /run.sh /pg_run.sh

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    (until pg_isready; do sleep 1; done) && \
    psql --command "CREATE USER sosse WITH PASSWORD 'sosse';" && \
    createdb -O sosse sosse && \
    /etc/init.d/postgresql stop && \
    tar -c -p -C / -f /tmp/postgres_sosse.tar.gz /var/lib/postgresql

USER root
CMD ["/usr/bin/bash", "/pg_run.sh"]
