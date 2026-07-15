#!/bin/sh

docker stop microdom-task
sleep 3
docker run --rm -it \
  -e DBUSER=dompi_web \
  -e DBPASSWORD=dompi_web \
  -e DBHOST=192.168.10.32 \
  -e DBNAME=DB_DOMPIWEB \
  --name microdom-task \
  -v /etc/microdom.conf:/app/etc/microdom.conf \
  -v /var/log/microdom:/app/logs \
  -p 8081:8081 microdom-task

