#!/usr/bin/env bash

# --------------------------------------------
# install and configure Oracle Java 8
# --------------------------------------------

# add repo
sudo add-apt-repository ppa:webupd8team/java

# install
sudo DEBIAN_FRONTEND=noninteractive apt -q -y update
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install oracle-java8-installer

# add JAVA_HOME to environment variables (for all users)
echo "JAVA_HOME=\"/usr/lib/jvm/java-8-oracle\"" | sudo tee --append /etc/environment
source /etc/environment







