#!/usr/bin/env bash

# --------------------------------------------
# install and configure NGINX
# --------------------------------------------

# add repo
sudo add-apt-repository -y "deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx"

# add repo to sources
sudo bash -c "echo 'deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx' >> /etc/apt/sources.list"
sudo bash -c "echo 'deb-src http://nginx.org/packages/mainline/ubuntu/ xenial nginx' >> /etc/apt/sources.list"

# get GPG key
sudo wget --quiet https://nginx.org/keys/nginx_signing.key -O - | sudo apt-key add -
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys ABF5BD827BD9BF62

# install
sudo DEBIAN_FRONTEND=noninteractive apt -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install nginx

# configure & start
sudo systemctl unmask nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# add new site
