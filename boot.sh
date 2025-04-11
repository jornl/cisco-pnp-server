#!/bin/bash
exec gunicorn -b :5000 --access-logfile - --error-logfile - --workers 4 --threads 8 main:app