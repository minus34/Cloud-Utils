#!/usr/bin/env bash

# --------------------------------------------------------------------------------------
# Installs Apache Spark
#
# --------------------------------------------------------------------------------------

# download binaries
cd ~
wget --quiet -O - https://www.apache.org/dyn/closer.lua/spark/spark-2.2.1/spark-2.2.1-bin-hadoop2.7.tgz

# unzip and copy to final resting place





# set SPARK_HOME environment var







# install pip and PySpark
sudo DEBIAN_FRONTEND=noninteractive apt -q -y install python3-pip
sudo -H pip3 install --upgrade pip
sudo -H pip3 install pyspark

