
#FROM ubuntu:20.04
FROM alpine:3.12

#RUN apt-get update && apt-get install -y openssh-client
RUN apk update && apk add openssh-client bash

COPY ./bin/*.sh /usr/local/bin/


WORKDIR /usr/lib/sage/