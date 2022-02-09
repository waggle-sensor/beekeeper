# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

# docker build -t waggle/beekeeper-sshd:latest .

# note: this base image should be the same as used in bk-api
FROM ubuntu:20.04
#FROM ubuntu:18.04


ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    net-tools \
    netcat \
    openssh-server \
    perl \
    python3-flask \
    gunicorn \
    socat \
    supervisor
RUN mkdir -p /var/run/sshd /var/log/supervisor

RUN echo 'root:uZAh0t3Bj4R2Uey*PB5DKMx9GpW%68G9' | chpasswd

# add the registration user (minimal access)
RUN useradd -mr sage_registration
RUN echo 'sage_registration:3WSoOOg3JksknNe$Aizd4oG*7xn*!Fvo' | chpasswd

RUN cp /etc/ssh/sshd_config /etc/ssh/sshd_config.orig


RUN echo "Port 22" >> /etc/ssh/sshd_config
RUN echo "Port 2201" >> /etc/ssh/sshd_config


RUN sed -i -e 's/#Port .*/Port 22\nPort 2201/' \
    -e 's/^.\?PermitRootLogin.*/PermitRootLogin prohibit-password/' \
    -e 's/^.\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' \
    -e 's/^.\?PasswordAuthentication.*/PasswordAuthentication no/' \
    -e 's/^.\?UsePAM.*/UsePAM yes/' \
    -e 's/^.\?LogLevel.*/LogLevel VERBOSE/' \
    /etc/ssh/sshd_config

# UsePAM is needed for guest account

RUN echo "HostKey           /usr/lib/waggle/bk-server/beekeeper_server_key" >> /etc/ssh/sshd_config
RUN echo "HostCertificate   /usr/lib/waggle/bk-server/beekeeper_server_key-cert.pub" >> /etc/ssh/sshd_config
RUN echo "TrustedUserCAKeys /usr/lib/waggle/certca/beekeeper_ca_key.pub" >> /etc/ssh/sshd_config

# AuthorizedKeysFile is needed for guest account
RUN echo "AuthorizedKeysFile     .ssh/authorized_keys" >> /etc/ssh/sshd_config
RUN echo "StreamLocalBindUnlink yes" >> /etc/ssh/sshd_config
RUN echo "StreamLocalBindMask 0117" >> /etc/ssh/sshd_config
RUN echo "AllowStreamLocalForwarding remote" >> /etc/ssh/sshd_config
RUN echo "ClientAliveInterval 60" >> /etc/ssh/sshd_config


# admin via 2201 , not 22
RUN echo "Match LocalPort 22" >> /etc/ssh/sshd_config
RUN echo "    DenyUsers root" >> /etc/ssh/sshd_config


# copy over file system modifications
COPY ROOTFS/ /
COPY /entrypoint.sh /
COPY bin/* /usr/local/bin/

RUN useradd --shell /bin/bash -m waggle

EXPOSE 22
EXPOSE 2201
#CMD ["/usr/bin/supervisord"]
#CMD ["/entrypoint.sh"]
ENTRYPOINT ["/entrypoint.sh"]
#CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
