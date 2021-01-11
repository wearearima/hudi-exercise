# Example exercise with Apache HUDI

An example exercise that puts into practice the ideas explained in the following [post](https://blog.arima.eu/en/2020/10/20/exprimiendo-tu-data-lake-parte-I-hudi.html), which talks about the evolution of storage systems in Big Data environments, specifically Data Lakes, and how [Apache Hudi](https://hudi.apache.org) can help to manage them.

## Aim

To download a large number of Wikipedia entries and identify those that are about celebrities through an Apache Spark process. Store the result in HDFS as Parquet files using the Apache Hudi tool. Once the operation is completed, carry out a series of updates on the data to verify that Hudi generates and compacts the new files efficiently, checking the lineage of each operation for the modifications which have been made.

## Prerequisites

* [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Docker](https://docs.docker.com/get-docker)
* [Docker-compose](https://docs.docker.com/compose/install)

## Starting

We will run a Hadoop cluster in Docker containers (orchestrated by docker-compose) to configure and execute all the necessary services:

* [HADOOP HDFS](https://hadoop.apache.org/docs/r1.2.1/hdfs_design.html) - HDFS distributed file system.
* [APACHE HIVE](https://hive.apache.org) - Data storage infrastructure built on top of Hadoop for grouping, querying and data analytics.
* [APACHE SPARK](https://hadoop.apache.org/docs/r1.2.1/hdfs_design.html) - Distributed computing framework.
* [APACHE HUDI](https://hudi.apache.org) - Tool for ingesting and storing large analytical data sets across distributed file systems.

## Exercise

Here are the steps to launch the exercise:

### STEP 1 - Clone the project from GitHub

~~~
git clone https://github.com/wearearima/hudi-exercise.git
~~~

### STEP 2 - Initialize the cluster

All the necessary services are defined in the `docker-compose.yml` file. Run the following script to initialize the cluster:

~~~
./start.sh
~~~

### STEP 3 - Copy all the data from WIKI to the HDFS distributed file system

~~~
docker exec -it namenode /bin/bash hdfs dfs -copyFromLocal /wiki /wiki
~~~

---
**NOTE**

You can check if the container `namenode` is already launched with the command: `docker exec -it namenode hdfs dfsadmin -report`

---

### STEP 4 - Search for the celebrities with Apache Spark and save them to HDFS (Parquet) using the Apache Hudi tool. 

The Spark job is located in `./shared/spark-job/1-job.py` and it has two important parts:

1. Filter and obtain celebrities. We consider that a Wikipedia entry is a celebrity if there is a date within the first 150 characters of its content (this has been heavily inspired by the following [post](https://towardsdatascience.com/process-wikipedia-using-apache-spark-to-create-spicy-hot-datasets-1a59720e6e25))

    ```python
    ...

    data = sc.wholeTextFiles("hdfs://namenode:8020/wiki/wiki_*")
    pages = data.flatMap(lambda x: (x[1].split('</doc>'))).map(lambda x: (Utils.get_title(x), Utils.get_date_timestamp(
        x), Utils.get_content(x))).filter(lambda x: ((len(x[0]) != 0) or (len(x[1]) != 0))).filter(lambda x: Utils.check_if_person(x[1]))
    df = pages.toDF(["title", "date", "content"])
    df = df.select('title', to_date(df.date, 'MM/dd/yyyy').alias('date'), "content")
    ```
    (NOTE) The result of this execution will be a Spark DataFrame `df` with the following schema:
    ~~~
    >>> df.printSchema()
    root
    |-- title: string (nullable = true)
    |-- date: date (nullable = true)
    |-- content: string (nullable = true)
    ~~~

2. Transform the Dataframe `df` into a Parquet file and save it to HDFS using Apache Hudi.

    ```python
    tableName = "hudi_celebrities"
    basePath = "hdfs://namenode:8020/wiki/hudi_celebrities"

    hudi_options = {
        'hoodie.table.name': tableName,
        'hoodie.datasource.write.table.type': 'COPY_ON_WRITE',
        'hoodie.datasource.write.operation': 'upsert',
        'hoodie.datasource.write.recordkey.field': 'title',
        'hoodie.datasource.write.precombine.field': 'title',
        'hoodie.datasource.write.table.name': tableName,
        'hoodie.upsert.shuffle.parallelism': 2,
        'hoodie.insert.shuffle.parallelism': 2,
        'hoodie.datasource.write.keygenerator.class': 'org.apache.hudi.keygen.NonpartitionedKeyGenerator',
        'hoodie.datasource.hive_sync.enable': 'true',
        'hoodie.datasource.hive_sync.table': tableName,
        'hoodie.datasource.hive_sync.partition_extractor_class': 'org.apache.hudi.hive.NonPartitionedExtractor',
        'hoodie.datasource.hive_sync.jdbcurl': 'jdbc:hive2://hiveserver:10000'
    }

    df.write.format("hudi").options(**hudi_options).mode("overwrite").save(basePath)
    ```

    These are the most important parts of the above `hudi_options`:

    * Table type `COPY_ON_WRITE` is one of the options HUDI offers for managing their tables. You can get more information about the different Hudi table types in the [official documentation](https://hudi.apache.org/docs/concepts.html#table-types).
    * The properties of type `hoodie.datasource.hive ...` configure HUDI to automatically generate a HIVE table, with which you can query the data using SQL.
    * `Overwrite` mode is used, so if the folder `hdfs://namenode:8020/wiki/hudi_celebrities` already exists, Hudi will delete it and generate the data again from scratch.

Launch the first process:

~~~
docker exec -it adhoc-1 /bin/bash spark-submit \
--packages org.apache.hudi:hudi-spark-bundle_2.11:0.6.0,org.apache.spark:spark-avro_2.11:2.4.4 \
--conf 'spark.serializer=org.apache.spark.serializer.KryoSerializer' \
/var/hoodie/ws/spark-job/1-job.py
~~~

Check the results inside the `adhoc-1` container:

~~~
docker exec -it adhoc-1 /bin/bash
~~~

Once inside, check:

1. That the HUDI library managed the merging of datasets effectively:

    - root@adhoc-1:/# `/var/hoodie/ws/hudi-cli/hudi-cli.sh`
    - hudi-> `connect --path hdfs://namenode:8020/wiki/hudi_celebrities`<br/><br/>![Alt text](images/hudi-cli.png)

    A) HUDI table description

    - hudi:hudi_celebrities-> `desc`<br/><br/>![Alt text](images/hudi-desc.png)
       
    B) Verify first commit

    - hudi:hudi_celebrities-> `commits show  --desc true`<br/><br/>![Alt text](images/hudi-commits.png)
    <br/><br/>
    > **_NOTE:_**  You can exit the HUDI client by typing: `exit`


### STEP 5 - Make insert and update modifications to the dataset

Run a new process to modify the data. Unlike the previous one, this will just load a text file with 2 celebrities:

1. A new celebrity that needs to be added to the existing dataset.
2. A celebrity that already exists in the dataset but has been updated.

The process is in the file `spark-job/2-job.py` and is pretty similar to the previous one, except that in this case the writing mode is `append` because we are updating an existing Hudi table.

```python
....

df.write.format("hudi").options(**hudi_options).mode("append").save(basePath)
```

Run the second process:

~~~
docker exec -it adhoc-1 /bin/bash spark-submit \
--packages org.apache.hudi:hudi-spark-bundle_2.11:0.6.0,org.apache.spark:spark-avro_2.11:2.4.4 \
--conf 'spark.serializer=org.apache.spark.serializer.KryoSerializer' \
/var/hoodie/ws/spark-job/2-job.py
~~~

Once again, we will check the results inside the `adhoc-1` container:

~~~
docker exec -it adhoc-1 /bin/bash
~~~

Once inside the container, check:

1. That a new celebrity has been inserted (New Celebrity) and an existing one has been modified (Dean Koontz):

    - root@adhoc-1:/# `$SPARK_INSTALL/bin/pyspark --driver-class-path /opt/hive/conf --packages org.apache.hudi:hudi-spark-bundle_2.11:0.6.0,org.apache.spark:spark-avro_2.11:2.4.4 --conf spark.sql.hive.convertMetastoreParquet=false`<br/><br/>![Alt text](images/shell-pyspark.png)
    - &#62;&#62;&#62; `spark.sql("select title, date, content from hudi_celebrities where title='New Celebritie'").show(1, False)`<br/><br/>![Alt text](images/new-celebritie.png)
    - &#62;&#62;&#62; `spark.sql("select title, date, content from hudi_celebrities where title='Dean Koontz'").show(1, False)`<br/><br/>![Alt text](images/updated-celebritie.png)
    - &#62;&#62;&#62; `exit()`

2. That the HUDI library has managed everything automatically:

    - root@adhoc-1:/# `/var/hoodie/ws/hudi-cli/hudi-cli.sh`
    - hudi-> `connect --path hdfs://namenode:8020/wiki/hudi_celebrities`    

    A) Verify the second commit:

    - hudi:hudi_celebrities-> `commits show  --desc true`<br/><br/>![Alt text](images/hudi-commits-2.png)
        
    B) Check commit information

    - hudi:hudi_celebrities-> `commit showfiles --commit 20201013214314`<br/><br/>![Alt text](images/info-commit-2.png)
    <br/><br/>
    > **_NOTE:_**  You can exit the HUDI client by typing: `exit`

### STEP 6 - Delete one of the celebrities from the dataset

This process will load a file that includes the celebrity to be deleted.

The process `./shared/spark-job/3-job.py`, is practically the same as the previous ones, but it is configured to delete data `hudi_delete_options`:

```python
....

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
```

Run the third process:

~~~
docker exec -it adhoc-1 /bin/bash spark-submit \
--packages org.apache.hudi:hudi-spark-bundle_2.11:0.6.0,org.apache.spark:spark-avro_2.11:2.4.4 \
--conf 'spark.serializer=org.apache.spark.serializer.KryoSerializer' \
/var/hoodie/ws/spark-job/3-job.py
~~~

Check the results inside the `adhoc-1` container:

~~~
docker exec -it adhoc-1 /bin/bash
~~~

Once inside, check:

1. That the celebrity has been removed (Dean Koontz):

    - root@adhoc-1:/# `$SPARK_INSTALL/bin/pyspark --driver-class-path /opt/hive/conf --packages org.apache.hudi:hudi-spark-bundle_2.11:0.6.0,org.apache.spark:spark-avro_2.11:2.4.4 --conf spark.sql.hive.convertMetastoreParquet=false`
    - &#62;&#62;&#62; `spark.sql("select title, date, content from hudi_celebrities where title='Dean Koontz'").show(1, False)`<br/><br/>![Alt text](images/delete-celebritie.png)
    - &#62;&#62;&#62; `exit()`

2. That the HUDI library was able to manage everything automatically:

    - root@adhoc-1:/# `/var/hoodie/ws/hudi-cli/hudi-cli.sh`
    - hudi-> `connect --path hdfs://namenode:8020/wiki/hudi_celebrities`    

    A) Verify that a third commit exists:

    - hudi:hudi_celebrities-> `commits show  --desc true`<br/><br/>![Alt text](images/hudi-commits-3.png)
        
    B) Check the commit information

    - hudi:hudi_celebrities-> `commit showfiles --commit 20201013214621`<br/><br/>![Alt text](images/info-commit-3.png)
    <br/><br/>
    > **_NOTE:_**  You can exit the HUDI client by typing: `exit`

### STEP 7 - Stop the cluster

Once the exercise is finished, execute the following script to stop all Docker containers that are simulating the cluster:

~~~
./stop.sh
~~~
