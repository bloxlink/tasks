FROM python:3.6.5

WORKDIR /usr/src/partners

ADD . /usr/src/partners

RUN apt-get update

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt
RUN apt install dumb-init


ENTRYPOINT ["dumb-init", "-v", "--", "python3", "partners.py"]
