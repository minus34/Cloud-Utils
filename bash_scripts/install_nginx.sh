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

# add required directories and symbolic link between them
sudo mkdir -p /etc/nginx/sites-available/minus34.com
sudo mkdir -p /etc/nginx/sites-enabled/minus34.com
sudo ln -s /etc/nginx/sites-available/minus34.com /etc/nginx/sites-enabled/

sudo mkdir -p /home/ubuntu/www
sudo chown -R ubuntu:www-data /home/ubuntu/www
sudo chmod 755 /home/ubuntu/www

# include additional config files
sudo sed -i -e "s/http {/http {\n\ninclude /etc/nginx/sites-enabled/*.conf;\n\n/g" /etc/nginx/nginx.conf






