#!/bin/bash

docker-compose -f ./docker-compose.yml down
docker-compose -f ./docker-compose.yml pull
sleep 5
docker-compose -f ./docker-compose.yml up -d
sleep 15

docker exec -it adhoc-1 /bin/bash /var/hoodie/ws/config/setup_container.sh

echo "Copying all wiki data to HDFS"
docker exec -it namenode /bin/bash hdfs dfs -copyFromLocal /data/wiki /wiki
docker exec -it namenode /bin/bash hdfs dfs -copyFromLocal /data/extra /extra
