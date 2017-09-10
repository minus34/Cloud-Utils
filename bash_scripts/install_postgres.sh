#!/usr/bin/env bash

# --------------------------------------------------------------------------------------
# Installs Postgres & PostGIS, adds a read only user and enables access to the database
#
# Input vars:
#   0 = postgres user password
#   1 = read-only user (rouser) password
#   2 = CIDP IP range(s) that can access the database server - space delimited
#
# --------------------------------------------------------------------------------------

# add repo
sudo add-apt-repository -y "deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main"
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# install
sudo DEBIAN_FRONTEND=noninteractive apt -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install postgresql-9.6
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install postgresql-9.6-postgis-2.3 postgresql-contrib-9.6
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install postgis

# alter postgres user and create database
sudo -u postgres psql -c "ALTER USER postgres ENCRYPTED PASSWORD '{0}';"
#sudo -u postgres psql -c "CREATE EXTENSION adminpack;CREATE EXTENSION postgis;" postgres
sudo -u postgres psql -c "CREATE EXTENSION postgis;" postgres

# create read only user and grant access to all tables & sequences in public schema (to enable PostGIS use)
sudo -u postgres psql -c "CREATE USER rouser WITH ENCRYPTED PASSWORD '{1}';" postgres
sudo -u postgres psql -c "GRANT CONNECT ON DATABASE postgres TO rouser;" postgres
sudo -u postgres psql -c "GRANT USAGE ON SCHEMA public TO rouser;" postgres
sudo -u postgres psql -c "GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO rouser;" postgres
sudo -u postgres psql -c "GRANT SELECT ON ALL TABLES IN SCHEMA public to rouser;" postgres
sudo -u postgres psql -c "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rouser;" postgres  # for PostGIS functions

# whitelist postgres clients (if any)
ip_ranges=({2})

if [ ${#ip_ranges[@]} -gt 0 ]; then
    # allow external access to postgres
    sudo sed -i -e "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/9.6/main/postgresql.conf

    # enable client IP range access for read-only user
    for ip_range in ${ip_ranges[@]}; do
        echo -e "host\t postgres\t rouser\t ${ip_range}\t md5" | sudo tee -a /etc/postgresql/9.6/main/pg_hba.conf
    done
fi

sudo service postgresql restart
