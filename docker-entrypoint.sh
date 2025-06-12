#!/bin/bash

echo "Starting nginx..."
service nginx start

echo "Starting backend service..."
python -m uvicorn backend.asgi:application \
    --host 0.0.0.0 \
    --port 8900 \
    --workers 1