#!/usr/bin/bash
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_crawlpolicy;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_link;\""
su - postgres -c "psql -d sosse --command=\"DELETE FROM se_document;\""
exec /robotframework-venv/bin/robot --exitonerror --exitonfailure *_*.robot
