include ../Makefile.common

.PHONY: build

build:
	cp ../pg_run.sh ../run.sh .
	cp ../../debian/uwsgi.* ../../debian/sosse.conf .
	$(MAKE) -f ../Makefile.common _build
