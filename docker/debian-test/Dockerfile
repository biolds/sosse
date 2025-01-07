FROM biolds/sosse:debian
ARG APT_PROXY=
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN test -z "$APT_PROXY" || (echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf)
ADD sid.list /etc/apt/sources.list.d/
ADD 99sid /etc/apt/preferences.d/
RUN apt update
RUN apt purge -y sosse
RUN apt install -y python3-coverage python3-virtualenv flake8 sudo jq make git
RUN apt install -y -t sid pre-commit
RUN /etc/init.d/postgresql start && \
    su - postgres -c "psql --command 'ALTER USER sosse WITH SUPERUSER;'" && \
    /etc/init.d/postgresql stop
RUN git clone --depth=1 https://gitlab.com/biolds1/httpbin.git /root/httpbin && \
    cd /root/httpbin/httpbin && \
    python3 manage.py migrate && \
    python3 manage.py shell -c "from django.contrib.auth.models import User ; u = User.objects.create(username='admin', is_superuser=True, is_staff=True) ; u.set_password('admin') ; u.save()"
ADD requirements.txt /tmp
RUN virtualenv /robotframework-venv && /robotframework-venv/bin/pip install -r /tmp/requirements.txt && /robotframework-venv/bin/pip cache purge
RUN mkdir -p /var/lib/sosse/screenshots && git clone --depth=1 https://github.com/GurvanKervern/dummy-static-website /var/lib/sosse/screenshots/website
RUN test -z "$APT_PROXY" || rm /etc/apt/apt.conf.d/proxy.conf

# Pre-commit installation
RUN mkdir -p /tmp/pre-commit && cd /tmp/pre-commit && git init
ADD pre-commit-config.yaml /tmp/pre-commit/.pre-commit-config.yaml
RUN cd /tmp/pre-commit && pre-commit autoupdate && pre-commit run -a
