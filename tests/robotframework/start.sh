#!/usr/bin/bash
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_crawlpolicy;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_link;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_document;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_cookie;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_domainsetting;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_searchhistory;\""
su - postgres -c "psql -d sosse --command=\"TRUNCATE auth_user CASCADE;\""
su - postgres -c "psql -d sosse --command=\"ALTER SEQUENCE auth_user_id_seq RESTART WITH 1;\""
su - postgres -c "psql -d sosse --command=\"TRUNCATE se_webhook CASCADE;\""
sosse-admin update_se
sosse-admin default_admin
exec /opt/venv-robotframework/bin/robot -V config.yaml --exitonerror --exitonfailure docs/
#exec /robotframework-venv/bin/robot --exitonerror --exitonfailure 02_*.robot
