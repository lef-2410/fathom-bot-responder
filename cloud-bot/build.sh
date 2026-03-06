#!/bin/bash
# Deploys to Fly.io.
# Run from the cloud-bot/ directory.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Deploying to Fly.io..."
fly deploy

echo "Done."
