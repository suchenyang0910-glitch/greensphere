set -euo pipefail

APP_DIR="${APP_DIR:-/opt/greensphere}"
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

docker compose up -d --build

