#!/bin/sh

docker build -t microdom-task:latest .
docker tag microdom-task:latest ghcr.io/wpirri/microdom-task:latest
docker push ghcr.io/wpirri/microdom-task:latest

