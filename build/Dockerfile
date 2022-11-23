FROM debian:bullseye

RUN apt update && \
    apt upgrade -y && \
    apt install -y make build-essential python3-dev devscripts cdbs dh-python python3-setuptools curl gnupg2 && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
