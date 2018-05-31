"""
-----------------------------------------------------------------------------------------------------------------------

Purpose: Takes raw GDELT data & converts it to GeoMesa parquet format using Pyspark on an AWS EMR instance

Author:  Hugh Saalmans

Created: 31/05/2018

Workflow:
  1. create Spark dataframe from S3 files
  2. filter data using SparkSQL and output to temp HDFS directory
  3. ingest HDFS file into GeoMesa parquet format and output to S3

Notes:
  - Code loads the data one day at a time, this is for testing on small EMR instances (e.g. 1 master, 2 core servers)

-----------------------------------------------------------------------------------------------------------------------
"""

import datetime
import geomesa_pyspark
import os
import logging

from pyspark.sql import SparkSession
from subprocess import check_output


def main():
    start_time = datetime.datetime.now()

    settings = dict()

    # Spark & GeoMesa environment vars
    settings["home"] = os.environ["HOME"]
    settings["spark_home"] = os.environ["SPARK_HOME"]
    settings["hdfs_path"] = os.environ["HDFS_PATH"]
    settings["geomesa_version"] = os.environ["GEOMESA_VERSION"]
    settings["geomesa_fs_home"] = os.environ["GEOMESA_FS_HOME"]

    # -------------------------------------------------------------------------
    # Edit these to taste (feel free to convert this bit to runtime arguments)
    # -------------------------------------------------------------------------

    # date range of data to convert
    settings["start_date"] = "2018-03-01"
    settings["end_date"] = "2018-03-31"

    # name of the GeoMesa schema, aka feature name
    settings["geomesa_schema"] = "gdelt"

    # SimpleFeatureType & Converter - can be an existing sft or a config file
    settings["sft_config"] = "gdelt"
    settings["sft_converter"] = "gdelt"

    # GeoMesa partition schema to use, note: leaf storage is set to true
    settings["partition_schema"] = "daily,z2-4bit"

    # AWS S3 & EMR settings
    settings["source_s3_bucket"] = "gdelt-open-data"
    settings["source_s3_directory"] = "events"

    settings["target_s3_bucket"] = "<your S3 bucket>"
    settings["target_s3_directory"] = "geomesa_test"

    # number of reducers for GeoMesa ingest (determines how the reduce tasks get split up)
    settings["num_reducers"] = 16

    # -------------------------------------------------------------------------

    # set path to GeoMesa FileStore Spark JAR
    settings["geomesa_fs_spark_jar"] = "{}/dist/spark/geomesa-fs-spark-runtime_2.11-{}.jar"\
        .format(settings["geomesa_fs_home"], settings["geomesa_version"])

    # set S3 and HDFS paths - must use the s3a:// URL prefix for S3
    settings["source_s3_path"] = "s3a://{}/{}".format(settings["source_s3_bucket"], settings["source_s3_directory"])
    settings["temp_hdfs_path"] = "{}/tmp/geomesa_ingest".format(settings["hdfs_path"], )
    settings["target_s3_path"] = "s3a://{}/{}".format(settings["target_s3_bucket"], settings["target_s3_directory"])

    # The GeoMesa ingest Bash command
    THE_INGEST = """{0}/bin/geomesa-fs ingest \
                        --path '{1}' \
                        --encoding parquet \
                        --feature-name {2} \
                        --spec {3} \
                        --converter {4} \
                        --partition-scheme {5} \
                        --leaf-storage true \
                        --num-reducers {6} \
                        '{7}/*.csv'""" \
        .format(settings["geomesa_fs_home"], settings["target_s3_path"], settings["geomesa_schema"],
                settings["sft_config"], settings["sft_converter"], settings["partition_schema"],
                settings["num_reducers"], settings["temp_hdfs_path"])

    # set Spark config
    conf = geomesa_pyspark.configure(
        jars=[settings["geomesa_fs_spark_jar"]],
        packages=["geomesa_pyspark", "pytz"],
        spark_home=settings["spark_home"]) \
        .setAppName("GeoMesa_Ingest_Test")

    conf.set("spark.hadoop.fs.s3.fast.upload", "true")
    conf.set("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
    conf.set("spark.speculation", "false")
    conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    conf.set("spark.kryo.registrator", "org.locationtech.geomesa.spark.GeoMesaSparkKryoRegistrator")
    conf.set("spark.shuffle.service.enabled", "true")
    conf.set("spark.dynamicAllocation.enabled", "true")

    conf.get("spark.master")

    # create a SparkSession
    spark = SparkSession \
        .builder \
        .config(conf=conf) \
        .enableHiveSupport() \
        .getOrCreate()

    logger.info("Pyspark session initiated : {}".format(datetime.datetime.now() - start_time,))

    # convert start and end date strings to dates
    start_date = datetime.datetime.strptime(settings["start_date"], '%Y-%m-%d')
    end_date = datetime.datetime.strptime(settings["end_date"], '%Y-%m-%d')

    current_date = end_date

    # for each day - copy file
    while current_date >= start_date:
        day_start_time = datetime.datetime.now()
        start_time = day_start_time

        date_string = current_date.strftime('%Y-%m-%d')
        yyyy_mm_dd = date_string.split("-")

        logger.info("{} : START".format(date_string,))

        # e.g. 's3a://gdelt-open-data/events/20180301*'
        source_file_path = "{}/{}{}{}*" \
            .format(settings["source_s3_path"], yyyy_mm_dd[0], yyyy_mm_dd[1], yyyy_mm_dd[2])

        # create input dataframe and a temporary view of it
        input_data_frame = spark.read.load(source_file_path, format="csv", delimiter="|", header="false")
        input_data_frame.createOrReplaceTempView("raw_data")

        logger.info("\t- raw data view created : {}".format(datetime.datetime.now() - start_time,))
        start_time = datetime.datetime.now()

        # run a SQL statement to filter and transform the data - and output to HDFS
        spark.sql(THE_SQL).write.save(settings["temp_hdfs_path"],
                                      format='csv', delimiter="|", mode='overwrite', header='false')

        # remove data frames from cache (not sure if required to clean up RAM)
        input_data_frame.unpersist()

        logger.info("\t- data transformed, filtered & written to HDFS : {}"
                    .format(datetime.datetime.now() - start_time,))
        start_time = datetime.datetime.now()

        # run GeoMesa command-line ingest of HDFS file - output to S3
        logger.info("\t- start GeoMesa ingest")
        ingest_result = check_output(THE_INGEST, shell=True)

        logger.info("\t- data converted to GeoMesa parquet & written to S3 : {}"
                    .format(datetime.datetime.now() - start_time,))

        logger.info("{} : DONE : {}".format(date_string, datetime.datetime.now() - day_start_time))

        current_date -= datetime.timedelta(days=1)

    logger.info("")

    spark.stop()


# filter data by Australia
THE_SQL = """SELECT * FROM raw_data
               WHERE _c40 > -43.9 AND _c40 < -9.1
               AND _c41 > 112.8 AND _c41 < 154.0"""


if __name__ == '__main__':
    full_start_time = datetime.datetime.now()

    logger = logging.getLogger()

    # set logger
    log_file = os.path.abspath(__file__).replace(".py", ".log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format="%(asctime)s %(message)s",
                        datefmt="%m/%d/%Y %I:%M:%S %p")
    logging.getLogger('py4j').setLevel(logging.ERROR)
    logging.getLogger('pyspark').setLevel(logging.ERROR)

    # setup logger to write to screen as well as writing to log file
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    GLOBAL_INFO = list()
    GLOBAL_ERRORS = list()
    GLOBAL_WARNINGS = list()

    task_name = "GeoMesa Ingest Test"

    logger.info("Start {}".format(task_name))

    main()

    time_taken = datetime.datetime.now() - full_start_time

    # return success, warnings or errors
    if len(GLOBAL_ERRORS) == 0:
        if len(GLOBAL_WARNINGS) == 0:
            hb_status = 1   # success
            messages = '; '.join(GLOBAL_INFO)
            logger.info("{0} finished : {1}".format(task_name, time_taken))
        else:
            hb_status = 2  # warning
            messages = '; '.join(GLOBAL_WARNINGS)
            logger.warning("{0} finished - with warnings! : {1}".format(task_name, time_taken))
    else:
        hb_status = 0  # failure
        messages = '; '.join(GLOBAL_ERRORS)
        logger.error("{0} finished - with errors! : {1}".format(task_name, time_taken))
