#!/usr/bin/env bash
# Atajo para macOS y Linux. El script real es dev.mjs (Node), que funciona también en Windows: node dev.mjs
exec node "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dev.mjs" "$@"
