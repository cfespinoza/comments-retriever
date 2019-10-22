FROM python:3.6-alpine

RUN mkdir -p /opt/cr
COPY target/* /opt/cr/bin/

RUN pip install /opt/cr/bin/scraper.tar.gz
RUN rm /opt/cr/bin/scraper.tar.gz

ENTRYPOINT ["/opt/cr/bin/scrapper.sh"]