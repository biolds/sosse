FROM biolds/sosse:pip-base
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN apt-get update
RUN apt-get install -y postgresql-client # for pg_isready
RUN virtualenv /venv
RUN /venv/bin/pip install sosse uwsgi && /venv/bin/pip cache purge
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
