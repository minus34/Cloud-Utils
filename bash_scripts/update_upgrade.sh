#!/usr/bin/env bash

# ----------------------------------------------------
# Updates Ubuntu repos and upgrades the OS
#
# Note: requires a reboot for upgrades to take effect
#
# ----------------------------------------------------

sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt-get -q -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' dist-upgrade
