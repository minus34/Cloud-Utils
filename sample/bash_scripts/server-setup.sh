#!/usr/bin/env bash

# --------------------------------------------
# STEP 1 - install stuff
# --------------------------------------------

# install NGINX



# install Postgres
sudo add-apt-repository -y "deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main"
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y install postgresql-9.6
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y install postgresql-9.6-postgis-2.3 postgresql-contrib-9.6
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y install postgis

# ---------------------------------------------------
# STEP 2 - restore data to Postgres and run server
# ---------------------------------------------------

# alter postgres user and create database
sudo -u postgres psql -c "ALTER USER postgres ENCRYPTED PASSWORD '{0}';"
sudo -u postgres createdb geo
sudo -u postgres psql -c "CREATE EXTENSION adminpack;CREATE EXTENSION postgis;" geo

# create read only user and grant access to all tables & sequences
sudo -u postgres psql -c "CREATE USER rouser WITH ENCRYPTED PASSWORD '{1}';" geo
sudo -u postgres psql -c "GRANT CONNECT ON DATABASE geo TO rouser;" geo
sudo -u postgres psql -c "GRANT USAGE ON SCHEMA public TO rouser;" geo
sudo -u postgres psql -c "GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO rouser;" geo
sudo -u postgres psql -c "GRANT SELECT ON ALL TABLES IN SCHEMA public to rouser;" geo
sudo -u postgres psql -c "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rouser;" geo  # for PostGIS functions

# restore data into database and assign privileges for read only user
sudo mkdir ~/data
sudo aws s3 cp s3://s57405/cor.dmp ~/data/cor.dmp
sudo pg_restore -Fc -v -d geo -p 5432 -U postgres -h localhost ~/data/cor.dmp

sudo -u postgres psql -c "GRANT USAGE ON SCHEMA cor TO rouser;" geo
sudo -u postgres psql -c "GRANT SELECT ON ALL SEQUENCES IN SCHEMA cor TO rouser;" geo
sudo -u postgres psql -c "GRANT SELECT ON ALL TABLES IN SCHEMA cor to rouser;" geo
sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA cor GRANT SELECT ON SEQUENCES TO rouser;" geo
sudo -u postgres psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA cor GRANT SELECT ON TABLES TO rouser;" geo

# alter whitelisted postgres clients (the VPC subnet and the test client IP address)
sudo sed -i -e "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/9.6/main/postgresql.conf
echo -e "host\t geo\t rouser\t {2}\t md5" | sudo tee -a /etc/postgresql/9.6/main/pg_hba.conf
#echo -e "host\t geo\t rouser\t 101.164.227.2/32\t md5" | sudo tee -a /etc/postgresql/9.6/main/pg_hba.conf
sudo service postgresql restart

# delete dump files
cd ~/data/
sudo find . -name "*.dmp" -type f -delete

## set environment variables if needed
#export PGUSER="rouser"
#export PGPASSWORD="{1}"

