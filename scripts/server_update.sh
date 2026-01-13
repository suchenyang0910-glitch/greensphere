set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_APP_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${APP_DIR:-$DEFAULT_APP_DIR}"
REPO_SSH="${REPO_SSH:-git@github.com:suchenyang0910-glitch/greensphere.git}"
BRANCH="${BRANCH:-main}"

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -d ".git" ]; then
  git clone "$REPO_SSH" .
fi

git fetch --prune origin
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ ! -f ".env" ]; then
  echo "Missing $APP_DIR/.env. Copy from .env.example and fill secrets first." 1>&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. Install on Ubuntu:" 1>&2
  echo "  apt update && apt install -y docker.io docker-compose-plugin   (or docker-compose)" 1>&2
  exit 3
fi

if docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
else
  docker-compose up -d --build
fi
