FROM python:3.12.1-alpine3.19

COPY requirements.txt /

RUN apk add --no-cache libffi-dev openssl-dev tzdata && \
    apk add --no-cache --wait 10 --virtual .pynacl_deps build-base gcc musl-dev python3-dev libffi-dev cargo  && \
    pip3 install -r /requirements.txt && \
    apk del .pynacl_deps

COPY . /app
WORKDIR /app

CMD ["python3", "/app/sbb.py"]
