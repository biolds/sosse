FROM debian:bullseye

RUN apt update
RUN apt upgrade -y
RUN apt install -y virtualenv
RUN virtualenv /opt/sosse-doc
ADD requirements.txt /opt/sosse-doc/
RUN . /opt/sosse-doc/bin/activate && pip install -r /opt/sosse-doc/requirements.txt
