#!/usr/bin/env bash
# Run notion2tex via Docker against a file anywhere on disk, with no need
# to clone this repo. Output is written next to the input file, exactly
# like running notion2tex locally would.
#
# Usage:
#   notion2tex-docker.sh /path/to/Export.zip [extra notion2tex args...]
#   notion2tex-docker.sh /path/to/Export.zip --dark
#   notion2tex-docker.sh /path/to/Page.html --tex-only
#
# The image is pulled automatically on first use. Override it with:
#   NOTION2TEX_IMAGE=ghcr.io/adducec03/notion2tex:v1.2.3 notion2tex-docker.sh Export.zip

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $(basename "$0") /path/to/Export.zip [extra notion2tex args...]" >&2
  exit 1
fi

INPUT_PATH=$1
shift

if [ ! -f "$INPUT_PATH" ]; then
  echo "error: file not found: $INPUT_PATH" >&2
  exit 1
fi

IMAGE="${NOTION2TEX_IMAGE:-ghcr.io/adducec03/notion2tex:latest}"

# Resolve to an absolute path so the mount works regardless of cwd.
INPUT_DIR=$(cd "$(dirname "$INPUT_PATH")" && pwd)
INPUT_NAME=$(basename "$INPUT_PATH")

docker run --rm \
  -v "${INPUT_DIR}:/data" \
  -w /data \
  "$IMAGE" \
  "$INPUT_NAME" "$@"
