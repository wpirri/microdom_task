#!/bin/sh

echo "Stop microdom-task..."
docker stop microdom-task
sleep 3
echo "Remove microdom-task..."
docker rm microdom-task
sleep 3
docker run -it \
  -d --restart unless-stopped \
  -e DBUSER=dompi_web \
  -e DBPASSWORD=dompi_web \
  -e DBHOST=192.168.10.32 \
  -e DBNAME=DB_DOMPIWEB \
  --name microdom-task \
  -v /etc/microdom.conf:/app/etc/microdom.conf \
  -v /var/log/microdom:/app/logs \
  -p 8081:8081 microdom-task

