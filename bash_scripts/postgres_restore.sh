#!/usr/bin/env bash

# --------------------------------------------------------------------------------------------------------
# Copies a pg_dump file from AWS S3, restores it to Postgres and grants read only access to the schema(s)
#
# Input vars:
#   0 = S3 bucket name (and folder name if not in the root folder)
#   1 = pg_dump file name(s) - space delimited
#   2 = schema name(s) - space delimited
#
# --------------------------------------------------------------------------------------------------------

# restore schema(s)
sudo mkdir ~/data
cd ~/data/

# copy dump file(s) from S3 to instance
files=({1})
for file in ${files[@]}; do
    sudo aws s3 cp s3://{0}/${file} ~/data/${file}
    sudo pg_restore -Fc -v -d postgres -p 5432 -U postgres -h localhost ~/data/${file}

    # delete dump file
    sudo find . -name "{1}" -type f -delete
done

# grant read-only user access to all tables & sequences for each schema in the dump file
schemas=({2})
for name in ${schemas[@]}; do
    sudo -u postgres psql -c "GRANT USAGE ON SCHEMA ${name} TO rouser;" postgres
    sudo -u postgres psql -c "GRANT SELECT ON ALL SEQUENCES IN SCHEMA ${name} TO rouser;" postgres
    sudo -u postgres psql -c "GRANT SELECT ON ALL TABLES IN SCHEMA ${name} to rouser;" postgres
    sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA ${name} GRANT SELECT ON SEQUENCES TO rouser;" postgres
    sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA ${name} GRANT SELECT ON TABLES TO rouser;" postgres
    sudo -u postgres psql -c "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ${name} TO rouser;" postgres
done