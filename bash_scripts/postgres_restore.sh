#!/usr/bin/env bash

# ---------------------------------------------------------------------------------------
# Copies a pg_dump file from AWS S3, restores it to Postgres and grants read only access
#
# Input vars:
#   0 = S3 bucket name
#   1 = pg_dump file name
#   2 = target schema name
#
# ---------------------------------------------------------------------------------------

# restore data into database and assign privileges for read only user
sudo mkdir ~/data
sudo aws s3 cp s3://{0}/{1} ~/data/{1}
sudo pg_restore -Fc -v -d postgres -p 5432 -U postgres -h localhost ~/data/{1}

# grant read only user access to all tables & sequences
sudo -u postgres psql -c "GRANT USAGE ON SCHEMA {2} TO rouser;" postgres
sudo -u postgres psql -c "GRANT SELECT ON ALL SEQUENCES IN SCHEMA {2} TO rouser;" postgres
sudo -u postgres psql -c "GRANT SELECT ON ALL TABLES IN SCHEMA {2} to rouser;" postgres
sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA {2} GRANT SELECT ON SEQUENCES TO rouser;" postgres
sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA {2} GRANT SELECT ON TABLES TO rouser;" postgres
sudo -u postgres psql -c "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {2} TO rouser;" postgres

# delete dump files
cd ~/data/
sudo find . -name "{1}" -type f -delete
