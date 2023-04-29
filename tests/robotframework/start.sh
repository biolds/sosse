#!/usr/bin/bash
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_crawlpolicy;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_link;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_document;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_cookie;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_domainsetting;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_searchhistory;\""
exec /robotframework-venv/bin/robot --exitonerror --exitonfailure tests
#exec /robotframework-venv/bin/robot --exitonerror --exitonfailure 02_*.robot
