#!/usr/bin/env bash

# --------------------------------------------
# install and configure Oracle Java 8
# --------------------------------------------

# add repo
sudo add-apt-repository ppa:webupd8team/java

# update stuff
sudo DEBIAN_FRONTEND=noninteractive apt -q -y update

# install debconf-utils to accept Oracle's Java license silently
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install python-software-properties debconf-utils
echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | sudo debconf-set-selections

# install Java 8
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install oracle-java8-installer

# add JAVA_HOME to environment variables (for all users)
echo "JAVA_HOME=\"/usr/lib/jvm/java-8-oracle\"" | sudo tee --append /etc/environment
source /etc/environment
