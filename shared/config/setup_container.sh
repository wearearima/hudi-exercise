#!/bin/bash

cp /var/hoodie/ws/config/spark-defaults.conf $SPARK_CONF_DIR/.
cp /var/hoodie/ws/config/log4j.properties $SPARK_CONF_DIR/.
cp /var/hoodie/ws/config/hudi-hadoop-mr-bundle-0.6.0.jar /opt/hive/lib/hudi-hadoop-mr-bundle-0.6.0.jar