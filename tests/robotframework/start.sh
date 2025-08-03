#!/usr/bin/bash
sosse-admin update_se
sosse-admin update_mime
sosse-admin default_admin
exec /opt/venv-robotframework/bin/robot -V config.yaml --exitonerror --exitonfailure guides/
#exec /robotframework-venv/bin/robot --exitonerror --exitonfailure 02_*.robot
