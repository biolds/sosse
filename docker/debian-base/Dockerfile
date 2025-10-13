FROM debian:trixie
ADD control /
RUN apt-get update && \
    grep ^Depends: /control | sed -e "s/.*},//" -e "s/,//g" | xargs apt-get install -y && \
    apt-get clean autoclean && \
    rm -rf /control /var/lib/cache /var/lib/log /usr/share/doc /usr/share/man
