FROM python:3.7-alpine

COPY requirements.txt /

RUN apk add --no-cache libffi-dev openssl-dev tzdata && \
    apk add --no-cache --wait 10 --virtual .pynacl_deps build-base python3-dev  && \
    pip3 install -r /requirements.txt && \
    apk del .pynacl_deps

COPY . /app
WORKDIR /app

CMD ["python3", "/app/sbb.py"]
