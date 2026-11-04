#!/usr/bin/env bash
# Read production's recipes and pantry through the review API (docs/OPERATIONS.md, "The review API"). Only GET, and the
# API only reads. Free: no AI calls. Needs no venv, so it runs from any worktree.
#
#   ./scripts/review_api.sh recipes/382
#   ./scripts/review_api.sh 'pantry?q=yogurt%20butter'
#   ./scripts/review_api.sh questions
#   ./scripts/review_api.sh 'questions?limit=50'
#   ./scripts/review_api.sh pantry-report
#
# The key is REVIEW_API_KEY, else the macOS Keychain item "thelazychef-review-api" (docs/runbooks/ROTATE_SECRETS.md).
# LAZYCHEF_URL points it at another copy of the app (http://127.0.0.1:8000); the default is https://thelazychef.app.
set -euo pipefail

path=${1:?give a path, such as recipes/382 (see the top of this file)}
key=${REVIEW_API_KEY:-$(security find-generic-password -s thelazychef-review-api -w)}
# The key goes in on stdin, so it is not in the process list
printf 'header = "Authorization: Bearer %s"\n' "$key" |
  curl --config - --silent --show-error --fail-with-body --max-time 180 \
    "${LAZYCHEF_URL:-https://thelazychef.app}/api/review/$path"
echo
