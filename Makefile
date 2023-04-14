TMP ?= /tmp
current_dir = $(shell pwd)


.PHONY: setuptools docker deb _deb

setuptools:
	python3 setup.py sdist bdist

_deb:
	dpkg-buildpackage -us -uc
	mv ../sosse*_amd64.deb /deb/

deb:
	mkdir $(current_dir)/deb/ &>/dev/null ||:
	docker run --rm -v $(current_dir):/sosse:ro -v $(current_dir)/deb:/deb registry.gitlab.com/biolds1/sosse/debian-pkg:latest bash -c 'cp -x -r /sosse /sosse-deb && make -C /sosse-deb _deb'

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
