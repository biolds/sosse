#!/bin/bash -x
PG_VERSION=17
OLD_PG_VERSION=15
MIGRATION_LOG_PREFIX=/var/lib/postgresql/migration-pg${OLD_PG_VERSION}_to_pg${PG_VERSION}-

# Upgrade PG data on major upgrade
if [ -d /var/lib/postgresql/$OLD_PG_VERSION/main ] && [ ! -f /var/lib/postgresql/$PG_VERSION/main/PG_VERSION ]; then
  echo "Detected PostgreSQL $OLD_PG_VERSION data, migrating to PostgreSQL $PG_VERSION..."

  # Create the new PostgreSQL cluster
  echo "Initializing PostgreSQL $PG_VERSION cluster..."
  su postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/initdb -D /var/lib/postgresql/$PG_VERSION/main --encoding=UTF8 --locale=C"

  # Start old PostgreSQL temporarily to dump data
  echo "Starting PostgreSQL $OLD_PG_VERSION to dump data..."
  su postgres -c "/usr/lib/postgresql/$OLD_PG_VERSION/bin/pg_ctl -D /var/lib/postgresql/$OLD_PG_VERSION/main -l ${MIGRATION_LOG_PREFIX}pg${OLD_PG_VERSION}-migration.log -o '-c config_file=/etc/postgresql/$OLD_PG_VERSION/main/postgresql.conf' start" || {
    echo "Error: Could not start PostgreSQL $OLD_PG_VERSION for data dump. Migration aborted."
    exit 1
  }

  # Wait for old PostgreSQL to start
  until su postgres -c "/usr/lib/postgresql/$OLD_PG_VERSION/bin/pg_isready -p 5432"; do
    echo "Waiting for PostgreSQL $OLD_PG_VERSION to start..."
    sleep 1
  done

  # Dump all databases
  echo "Dumping PostgreSQL $OLD_PG_VERSION data..."
  su postgres -c "/usr/lib/postgresql/$OLD_PG_VERSION/bin/pg_dumpall -p 5432 | grep -v '^\(CREATE\|ALTER\) ROLE postgres[; ]' > /tmp/pg${OLD_PG_VERSION}_dump.sql"

  if [ $? -eq 0 ]; then
    # Stop old PostgreSQL
    su postgres -c "/usr/lib/postgresql/$OLD_PG_VERSION/bin/pg_ctl -D /var/lib/postgresql/$OLD_PG_VERSION/main stop"

    # Start new PostgreSQL
    echo "Starting PostgreSQL $PG_VERSION to restore data..."
    su postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/pg_ctl -D /var/lib/postgresql/$PG_VERSION/main -l ${MIGRATION_LOG_PREFIX}pg${PG_VERSION}-migration.log start" |
      grep -v 'role "postgres" already exists'

    # Wait for new PostgreSQL to start
    until su postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/pg_isready -p 5432"; do
      echo "Waiting for PostgreSQL $PG_VERSION to start..."
      sleep 1
    done

    # Restore data to new PostgreSQL
    echo "Restoring data to PostgreSQL $PG_VERSION..."
    su postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/psql -o ${MIGRATION_LOG_PREFIX}restore.log -p 5432 -f /tmp/pg${OLD_PG_VERSION}_dump.sql"

    if [ $? -eq 0 ]; then
      echo "Dump/restore migration successful!"
      # Archive old data for safety
      mv /var/lib/postgresql/$OLD_PG_VERSION /var/lib/postgresql/$OLD_PG_VERSION.migrated.backup
      # Cleanup dump file
      cp /tmp/pg${OLD_PG_VERSION}_dump.sql /var/lib/postgresql/dump.sql
      rm -f /tmp/pg${OLD_PG_VERSION}_dump.sql
    else
      echo "Error: Failed to restore data to PostgreSQL $PG_VERSION."
      exit 1
    fi

    # Stop new PostgreSQL (will be started again later)
    su postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/pg_ctl -D /var/lib/postgresql/$PG_VERSION/main stop"
  else
    echo "Error: Failed to dump PostgreSQL $OLD_PG_VERSION data."
    echo "Error: PostgreSQL migration failed."
    rm -rf /tmp/pg_upgrade
    exit 1
  fi
fi
test -e /etc/postgresql/$OLD_PG_VERSION && rm -rf /etc/postgresql/$OLD_PG_VERSION

# Extract PostgreSQL data on first run
test -e /var/lib/postgresql/$PG_VERSION || tar -x -p -C / -f /tmp/postgres_sosse.tar.gz

# Set proper ownership
chown -R 900:900 /var/lib/postgresql /etc/postgresql /var/run/postgresql
chown root:900 /var/log/postgresql
chown 900:adm /var/log/postgresql/* 2>/dev/null || true

/etc/init.d/postgresql start

export SOSSE_DB_HOST=${SOSSE_DB_HOST:-localhost}

exec bash /run.sh
