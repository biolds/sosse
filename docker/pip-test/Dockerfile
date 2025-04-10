FROM biolds/sosse:pip-base
ARG APT_PROXY=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
RUN apt update
RUN apt install -y firefox-esr wget jq make git postgresql rsync curl python3-django python3-pil
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz -O /tmp/gecko.tar.gz && \
    tar xvzf /tmp/gecko.tar.gz && \
    mv geckodriver /usr/local/bin/
RUN mkdir -p /var/lib/sosse/screenshots && git clone --depth=1 https://github.com/GurvanKervern/dummy-static-website /var/lib/sosse/screenshots/website
RUN git clone --depth=1 https://gitlab.com/biolds1/httpbin.git /root/httpbin && \
    cd /root/httpbin/httpbin && \
    python3 manage.py migrate && \
    python3 manage.py shell -c "from django.contrib.auth.models import User ; u = User.objects.create(username='admin', is_superuser=True, is_staff=True) ; u.set_password('admin') ; u.save()"
