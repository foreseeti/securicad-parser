FROM python:3.8-alpine

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY securicad_parser/__main__.py .

ENTRYPOINT python __main__.py
