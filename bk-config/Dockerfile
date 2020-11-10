#FROM ubuntu:18.04
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y openssh-client

COPY ./bin/*.sh /usr/local/bin/


WORKDIR /usr/lib/sage/