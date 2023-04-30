FROM debian:bullseye
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt update
RUN apt upgrade -y
RUN apt install -y virtualenv jq curl
RUN virtualenv /opt/sosse-doc
ADD requirements.txt /tmp/
RUN . /opt/sosse-doc/bin/activate && pip install -r /tmp/requirements.txt
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
