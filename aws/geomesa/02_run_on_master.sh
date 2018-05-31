#!/usr/bin/env bash

# RUN THIS ON THE EMR MASTER SERVER

# install GeoMesa and it's dependancies (takes 8-10 mins)
. install-geomesa.sh

# run the pyspark script to convert Life360 raw points into GeoMesa parquet
spark-submit --jars $GEOMESA_FS_HOME/dist/spark/geomesa-fs-spark-runtime_2.11-$GEOMESA_VERSION.jar test.py
