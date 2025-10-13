FROM debian:trixie
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y virtualenv jq curl && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
RUN virtualenv /opt/sosse-doc
ADD requirements.txt requirements-rtd.txt /tmp/
RUN /opt/sosse-doc/bin/pip install -r /tmp/requirements.txt && /opt/sosse-doc/bin/pip install -r /tmp/requirements-rtd.txt
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
