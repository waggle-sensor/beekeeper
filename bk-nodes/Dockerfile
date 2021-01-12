
# docker build -t beekeeper/bk-nodes .
# docker run -ti -p 5000:5000 -v `pwd`:/usr/src/app beekeeper/bk-nodes
FROM python:3.9-alpine

WORKDIR /usr/src/app

# required for python library mysqlclient
RUN apk add  mariadb-connector-c-dev gcc musl-dev

# required for wsgi
RUN apk add linux-headers

RUN /usr/local/bin/python -m pip install --upgrade pip

COPY  . /usr/src/app
RUN pip install -r requirements.txt

#CMD ./bk-nodes.py
CMD gunicorn bk-nodes:app --bind=0.0.0.0:5000

