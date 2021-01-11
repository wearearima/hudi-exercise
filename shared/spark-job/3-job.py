import pyspark
import os
from utils import Utils
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.sql import SQLContext
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession

conf = (SparkConf()
        .setMaster("spark://sparkmaster:7077")
        .setAppName("HUDI_EXERCISE"))

sc = SparkContext(conf=conf)
spark = SparkSession(sc)

os.system("echo 'PROCESSING DATA...'")

sc.addPyFile("/var/hoodie/ws/spark-job/utils.py")
data = sc.wholeTextFiles("hdfs://namenode:8020/wiki/extra/delete")

pages = data.flatMap(lambda x: (x[1].split('</doc>'))).map(lambda x: (Utils.get_title(x), Utils.get_date_timestamp(
    x), Utils.get_content(x))).filter(lambda x: ((len(x[0]) != 0) or (len(x[1]) != 0))).filter(lambda x: Utils.check_if_person(x[1]))
df = pages.toDF(["title", "date", "content"])
df = df.select('title', to_date(
    df.date, 'MM/dd/yyyy').alias('date'), "content")

tableName = "hudi_celebrities"
basePath = "hdfs://namenode:8020/wiki/hudi_celebrities"

hudi_delete_options = {
    'hoodie.table.name': tableName,
    'hoodie.datasource.write.table.type': 'COPY_ON_WRITE',
    'hoodie.datasource.write.operation': 'delete',
    'hoodie.datasource.write.recordkey.field': 'title',
    'hoodie.datasource.write.precombine.field': 'title',
    'hoodie.datasource.write.table.name': tableName,
    'hoodie.upsert.shuffle.parallelism': 2,
    'hoodie.insert.shuffle.parallelism': 2,
    'hoodie.datasource.write.keygenerator.class': 'org.apache.hudi.keygen.NonpartitionedKeyGenerator'
}

df.write.format("hudi").options(
    **hudi_delete_options).mode("append").save(basePath)
