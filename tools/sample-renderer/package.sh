#!/bin/sh
# Build tone-<version>.tar.gz with plugin.json at its top level.
cd "$(dirname "$0")"
version=$(python3 -c 'import json; print(json.load(open("plugin.json"))["version"])')
tar -czf "tone-$version.tar.gz" plugin.json tone.py
echo "tone-$version.tar.gz"
