#!/usr/bin/env bash
# Render build script for JieStore
set -o errexit

pip install -r requirements.txt

cd JieStore
python manage.py collectstatic --noinput
python manage.py migrate --noinput
