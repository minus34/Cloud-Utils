#!/usr/bin/env bash

# ---------------------------------------------------------------------------------------
# Installs The GeoDocker stack (Hadoop/Accumulo/Spark/GeoMesa) on AWS Elastic Map Reduce
#
# ---------------------------------------------------------------------------------------

VERSION="1.3.2"

KEY_NAME="Default"

aws emr create-cluster                                \
    --name "GeoDocker GeoMesa"                        \
    --release-label emr-5.2.0                         \
    --output text                                     \
    --use-default-roles                               \
    --ec2-attributes KeyName=$KEY_NAME             \
    --applications Name=Hadoop Name=Zookeeper Name=Spark \
    --instance-groups                                    \
      Name=Master,InstanceCount=1,InstanceGroupType=MASTER,InstanceType=m3.xlarge \
      Name=Workers,InstanceCount=3,InstanceGroupType=CORE,InstanceType=m3.xlarge  \
    --bootstrap-actions                                                                        \
      Name=BootstrapGeoMesa,Path=s3://geomesa-docker/bootstrap-geodocker-accumulo.sh,Args=\[-t=geomesa-$VERSION-accumulo-1.8.0,-n=gis,-p=secret,-e=TSERVER_XMX=10G,-e=TSERVER_CACHE_DATA_SIZE=6G,-e=TSERVER_CACHE_INDEX_SIZE=2G]
