#!/usr/bin/env bash

# --------------------------------------------
# install and configure NGINX
# --------------------------------------------

# add repo
sudo add-apt-repository -y "deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx"
wget --quiet -O http://nginx.org/keys/nginx_signing.key | sudo apt-key add -

## add repo to sources
#sudo bash -c "echo 'deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx' >> /etc/apt/sources.list"
#sudo bash -c "echo 'deb-src http://nginx.org/packages/mainline/ubuntu/ xenial nginx' >> /etc/apt/sources.list"

# install
sudo DEBIAN_FRONTEND=noninteractive apt -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install nginx

# configure & start
sudo systemctl unmask nginx
sudo systemctl enable nginx
sudo systemctl start nginx
