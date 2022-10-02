SOSSE_DOCKER_VER ?= main
TMP ?= /tmp
current_dir = $(shell pwd)


.PHONY: setuptools docker deb _deb

setuptools:
	python3 setup.py sdist bdist

_deb:
	dpkg-buildpackage -us -uc
	mv /sosse*_amd64.deb /deb/

deb:
	mkdir $(current_dir)/deb/ &>/dev/null ||:
	docker run --rm -v $(current_dir):/sosse:ro -v $(current_dir)/deb:/deb sosse-deb bash -c 'cp -x -r /sosse /sosse-deb && make -C /sosse-deb _deb'

docker:
	docker pull debian:bullseye
	cd $(current_dir)/build/ && docker build --rm -t sosse-deb .

sosse_docker:
	docker pull debian:bullseye
	docker build --build-arg SOSSE_DOCKER_VER=$(SOSSE_DOCKER_VER) -t sosse:$(SOSSE_DOCKER_VER) .
