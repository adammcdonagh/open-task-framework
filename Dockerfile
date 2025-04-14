FROM python:3.13-alpine
RUN pip install opentaskpy
RUN mkdir /app /logs && ln -s /logs /app/logs
WORKDIR /app

ENTRYPOINT [ "task-run" ]
