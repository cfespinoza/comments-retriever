FROM python:3.6-alpine

RUN apk add --no-cache --virtual .build-deps gcc libc-dev libxslt-dev && \
    apk add --no-cache libxslt

RUN mkdir -p /opt/cr
COPY target/* /opt/cr/bin/

RUN pip install --no-cache-dir -r /opt/cr/bin/requirements.txt && \
    pip install --no-cache-dir /opt/cr/bin/scraper.tar.gz

RUN rm /opt/cr/bin/scraper.tar.gz

ENTRYPOINT ["/opt/cr/bin/scrapper.sh"]