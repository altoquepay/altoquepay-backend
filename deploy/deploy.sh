#!/bin/bash
# Forced command of the GitHub Actions deploy key: it deploys one published version and nothing else.
# The Deploy workflow sends the version as the SSH command, and its user and token on stdin.
set -euo pipefail

version="${SSH_ORIGINAL_COMMAND:-}"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Expected a version such as 0.7.1, got: $version" >&2
  exit 64
fi
read -r registry_user
read -r token

cd "$(dirname "$0")"
files=(compose.yml Caddyfile deploy.sh)
trap 'docker logout ghcr.io >/dev/null 2>&1 || true; rm -f "${files[@]/%/.new}"' EXIT

# The deploy files of the release itself, so the server always matches the tag it runs.
for file in "${files[@]}"; do
  curl -fsS -o "$file.new" -H "Authorization: Bearer $token" -H "Accept: application/vnd.github.raw" \
    "https://api.github.com/repos/altoquepay/altoquepay-backend/contents/deploy/$file?ref=v$version"
done

echo "$token" | docker login ghcr.io -u "$registry_user" --password-stdin
# Pulls before changing anything, so a version without an image leaves the server as it was.
API_VERSION="$version" docker compose -f compose.yml.new pull api

caddyfile_changed=$(cmp -s Caddyfile Caddyfile.new || echo yes)
for file in "${files[@]}"; do mv "$file.new" "$file"; done
chmod +x deploy.sh
sed -i '/^API_VERSION=/d' .env
echo "API_VERSION=$version" >> .env

docker compose up -d --no-build
# A container keeps seeing the old file after its bind-mounted file is replaced, until it restarts.
if [[ -n "$caddyfile_changed" ]]; then docker compose restart caddy; fi
docker image prune -f >/dev/null
echo "Deployed $version"
