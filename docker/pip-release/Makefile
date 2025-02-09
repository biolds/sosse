include ../Makefile.common

.PHONY: build

build:
	cp ../run.sh .
	cp ../../debian/uwsgi.* ../../debian/sosse.conf .
	$(MAKE) -f ../Makefile.common _build
