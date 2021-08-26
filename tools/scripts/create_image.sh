#!/bin/sh

cd "$(dirname "$0")/../.."

version=$(awk -F "=" '/version/ {print $2}' setup.cfg | tr -d " ")
podman build --squash-all --tag foreseeti/securicad-parser:"$version" .

