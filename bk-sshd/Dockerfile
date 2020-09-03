# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    curl \
    net-tools \
    netcat \
    openssh-server \
    perl \
    python3-flask \
    socat
RUN mkdir -p /var/run/sshd

RUN echo 'root:uZAh0t3Bj4R2Uey*PB5DKMx9GpW%68G9' | chpasswd

# add the registration user (minimal access)
RUN useradd -mr sage_registration
RUN echo 'sage_registration:3WSoOOg3JksknNe$Aizd4oG*7xn*!Fvo' | chpasswd

RUN cp /etc/ssh/sshd_config /etc/ssh/sshd_config.orig
RUN sed -i -e 's/^.\?PermitRootLogin.*/PermitRootLogin prohibit-password/' \
    -e 's/^.\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' \
    -e 's/^.\?PasswordAuthentication.*/PasswordAuthentication no/' \
    -e 's/^.\?UsePAM.*/UsePAM no/' \
    -e 's/^.\?LogLevel.*/LogLevel VERBOSE/' \
    /etc/ssh/sshd_config

RUN echo "HostKey /usr/lib/sage/bk-server/id_rsa_sage_beekeeper" >> /etc/ssh/sshd_config
RUN echo "HostCertificate /usr/lib/sage/bk-server/id_rsa_sage_beekeeper-cert.pub" >> /etc/ssh/sshd_config
RUN echo "TrustedUserCAKeys /usr/lib/sage/certca/sage_beekeeper_ca.pub" >> /etc/ssh/sshd_config
RUN echo "StreamLocalBindUnlink yes" >> /etc/ssh/sshd_config
RUN echo "AllowStreamLocalForwarding remote" >> /etc/ssh/sshd_config

# copy over file system modifications
COPY ROOTFS/ /

EXPOSE 22
CMD ["/opt/sage/beekeeper/run.sh"]
