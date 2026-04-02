#!/bin/sh
set -e

# Ensure directories exist and are writable by the app user
mkdir -p /app/knowledge/erd
mkdir -p /app/knowledge/diagrams

# Fix permissions (may fail if volume is read-only, but that's ok for initial dirs)
chown -R app:app /app/knowledge 2>/dev/null || true

# Run the actual command
exec "$@"
