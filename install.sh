#!/bin/bash
# This script installs the samftp-cli application and its dependencies.

set -e

echo "Checking for Rye..."
if ! command -v rye &> /dev/null
then
    echo "Rye is not installed. Please install it from https://rye-up.com/ and try again."
    exit 1
fi

echo "Syncing project dependencies..."
rye sync

echo "Installing the samftp command..."
rye install --force samftp-cli --path .

echo ""
echo "✅ Installation successful!"
echo "You can now run the 'samftp' command from anywhere in your terminal."
echo "Please ensure '~/.rye/shims' is in your shell's PATH." 