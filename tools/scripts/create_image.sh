#!/bin/sh

set -eu

cd "$(dirname "$0")/../.."

version=$(python3 -c 'from configparser import ConfigParser; config = ConfigParser(); config.read("setup.cfg"); print(config["metadata"]["version"])')
podman build --squash-all --tag foreseeti/securicad-parser:"$version" .

