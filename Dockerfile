# Run ulif.openoffice as a converting server on port 8008.
# 
# build with something like:
#   docker build [--no-cache] -t ulif/openoffice-xmlrpc:1.1 .
# run with something like:
#   docker run --net=host -d -p 8008 ulif/openoffice-xmlrpc

FROM ubuntu:14.04.4

MAINTAINER Uli Fouquet <uli@gnufix.de>

RUN apt-get update && apt-get install -y
RUN apt-get install -y python2.7-dev libxml2-dev libxslt1-dev \
                       zlib1g-dev python-virtualenv
# see https://urllib3.readthedocs.org/en/latest/security.html#openssl-pyopenssl
RUN apt-get install -y libssl-dev libffi-dev
RUN apt-get install -y sudo wget git
RUN apt-get install -y unoconv tidy

# add user `deploy`
RUN useradd -ms /bin/bash deploy
# set password of user `deploy` and add to group 'sudo'
RUN echo deploy:deploy | chpasswd && adduser deploy sudo

# become user `deploy`
WORKDIR /home/deploy
USER deploy
ENV HOME /home/deploy

# get sources
RUN git clone https://github.com/ulif/ulif.openoffice

# install a py2 virtualenv
RUN virtualenv -p /usr/bin/python2.7 py27
RUN /home/deploy/py27/bin/pip install --upgrade pip

# init dev env (py2.7)
WORKDIR /home/deploy/ulif.openoffice
RUN /home/deploy/py27/bin/python setup.py dev

# install paste.script (contains a WSGI server)
RUN /home/deploy/py27/bin/pip install pastescript

EXPOSE 8008
CMD /home/deploy/py27/bin/paster serve /home/deploy/ulif.openoffice/xmlrpc.ini

