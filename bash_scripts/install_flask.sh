#!/usr/bin/env bash

# --------------------------------------------
# install pip and required python modules
# --------------------------------------------

sudo DEBIAN_FRONTEND=noninteractive apt -q -y install python3-pip
sudo -H pip3 install --upgrade pip

sudo -H pip3 install gunicorn

sudo -H pip3 install Flask
sudo -H pip3 install Flask-Compress
sudo -H pip3 install Flask-Cors

sudo -H pip3 install psycopg2
