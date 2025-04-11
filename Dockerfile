FROM python:3.13-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt && \
  pip install gunicorn

RUN chmod a+x boot.sh

ENV FLASK_APP=main.py
EXPOSE 5000
ENTRYPOINT [ "./boot.sh" ] 