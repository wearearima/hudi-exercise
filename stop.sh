#!/bin/bash

SCRIPT_PATH=$(cd `dirname $0`; pwd)
# set up root directory
WS_ROOT=`dirname $SCRIPT_PATH`
# shut down cluster
HUDI_WS=${WS_ROOT} docker-compose -f ${SCRIPT_PATH}/docker-compose.yml down
