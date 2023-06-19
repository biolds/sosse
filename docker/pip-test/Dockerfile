FROM biolds/sosse:pip-base
ARG APT_PROXY=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt install -y firefox-esr wget jq make git
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz -O /tmp/gecko.tar.gz && \
    tar xvzf /tmp/gecko.tar.gz && \
    mv geckodriver /usr/local/bin/
RUN mkdir -p /var/lib/sosse/screenshots && git clone --depth=1 https://github.com/GurvanKervern/dummy-static-website /var/lib/sosse/screenshots/website
