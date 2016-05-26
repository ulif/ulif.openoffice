FROM ubuntu:14.04.4

MAINTAINER Uli Fouquet <uli@gnufix.de>

RUN apt-get update && apt-get install -y
RUN apt-get install -y python2.7-dev libxml2-dev libxslt1-dev \
                       zlib1g-dev python-virtualenv
# see https://urllib3.readthedocs.org/en/latest/security.html#openssl-pyopenssl
RUN apt-get install -y libssl-dev libffi-dev
RUN apt-get install -y sudo wget git

CMD /bin/bash
