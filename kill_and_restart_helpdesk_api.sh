#!/bin/bash

docker inspect -f '{{.State.Pid}}' docker-frappe-1 | xargs kill -9
docker rm -f docker-frappe-1
cd docker
docker compose up -d
