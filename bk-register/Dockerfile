# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

#FROM ubuntu:18.04
FROM ubuntu:20.04

EXPOSE 80
RUN apt-get update && apt-get install -y \
  openssh-client \
  python3-pip \
  gunicorn \
  curl      # to access API in script-mode via docker exec...


COPY requirements.txt /
RUN pip3 install -r /requirements.txt

COPY ROOTFS/ /

WORKDIR /opt/sage/beekeeper/register/
#CMD ["python3", "./register.py"]
CMD gunicorn register:app --bind=0.0.0.0:80