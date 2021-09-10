FROM python:3.8-slim-buster

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN rm -f requirements.txt
COPY securicad_parser/__main__.py .

ENTRYPOINT python __main__.py
