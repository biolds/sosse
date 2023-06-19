.PHONY=build

build:
	docker pull debian:bookworm
	$(MAKE) -C debian build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C debian-pkg build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C debian-test build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C pip-base build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C pip-release build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C pip-test build APT_PROXY=$(APT_PROXY) PIP_INDEX_URL=$(PIP_INDEX_URL) PIP_TRUSTED_HOST=$(PIP_TRUSTED_HOST)
	$(MAKE) -C doc build

push:
	@for a in $$(ls); do \
		if [ -d $$a ]; then \
			$(MAKE) -C $$a push; \
		fi; \
	done;
