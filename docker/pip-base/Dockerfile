FROM debian:bookworm
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN groupadd -g 900 postgres && \
    useradd -u 900 -g 900 -m -d /var/lib/postgresql -s /bin/bash postgres && \
    passwd -l postgres
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y sudo python3-pip python3-dev python3-venv build-essential libpq-dev libmagic1 nginx chromium chromium-driver firefox-esr fonts-noto unifont virtualenv npm
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
