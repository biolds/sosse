FROM biolds/sosse:pip-compose
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
ADD run.sh pg_run.sh /
RUN chmod +x /run.sh /pg_run.sh
RUN apt-get update && apt-get install -y postgresql && apt-get clean

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
