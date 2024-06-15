#!/usr/bin/bash
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_crawlpolicy;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_link;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_document;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_cookie;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_domainsetting;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_searchhistory;\""

export VRT_CIBUILDID=$(git rev-parse HEAD)
export VRT_BRANCHNAME=master
export VRT_APIURL=http://172.17.0.1:8080
export VRT_PROJECT="Default project"
export VRT_APIKEY=DEFAULTUSERAPIKEYTOBECHANGED
export VRT_ENABLESOFTASSERT="false"
export VRT_IGNORE_ERRORS="true"

exec /rf-venv/bin/robot -V config.yaml \
	--debug-file dbg-output \
	-v VRT_CIBUILDID:$(git rev-parse HEAD) \
	-v VRT_BRANCHNAME:master \
	-v VRT_APIURL:http://172.17.0.1:8080 \
	-v VRT_APIKEY:DEFAULTUSERAPIKEYTOBECHANGED \
	-v VRT_PROJECT:Default\ project \
	-v VRT_ENABLESOFTASSERT:false \
	--exitonerror --exitonfailure vrt/
