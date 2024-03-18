FROM debian:bookworm
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt update && \
    apt upgrade -y && \
    apt install -y make build-essential python3-dev devscripts cdbs dh-python python3-setuptools curl gnupg2 npm && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
