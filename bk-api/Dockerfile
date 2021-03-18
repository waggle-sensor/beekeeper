
# docker build -t beekeeper/bk-api .
# docker run -ti -p 5000:5000 -v `pwd`:/usr/src/app beekeeper/bk-api
#FROM python:3.9-alpine

# note: this base image should be the same as used in bk-sshd
FROM ubuntu:20.04

WORKDIR /usr/src/app

# required for python library mysqlclient
#RUN apk add  mariadb-connector-c-dev gcc musl-dev curl

ARG DEBIAN_FRONTEND noninteractive

# required for wsgi
#RUN apk add linux-headers
RUN apt-get update &&  apt-get install -y python3-pip gunicorn libmysqlclient-dev curl
#RUN pip3
#RUN /usr/local/bin/python -m pip install --upgrade pip

COPY  . /usr/src/app
RUN pip3 install -r requirements.txt

#CMD ./bk_api.py
CMD gunicorn bk_api:app --bind=0.0.0.0:5000

