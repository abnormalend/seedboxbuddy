FROM python:3.12.1-alpine3.19

COPY requirements.txt /

RUN buildDeps='.pynacl_deps gcc musl-dev cargo' && \
    apk add --no-cache libffi-dev openssl-dev tzdata && \
    apk add --no-cache --wait 10 --virtual $buildDeps build-base python3-dev libffi-dev  && \
    pip3 install -r /requirements.txt && \
    apk del $buildDeps

COPY . /app
WORKDIR /app

CMD ["python3", "/app/sbb.py"]
