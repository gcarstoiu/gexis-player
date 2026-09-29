#!/bin/sh
# Build hello-<version>.tar.gz with plugin.json at its top level (ADR-0106).
cd "$(dirname "$0")"
version=$(python3 -c 'import json; print(json.load(open("plugin.json"))["version"])')
tar -czf "hello-$version.tar.gz" plugin.json hello.py
echo "hello-$version.tar.gz"
