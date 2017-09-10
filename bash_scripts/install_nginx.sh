#!/usr/bin/env bash

# --------------------------------------------
# installs and configures NGINX
# --------------------------------------------

# get repo public key
wget http://nginx.org/keys/nginx_signing.key
sudo apt-key add nginx_signing.key

# add repo to sources
sudo bash -c "echo 'deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx' >> /etc/apt/sources.list"
sudo bash -c "echo 'deb-src http://nginx.org/packages/mainline/ubuntu/ xenial nginx' >> /etc/apt/sources.list"

# install
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y install nginx

# configure & start
sudo systemctl unmask nginx
sudo systemctl enable nginx
sudo systemctl start nginx
