#!/bin/bash
# Health check script for backend service

echo "Checking backend health..."

# Check if API is responding
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$HTTP_CODE" == "200" ]; then
    echo "✓ Backend health check passed (HTTP $HTTP_CODE)"
    exit 0
else
    echo "✗ Backend health check failed (HTTP $HTTP_CODE)"
    exit 1
fi
