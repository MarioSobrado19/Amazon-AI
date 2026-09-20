#!/bin/sh
set -eu
python -m compliance.ebay_deletion_worker &
exec gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 4 --access-logfile /dev/null --error-logfile - compliance.ebay_deletion_app:app
