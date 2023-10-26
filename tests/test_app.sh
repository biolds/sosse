#/usr/bin/bash
SERVER_DIR=/tmp/testserver
CURRENT_DIR="$(pwd)"

test -d $SERVER_DIR && echo "Test server already exists" >&2 && exit 1

cd /tmp
git clone --depth=1 https://gitlab.com/biolds1/httpbin.git $SERVER_DIR

cd $SERVER_DIR/httpbin
python3 manage.py migrate
python3 manage.py shell -c "from django.contrib.auth.models import User ; u = User.objects.create(username='admin', is_superuser=True, is_staff=True) ; u.set_password('admin') ; u.save()"

if [ "$GITLAB_CI" == "" ]
then
    cat << EOF > /etc/systemd/system/django-test.service
[Unit]
Description=TestServer

[Service]
ExecStart=/usr/bin/python3 $SERVER_DIR/httpbin/manage.py runserver 0.0.0.0:8000
WorkingDirectory=$SERVER_DIR
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable django-test.service
    systemctl restart django-test.service
else
    /usr/bin/python3 $SERVER_DIR/httpbin/manage.py runserver 0.0.0.0:8000 &
fi

cd "$CURRENT_DIR"
cd "$(dirname $0)"/..
mkdir "$SERVER_DIR/httpbin/bin/static/"
cp -r tests/pages/ "$SERVER_DIR/httpbin/bin/static/"
