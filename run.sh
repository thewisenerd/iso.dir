#!/usr/bin/env bash

if [ ! -d '.venv' ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r requirements.txt
else
    source .venv/bin/activate
fi

gunicorn --bind=127.0.0.1:8003 \
  --workers=3 --threads=2 \
  --access-logfile '-' --log-file '-' \
   run:app
