set -euo pipefail

REPO_SSH="${REPO_SSH:-git@github.com:suchenyang0910-glitch/greensphere.git}"
APP_DIR="${APP_DIR:-/opt/greensphere}"
BRANCH="${BRANCH:-main}"

apt update
apt install -y git ca-certificates curl docker.io
if ! apt install -y docker-compose-plugin; then
  apt install -y docker-compose
fi
systemctl enable --now docker

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -d ".git" ]; then
  git clone "$REPO_SSH" .
fi

git fetch --prune origin
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created $APP_DIR/.env from .env.example. Please edit secrets then rerun:" 1>&2
  echo "  nano $APP_DIR/.env" 1>&2
  echo "  docker compose up -d --build  (or: docker-compose up -d --build)" 1>&2
  exit 2
fi

if docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
  docker compose ps
else
  docker-compose up -d --build
  docker-compose ps
fi
