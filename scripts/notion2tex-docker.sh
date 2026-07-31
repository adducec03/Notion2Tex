#!/usr/bin/env bash
# Run notion2tex via Docker against a file anywhere on disk, with no need
# to clone this repo. Output is written next to the input file, exactly
# like running notion2tex locally would.
#
# Usage:
#   notion2tex-docker.sh /path/to/Export.zip [extra notion2tex args...]
#   notion2tex-docker.sh /path/to/Export.zip --dark
#   notion2tex-docker.sh /path/to/Page.html --tex-only
#   notion2tex-docker.sh --config     # interactive menu, saves a profile
#   notion2tex-docker.sh --check
#
# Always pulls the latest ":latest" from the registry first (every push to
# main republishes it), so you never run a stale cached copy. Pin a version
# instead with:
#   NOTION2TEX_IMAGE=ghcr.io/adducec03/notion2tex:v1.2.3 notion2tex-docker.sh Export.zip

set -euo pipefail

IMAGE="${NOTION2TEX_IMAGE:-ghcr.io/adducec03/notion2tex:latest}"

# --config's saved profiles need to survive past a single `docker run
# --rm` (the container's own filesystem is thrown away on exit) -- mount
# the same host directory a local (non-Docker) install would use, onto
# the container path the Dockerfile exports as XDG_CONFIG_HOME.
CONFIG_HOST_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/notion2tex"
mkdir -p "$CONFIG_HOST_DIR"

# --config's arrow-key menu (and any other interactive prompt) needs a
# real terminal to render -- added only when stdin/stdout actually are
# one, so this still works fine in non-interactive/piped contexts. Plain
# string (not an array): always either empty or the single token "-it",
# so unquoted expansion below is safe and avoids "unbound variable"
# issues some bash versions raise for an empty array under `set -u`.
TTY_FLAGS=""
if [ -t 0 ] && [ -t 1 ]; then
  TTY_FLAGS="-it"
fi

# Standalone actions that take no input file: mount the current directory
# instead of a file's parent (e.g. so a plain `notion2tex-docker.sh
# Export.zip` run afterward has the same working directory feel).
case "${1:-}" in
  --config | --check | --version | --help | -h | "")
    exec docker run --rm $TTY_FLAGS --pull always \
      -v "$(pwd):/data" \
      -v "${CONFIG_HOST_DIR}:/config/notion2tex" \
      -w /data \
      "$IMAGE" \
      "$@"
    ;;
esac

INPUT_PATH=$1
shift

if [ ! -f "$INPUT_PATH" ]; then
  echo "error: file not found: $INPUT_PATH" >&2
  exit 1
fi

# Resolve to an absolute path so the mount works regardless of cwd.
INPUT_DIR=$(cd "$(dirname "$INPUT_PATH")" && pwd)
INPUT_NAME=$(basename "$INPUT_PATH")

docker run --rm --pull always \
  -v "${INPUT_DIR}:/data" \
  -v "${CONFIG_HOST_DIR}:/config/notion2tex" \
  -w /data \
  "$IMAGE" \
  "$INPUT_NAME" "$@"
