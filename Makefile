TMP ?= /tmp
current_dir = $(shell pwd)

.PHONY: _setuptools setuptools _setuptools_test setuptools_test _setuptools_push setuptools_push _deb \
	deb docker_doc docker_doc_push _build_doc build_doc docker_debian docker_debian_test \
	docker_debian_test_push docker_debian_pkg docker_debian_pkg_push docker_pip_base docker_pip_base_push \
	docker docker_run docker_push

# Empty default target, since the debian packagin runs `make`
all:
	@echo

_setuptools:
	virtualenv /venv
	/venv/bin/pip install build
	/venv/bin/python3 -m build .

setuptools:
	mkdir -p dist
	docker run --rm -v $(current_dir):/sosse-ro:ro -v $(current_dir)/dist:/sosse/dist biolds/sosse:pip-base bash -c 'cd /sosse && tar -C /sosse-ro --exclude=.git -caf - . | tar xf - && make _setuptools'

_setuptools_test:
	virtualenv /venv
	/venv/bin/pip install twine
	/venv/bin/pip install dist/*.whl
	/venv/bin/twine check dist/*
	mkdir /var/log/sosse/
	/venv/bin/sosse-admin check
	/venv/bin/sosse-admin default_conf > /dev/null

setuptools_test:
	docker run --rm -v $(current_dir):/sosse:ro biolds/sosse:pip-base bash -c 'cd /sosse && make _setuptools_test'

_setuptools_push:
	virtualenv /venv
	/venv/bin/pip install twine
	@echo ==============================================================================================
	@echo 'Uploading to Pypi, please use "__token__" as username, and the token (pypi-xxxxxx) as password'
	@echo ==============================================================================================
	/venv/bin/twine upload dist/*

setuptools_push:
	docker run --rm -v $(current_dir):/sosse:ro -ti biolds/sosse:pip-base bash -c 'cd /sosse && make _setuptools_push'

_deb:
	dpkg-buildpackage -us -uc
	mv ../sosse*_amd64.deb /deb/

deb:
	mkdir $(current_dir)/deb/ &>/dev/null ||:
	docker run --rm -v $(current_dir):/sosse:ro -v $(current_dir)/deb:/deb registry.gitlab.com/biolds1/sosse/debian-pkg:latest bash -c 'cp -x -r /sosse /sosse-deb && make -C /sosse-deb _deb'

docker_doc:
	docker pull debian:bullseye
	cd $(current_dir)/docker/doc/ && docker build --rm -t biolds/sosse:doc .

docker_doc_push:
	docker push biolds/sosse:doc

_build_doc:
	. /opt/sosse-doc/bin/activate ; make -C doc html

build_doc:
	mkdir -p doc/build/
	docker run --rm -v $(current_dir):/sosse:ro -v $(current_dir)/doc/build:/sosse/doc/build biolds/sosse:doc bash -c 'cd /sosse && make _build_doc'

docker_debian:
	docker pull debian:bullseye
	cd $(current_dir)/docker/debian-docker/ && docker build --rm -t biolds/sosse:debian .

docker_debian_test:
	docker pull debian:bullseye
	cd $(current_dir)/docker/debian-test/ && docker build --rm -t biolds/sosse:deb-test .

docker_debian_test_push:
	docker push biolds/sosse:deb-test

docker_debian_pkg:
	docker pull debian:bullseye
	cd $(current_dir)/docker/debian-pkg/ && docker build --rm -t registry.gitlab.com/biolds1/sosse/debian-pkg:latest .

docker_debian_pkg_push:
	docker push registry.gitlab.com/biolds1/sosse/debian-pkg:latest

docker_pip_base:
	docker pull debian:bullseye
	cd $(current_dir)/docker/pip-base/ && docker build --rm -t biolds/sosse:pip-base .

docker_pip_base_push:
	docker push biolds/sosse:pip-base

docker:
	docker build -t biolds/sosse:latest .

docker_run:
	docker volume inspect sosse_postgres &>/dev/null || docker volume create sosse_postgres
	docker volume inspect sosse_var &>/dev/null || docker volume create sosse_var
	docker run -p 8005:80 --mount source=sosse_postgres,destination=/var/lib/postgresql \
						--mount source=sosse_var,destination=/var/lib/sosse biolds/sosse:latest

docker_push:
	docker push biolds/sosse:latest
