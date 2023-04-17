FROM python:3.10
RUN pip install opentaskpy
RUN mkdir /app /logs && ln -s /logs /app/logs
WORKDIR /app
