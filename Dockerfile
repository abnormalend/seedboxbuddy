FROM python:2.7-alpine

COPY requirements.txt /

RUN apk add --no-cache libffi-dev openssl-dev && \
    apk add --no-cache --wait 10 --virtual .pynacl_deps build-base python2-dev  && \
    pip install -r /requirements.txt && \
    apk del .pynacl_deps

COPY ./* /
WORKDIR /

CMD ["python", "sbb.py"]
