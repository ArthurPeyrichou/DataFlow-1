FROM python:latest

ARG HTTP_PROXY
ARG HTTPS_PROXY

RUN mkdir /app

WORKDIR /app
ADD . /app/

RUN export HTTP_PROXY=$HTTP_PROXY
RUN export HTTPS_PROXY=$HTTPS_PROXY

RUN pip install -r requirements.txt

EXPOSE 5001

CMD python WSMain.py
