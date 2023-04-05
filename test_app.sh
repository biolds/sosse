#/usr/bin/bash
SERVER_DIR=/tmp/testserver

test -d $SERVER_DIR && echo "Test server already exists" >&2 && exit 1

mkdir $SERVER_DIR
django-admin startproject testserver $SERVER_DIR
cd $SERVER_DIR
python3 manage.py migrate
echo "ALLOWED_HOSTS = ['*']" >> $SERVER_DIR/testserver/settings.py

if [ "$GITLAB_CI" == "" ]
then
    cat << EOF > /etc/systemd/system/django-test.service
[Unit]
Description=TestServer

[Service]
ExecStart=/usr/bin/python3 $SERVER_DIR/manage.py runserver 0.0.0.0:8000
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
    /usr/bin/python3 $SERVER_DIR/manage.py runserver 0.0.0.0:8000 &
fi
