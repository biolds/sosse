TMP ?= /tmp
current_dir = $(shell pwd)


.PHONY: setuptools docker deb _deb

setuptools:
	python3 setup.py sdist bdist

_deb:
	dpkg-buildpackage -us -uc
	mv /osse*_amd64.deb /deb/

deb:
	mkdir $(current_dir)/deb/ &>/dev/null ||:
	docker run --rm -v $(current_dir):/osse:ro -v $(current_dir)/deb:/deb osse-deb bash -c 'cp -x -r /osse /osse-deb && make -C /osse-deb _deb'

docker:
	docker pull debian:bullseye
	cd $(current_dir)/build/ && docker build --rm -t osse-deb .
