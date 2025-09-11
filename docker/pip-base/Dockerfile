FROM debian:trixie
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN groupadd -g 900 postgres && \
    useradd -u 900 -g 900 -m -d /var/lib/postgresql -s /bin/bash postgres && \
    passwd -l postgres
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y sudo curl python3-pip python3-dev python3-venv build-essential libpq-dev \
    libmagic1 nginx chromium chromium-driver firefox-esr fonts-noto unifont virtualenv npm && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz | tar -C /usr/local/bin -x -v -z -f -
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
