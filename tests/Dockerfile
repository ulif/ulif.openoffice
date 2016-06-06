FROM ubuntu:14.04.4

MAINTAINER Uli Fouquet <uli@gnufix.de>

RUN apt-get update && apt-get install -y
RUN apt-get install -y python2.7-dev libxml2-dev libxslt1-dev \
                       zlib1g-dev python-virtualenv python3-dev
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

# install a py3 virtualenv
RUN virtualenv -p /usr/bin/python3.4 py34
RUN /home/deploy/py34/bin/pip install --upgrade pip

# init dev env (py2.7)
WORKDIR /home/deploy/ulif.openoffice
RUN /home/deploy/py27/bin/python setup.py dev

# init dev env (py3.4)
WORKDIR /home/deploy/ulif.openoffice
RUN /home/deploy/py34/bin/python setup.py dev

CMD /bin/bash
