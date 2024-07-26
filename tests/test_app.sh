#/usr/bin/bash
SERVER_DIR=/tmp/testserver
SRC_SERVER_DIR=/tmp/srctestserver
SOSSE_TEST_DIR="$(dirname "$0")"
CURRENT_DIR="$(pwd)"

if [ -d "$SERVER_DIR" ]; then
	echo "Test server already exists" >&2
else
	if [ -d "$SRC_SERVER_DIR" ]; then
		cp -r "$SRC_SERVER_DIR" "$SERVER_DIR"
	else
		cd /tmp
		git clone --depth=1 https://gitlab.com/biolds1/httpbin.git $SERVER_DIR
	fi
fi

cd $SERVER_DIR/httpbin

if [ ! -e /tmp/httpbin-db.sqlite3 ]; then
	python3 manage.py migrate
	python3 manage.py shell -c "from django.contrib.auth.models import User ; u = User.objects.create(username='admin', is_superuser=True, is_staff=True) ; u.set_password('admin') ; u.save()"
fi

if [ ! -e /etc/systemd/system/django-test.service ]; then
	if [ "$GITLAB_CI" == "" ]; then
		cat <<EOF >/etc/systemd/system/django-test.service
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
else
	echo "Service already exist" >&2
fi

cd "$CURRENT_DIR"
mkdir -p "$SERVER_DIR/httpbin/bin/static/"
rsync -avz "$SOSSE_TEST_DIR/pages" "$SERVER_DIR/httpbin/bin/static/"
