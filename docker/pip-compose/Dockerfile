FROM biolds/sosse:pip-base
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN apt-get update
# install postgresql-client for pg_isready
RUN apt-get install -y jq postgresql-client && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
RUN virtualenv /venv
RUN /venv/bin/pip install sosse uwsgi && /venv/bin/pip cache purge
RUN jq -r '.[].dependencies[]?' /venv/lib/python3.13/site-packages/sosse/mime_plugins.json | sort -u | xargs apt install -y && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
RUN mkdir -p /etc/sosse/ /etc/sosse_src/ /var/log/sosse /var/log/uwsgi
ADD uwsgi.* /etc/sosse_src/
ADD sosse.conf /etc/nginx/sites-enabled/default
RUN chown -R root:www-data /etc/sosse /etc/sosse_src && chmod 750 /etc/sosse_src/ && chmod 640 /etc/sosse_src/*
RUN mkdir /var/www/.cache /var/www/.mozilla
RUN chown www-data:www-data /var/www/.cache /var/www/.mozilla
ADD run.sh /
RUN chmod +x /run.sh

USER root
CMD ["/usr/bin/bash", "/run.sh"]
