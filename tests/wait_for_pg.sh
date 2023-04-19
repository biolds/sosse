#!/usr/bin/bash
while true
do
	su postgres -c 'psql --command="select 1"' && break
    sleep 1s
done
