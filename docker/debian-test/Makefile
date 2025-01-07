include ../Makefile.common

.PHONY: build

build:
	cp ../../tests/robotframework/requirements.txt .
	cp ../../.pre-commit-config.yaml pre-commit-config.yaml
	$(MAKE) -f ../Makefile.common _build
