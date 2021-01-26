
FROM ubuntu:20.04
#FROM ubuntu:18.04
#FROM alpine:3.12 
# alpine seems to make problems, registration is not recognized


# jq and curl are need for unit tests
RUN apt-get update && apt-get install -y openssh-client jq curl
#RUN apk update && apk add openssh-client bash

COPY ./bin/*.sh /usr/local/bin/


WORKDIR /usr/lib/sage/