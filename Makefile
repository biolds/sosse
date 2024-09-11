TMP ?= /tmp
BROWSER ?= chromium
current_dir = $(shell pwd)

.PHONY: _pip_pkg pip_pkg _pip_pkg_push pip_pkg_push _deb \
	deb docker_run docker_build docker_push _build_doc build_doc \
	doc_test_debian _doc_test_debian doc_test_pip _doc_test_pip \
	pip_pkg_check _pip_pkg_check _pip_functional_tests _pip_pkg_functional_tests _deb_pkg_functional_tests \
	_common_pip_functional_tests _rf_functional_tests _rf_functional_tests_deps functional_tests install_js_deps vrt

# Empty default target, since the debian packaging runs `make`
all:
	@echo

_pip_pkg: install_js_deps
	virtualenv /venv
	/venv/bin/pip install build
	/venv/bin/python3 -m build .

pip_pkg:
	mkdir -p dist
	docker run --rm -v $(current_dir):/sosse-ro:ro -v $(current_dir)/dist:/sosse/dist biolds/sosse:pip-base bash -c 'cd /sosse && tar -C /sosse-ro --exclude=.git -caf - . | tar xf - && make _pip_pkg'

_pip_pkg_push:
	virtualenv /venv
	/venv/bin/pip install twine
	@echo ==============================================================================================
	@echo 'Uploading to Pypi, please use "__token__" as username, and the token (pypi-xxxxxx) as password'
	@echo ==============================================================================================
	/venv/bin/twine upload --verbose dist/*

pip_pkg_push:
	docker run --rm -v $(current_dir):/sosse:ro -ti biolds/sosse:pip-test bash -c 'cd /sosse && make _pip_pkg_push'

_deb: install_js_deps
	dpkg-buildpackage -us -uc
	mv ../sosse*_amd64.deb /deb/

deb:
	mkdir $(current_dir)/deb/ &>/dev/null ||:
	docker run --rm -v $(current_dir):/sosse:ro -v $(current_dir)/deb:/deb biolds/sosse:debian-pkg bash -c 'cp -x -r /sosse /sosse-deb && make -C /sosse-deb _deb'

_build_doc:
	./doc/build_changelog.sh > doc/source/CHANGELOG.md
	sed -e 's#|sosse-admin|#sosse-admin#' doc/source/install/database.rst.template > doc/source/install/database_debian_generated.rst
	sed -e 's#|sosse-admin|#/opt/sosse-venv/bin/sosse-admin#' doc/source/install/database.rst.template > doc/source/install/database_pip_generated.rst
	. /opt/sosse-doc/bin/activate ; make -C doc linkcheck html SPHINXOPTS="-W"
	jq . < doc/code_blocks.json > /tmp/code_blocks.json
	mv /tmp/code_blocks.json doc/code_blocks.json

build_doc:
	mkdir -p doc/build/
	docker run --rm -v $(current_dir):/sosse:ro -v $(current_dir)/doc:/sosse/doc biolds/sosse:doc bash -c 'cd /sosse && make _build_doc'

doc_gen:
	apt update
	grep ^Depends: debian/control | sed -e "s/.*},//" -e "s/,//g" | xargs apt install -y
	./sosse-admin extract_doc conf > doc/source/config_file_generated.rst
	./sosse-admin extract_doc cli > doc/source/cli_generated.rst
	./sosse-admin extract_doc se > doc/source/user/shortcut_list_generated.rst
	./doc/build_changelog.sh > doc/source/CHANGELOG.md
	sed -e 's#|sosse-admin|#sosse-admin#' doc/source/install/database.rst.template > doc/source/install/database_debian_generated.rst
	sed -e 's#|sosse-admin|#/opt/sosse-venv/bin/sosse-admin#' doc/source/install/database.rst.template > doc/source/install/database_pip_generated.rst
	cat README.md | grep -v '^=\+$$' | sed -e 's/^\(SOSSE 🦦\)$$/# \1/' -e 's/^\(Try it out\|Keep in touch\)/## \1/' -e 's#https://sosse.readthedocs.io/en/stable/##g' -e 's#\[documentation\]()#documentation#' -e 's#\[documentation\](install.html)#[install pages](install.html)#' -e 's/\(install\|screenshots\).html/\1/' > doc/source/introduction.md

docker_run:
	docker volume inspect sosse_postgres &>/dev/null || docker volume create sosse_postgres
	docker volume inspect sosse_var &>/dev/null || docker volume create sosse_var
	docker run -p 8005:80 --mount source=sosse_postgres,destination=/var/lib/postgresql \
						--mount source=sosse_var,destination=/var/lib/sosse biolds/sosse:latest

docker_release_push:
	docker push biolds/sosse:latest

docker_release_build:
	docker pull debian:bookworm
	$(MAKE) -C docker/pip-base build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C docker/pip-release build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	docker tag biolds/sosse:pip-release biolds/sosse:latest

docker_git_build:
	docker pull debian:bookworm
	$(MAKE) -C docker/pip-base build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	docker build --build-arg APT_PROXY=$(APT_PROXY) --build-arg PIP_INDEX_URL=$(PIP_INDEX_URL) --build-arg PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST) -t biolds/sosse:git .

docker_push:
	$(MAKE) -C docker push

docker_build:
	$(MAKE) -C docker build

_doc_test_debian:
	cp doc/code_blocks.json /tmp/code_blocks.json
	grep -q 'apt install -y sosse' /tmp/code_blocks.json
	sed -e 's#apt install -y sosse#apt install -y sosse; /etc/init.d/nginx start \& /etc/init.d/postgresql start \& bash ./tests/wait_for_pg.sh#' -i /tmp/code_blocks.json
	bash ./tests/doc_test.sh /tmp/code_blocks.json install/debian

doc_test_debian:
	docker run -v $(current_dir):/sosse:ro debian:bookworm bash -c 'cd /sosse && apt-get update && apt-get install -y make jq && make _doc_test_debian'

_doc_test_pip:
	apt install -y chromium chromium-driver postgresql libpq-dev nginx python3-dev python3-pip virtualenv
	/etc/init.d/postgresql start &
	bash ./tests/wait_for_pg.sh
	bash ./tests/doc_test.sh doc/code_blocks.json install/pip

doc_test_pip:
	docker run -v $(current_dir):/sosse:ro debian:bookworm bash -c 'cd /sosse && apt-get update && apt-get install -y make jq && make _doc_test_pip'

_pip_pkg_check:
	pip install twine
	twine check dist/*

pip_pkg_check:
	docker run --rm -v $(current_dir):/sosse:ro biolds/sosse:pip-base bash -c 'cd /sosse && make _pip_pkg_check'

_pip_functional_tests: install_js_deps
	make _common_pip_functional_tests
	/etc/init.d/postgresql start &
	bash ./tests/wait_for_pg.sh
	grep -q 'pip install sosse' /tmp/code_blocks.json
	sed -e 's#pip install sosse#pip install ./#' -i /tmp/code_blocks.json
	bash ./tests/doc_test.sh /tmp/code_blocks.json install/pip

_pip_pkg_functional_tests:
	make _common_pip_functional_tests
	/etc/init.d/postgresql start &
	bash ./tests/wait_for_pg.sh
	grep -q 'pip install sosse' /tmp/code_blocks.json
	sed -e 's#pip install sosse#pip install dist/*.whl#' -i /tmp/code_blocks.json
	bash ./tests/doc_test.sh /tmp/code_blocks.json install/pip

_common_pip_functional_tests:
	cp doc/code_blocks.json /tmp/code_blocks.json
	grep -q 'sosse-admin default_conf' /tmp/code_blocks.json
	sed -e 's#sosse-admin default_conf#sosse-admin default_conf | sed -e \\"s/^.chromium_options=.*/chromium_options=--enable-precise-memory-info --disable-default-apps --headless --no-sandbox --disable-dev-shm-usage/\\" -e \\"s/^.browser_crash_retry=.*/browser_crash_retry=3/\\" -e \\"s/^.crawler_count=.*/crawler_count=1/\\" -e \\"s/^.debug=.*/debug=true/\\"#' -e \\"s/^.default_browser=.*/default_browser=$(BROWSER)/\\" -i /tmp/code_blocks.json # add --no-sandbox --disable-dev-shm-usage to chromium's command line
	echo 'SOSSE_ADMIN: /opt/sosse-venv/bin/sosse-admin' > tests/robotframework/config.yaml

_deb_pkg_functional_tests:
	grep ^Depends: debian/control | sed -e "s/.*},//" -e "s/,//g" | xargs apt install -y
	grep '^ExecStartPre=' debian/sosse-uwsgi.service | sed -e 's/^ExecStartPre=-\?+\?//' -e 's/^/---- /'
	bash -c "`grep '^ExecStartPre=' debian/sosse-uwsgi.service | sed -e 's/^ExecStartPre=-\?+\?//'`"
	cp doc/code_blocks.json /tmp/code_blocks.json
	grep -q 'apt install -y sosse' /tmp/code_blocks.json
	sed -e 's#apt install -y sosse#apt install -y sudo; dpkg -i deb/*.deb ; /etc/init.d/postgresql start \& bash ./tests/wait_for_pg.sh#' -i /tmp/code_blocks.json
	bash ./tests/doc_test.sh /tmp/code_blocks.json install/debian
	sed -e 's/^.chromium_options=.*/chromium_options=--enable-precise-memory-info --disable-default-apps --headless --no-sandbox --disable-dev-shm-usage/' -i /etc/sosse/sosse.conf # add --no-sandbox --disable-dev-shm-usage to chromium's command line
	sed -e 's/^.browser_crash_retry=.*/browser_crash_retry=3/' -i /etc/sosse/sosse.conf
	sed -e 's/^.debug=.*/debug=true/' -i /etc/sosse/sosse.conf
	sed -e 's/^.crawler_count=.*/crawler_count=1/' -i /etc/sosse/sosse.conf
	/etc/init.d/nginx start
	sed -e "s/^.default_browser=.*/default_browser=$(BROWSER)/" -i /etc/sosse/sosse.conf
	bash -c 'uwsgi --uid www-data --gid www-data --plugin python3 --ini /etc/sosse/uwsgi.ini --logto /var/log/sosse/uwsgi.log & sudo -u www-data sosse-admin crawl &'
	bash ./tests/docker_run.sh docker/pip-test/Dockerfile

_rf_functional_tests_deps:
	cat /etc/sosse/sosse.conf
	cat /etc/nginx/sites-enabled/sosse.conf
	ls /var/lib/sosse/static
	ls /var/lib/sosse/static/swagger
	virtualenv /rf-venv
	/rf-venv/bin/pip install -r tests/robotframework/requirements.txt

_rf_functional_tests: _rf_functional_tests_deps
	cd ./tests/robotframework && /rf-venv/bin/robot -V config.yaml --exitonerror --exitonfailure tests/

functional_tests:
	docker run --rm -v $(current_dir):/sosse biolds/sosse:pip-test bash -c 'cd /sosse && make _pip_functional_tests _rf_functional_tests'

static_checks:
	flake8 --ignore=E501,W503,W504 --exclude=migrations,tests
	bash -c 'for f in $$(find -name \*.py|grep -v /__init__\.py$$) ; do grep -q "^# Copyright" "$$f" || echo "File $$f does not have a copyright header" ; done'
	bash -c 'for f in $$(find -name \*.py|grep -v /__init__\.py$$) ; do grep -q "^# Copyright" "$$f" || exit 1 ; done'

install_js_deps:
	npm install
	rm -rf se/static/swagger/
	cp -r node_modules/swagger-ui-dist/ se/static/swagger/
	cp swagger-initializer.js se/static/swagger/
	rm -rf se/static/se/node_modules
	cp -r node_modules/ se/static/se/

vrt:
	docker run -v $(current_dir):/sosse -p 8001:80 -ti biolds/sosse:pip-test bash -c 'cd /sosse && echo "SOSSE_ADMIN: /opt/sosse-venv/bin/sosse-admin" > tests/robotframework/config.yaml && make _pip_functional_tests _rf_functional_tests_deps && /rf-venv/bin/pip install git+https://github.com/biolds/robotframework-VRTLibrary/ && git config --global --add safe.directory /sosse && bash -i'

_docker_unit_test_prepare:
	echo 'sudo --preserve-env=PYTHONPATH -u www-data python3-coverage run -a --source se,sosse ./sosse/sosse_admin.py "$$@"' > /tmp/sudo_sosse
	chmod 755 /tmp/sudo_sosse
	apt update
	grep ^Depends: debian/control | sed -e "s/.*},//" -e "s/,//g" | xargs apt install -y
	/etc/init.d/postgresql start
	mkdir -p /var/lib/sosse/screenshots /var/lib/sosse/html /var/lib/sosse/log /var/lib/sosse/browser_config /root/httpbin/httpbin/bin/static/
	chown -R www-data:www-data /var/lib/sosse/ /var/log/sosse /var/lib/sosse/browser_config
	cp -r tests/pages/ /root/httpbin/httpbin/bin/static/
	/usr/bin/python3 /root/httpbin/httpbin/manage.py runserver 0.0.0.0:8000 &
	/tmp/sudo_sosse default_conf | sed -e "s/^#debug=.*/debug=true/" -e "s/#dl_check_time=.*/dl_check_time=1/" -e "s,#online_check_url.*,online_check_url=http://localhost:8000/," -e "s/^#chromium_options=\(.*\)/chromium_options=\1 --no-sandbox --disable-dev-shm-usage/" > /etc/sosse/sosse.conf

docker_unit_test_prepare:
	docker run -v $(current_dir):/sosse -ti biolds/sosse:debian-test bash -c 'cp -r /sosse /sosse-rw ; export PYTHONPATH=/sosse-rw ; cd /sosse-rw ; make _docker_unit_test_prepare ; bash -i'
