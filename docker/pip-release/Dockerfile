FROM biolds/sosse:pip-compose
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN apt-get update && apt-get install -y postgresql && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man

WORKDIR /
USER postgres
RUN /etc/init.d/postgresql start && \
    (until pg_isready; do sleep 1; done) && \
    psql --command "CREATE USER sosse WITH PASSWORD 'sosse';" && \
    createdb -O sosse sosse && \
    /etc/init.d/postgresql stop && \
    tar -c -p -C / -f /tmp/postgres_sosse.tar.gz /var/lib/postgresql

USER root

# PostgreSQL from Bookworm for upgrade steps
ADD bookworm.sources /etc/apt/sources.list.d/
RUN apt-get update && apt-get install -y postgresql-15 && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
RUN mkdir -p /etc/postgresql/15/main/
ADD postgresql.conf.bookworm /etc/postgresql/15/main/postgresql.conf
RUN echo 'local   all             postgres                                peer' > /etc/postgresql/15/main/pg_hba.conf
RUN echo 'auto' > /etc/postgresql/15/main/start.conf

ADD run.sh pg_run.sh /
RUN chmod +x /run.sh /pg_run.sh
CMD ["/usr/bin/bash", "/pg_run.sh"]
