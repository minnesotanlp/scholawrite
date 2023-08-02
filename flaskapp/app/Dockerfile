FROM python:3.6.8-alpine3.9

LABEL MAINTAINER="Ryan Koo kooryan03@gmail.com"

ENV GROUP_ID=1000 \
    USER_ID=1000

WORKDIR /var/www/

ENV PYTHONUNBUFFERED=0

ADD . /var/www/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN python -m nltk.downloader punkt
RUN pip install gunicorn

RUN addgroup -g $GROUP_ID www
RUN adduser -D -u $USER_ID -G www www -s /bin/sh

USER www

EXPOSE 5000

CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi"]
