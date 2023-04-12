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

docker_deb_test:
	docker pull debian:bullseye
	cd $(current_dir)/docker/debian-pkg-test/ && docker build --rm -t biolds/sosse:deb-test .

docker_deb_test_push:
	docker push biolds/sosse:deb-test

docker_deb:
	docker pull debian:bullseye
	cd $(current_dir)/docker/debian-pkg/ && docker build --rm -t registry.gitlab.com/biolds1/sosse/debian-pkg:latest .

docker_deb_push:
	docker push registry.gitlab.com/biolds1/sosse/debian-pkg:latest

docker:
	docker pull debian:bullseye
	docker build -t biolds/sosse:latest .

docker_run:
	docker volume inspect sosse_postgres &>/dev/null || docker volume create sosse_postgres
	docker volume inspect sosse_var &>/dev/null || docker volume create sosse_var
	docker run -p 8005:80 --mount source=sosse_postgres,destination=/var/lib/postgresql \
						--mount source=sosse_var,destination=/var/lib/sosse biolds/sosse:latest

docker_push:
	docker push biolds/sosse:latest
