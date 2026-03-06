#!/bin/bash
# Prepares the build context and deploys to Fly.io.
# Run from the cloud-bot/ directory.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Copy the email style guide into the build context
echo "Copying email style guide..."
cp "../.claude/email-style.md" ./email-style.md

echo "Deploying to Fly.io..."
fly deploy

# Clean up
rm -f ./email-style.md
echo "Done."
