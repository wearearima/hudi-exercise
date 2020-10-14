import pyspark
import os
import re
from datetime import datetime
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


def get_title(content):
    content = content.strip()
    title = ''
    try:
        if(content != ''):
            arr = content.split("\n", 2)
            title = arr[1]
    except:
        title = ''
    return title


def get_content(content):
    content = content.strip()
    actual_content = ''
    try:
        if(content != ''):
            arr = content.split("\n", 2)
            actual_content = arr[2]
    except:
        actual_content = ''
    return actual_content


def get_date_timestamp(content):
    content = content.strip()
    date = ''
    list1 = re.findall(r"[\d]{1,2} [ADFJMNOS]\w* [\d]{4}", content)
    try:
        if(len(list1) > 0):
            date = datetime.strptime(
                str(list1[0]), "%d %B %Y").strftime("%m/%d/%Y")
        else:
            date = ''
    except:
        date = ''
    return date


def check_if_person(date):
    if(date != ''):
        return True
    return False


os.system("echo 'PROCESSING DATA...'")

data = sc.wholeTextFiles("hdfs://namenode:8020/extra/delete")
pages = data.flatMap(lambda x: (x[1].split('</doc>'))).map(lambda x: (get_title(x), get_date_timestamp(
    x), get_content(x))).filter(lambda x: ((len(x[0]) != 0) or (len(x[1]) != 0))).filter(lambda x: check_if_person(x[1]))
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
