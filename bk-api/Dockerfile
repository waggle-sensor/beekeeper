
# docker build -t waggle/beekeeper-api .
# docker run -ti -p 5000:5000 -v `pwd`:/usr/src/app waggle/beekeeper-api


# note: this base image should be the same as used in bk-sshd
FROM ubuntu:20.04

WORKDIR /usr/src/app

# required for python library mysqlclient
#RUN apk add  mariadb-connector-c-dev gcc musl-dev curl

ARG DEBIAN_FRONTEND=noninteractive

# required for wsgi
#RUN apk add linux-headers
RUN apt-get update &&  apt-get install -y python3-pip gunicorn libmysqlclient-dev openssh-client curl psmisc
#RUN pip3
#RUN /usr/local/bin/python -m pip install --upgrade pip

# copy requirements.txt explicitly first: https://stackoverflow.com/a/34399661/2069181
COPY requirements.txt /usr/src/app/requirements.txt
RUN pip3 install -r requirements.txt

COPY  . /usr/src/app


#CMD ./bk_api.py
CMD gunicorn bk_api:app --timeout=120 --bind=0.0.0.0:5000

