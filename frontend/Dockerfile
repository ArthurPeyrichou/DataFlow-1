FROM node:latest

RUN mkdir /app
WORKDIR /app

ADD . /app

RUN npm install

# Modify config

CMD node release.js