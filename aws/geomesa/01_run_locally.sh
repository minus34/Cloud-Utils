#!/usr/bin/env bash

# RUN THIS ON YOUR MACHINE

# set your IP address
ip_address="<your EMR master server IP address>"

# set the path to your EC2 key pair's pem file
pem_file="<full path to your pem file>"

# get this script's directory
file_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# copy required files over (type 'yes' when requested)

# Pyspark script
scp -i ${pem_file} ${file_dir}/master_server_files/geomesa_convert.py hadoop@${ip_address}:~/

# GeoMesa SimpleFeatureType and Converters definitions
scp -i ${pem_file} ${file_dir}/master_server_files/gdelt.conf hadoop@${ip_address}:~/

# GeoMesa FileStore and Spark install script
scp -i ${pem_file} ${file_dir}/master_server_files/install-geomesa.sh hadoop@${ip_address}:~/

# ssh into master EMR server
ssh -i ${pem_file} hadoop@${ip_address}
