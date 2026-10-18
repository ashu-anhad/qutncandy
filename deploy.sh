#!/usr/bin/env bash
# Deploy QutnCandy to the server from this Mac.
#
#   ./deploy.sh setup                  one-time: Docker, firewall, swap on the server
#   ./deploy.sh                        deploy the current code (rollback: git checkout <commit> && ./deploy.sh)
#   ./deploy.sh admin EMAIL "NAME"     create an admin (asks for the password)
#   ./deploy.sh seed                   load the sample catalog
#   ./deploy.sh status | logs [svc]    what's running / follow logs
#   ./deploy.sh backups                download the latest backups to ./backups
#
# Server details live in deploy/.env.server (not committed):
#   SERVER=ubuntu@<server-ip>
#   SSH_KEY=~/.ssh/<private-key-file>
set -euo pipefail
cd "$(dirname "$0")"

CONFIG=deploy/.env.server
if [ ! -f "$CONFIG" ]; then
  printf 'SERVER=ubuntu@SERVER_IP\nSSH_KEY=~/.ssh/oracle-qutncandy.key\n' > "$CONFIG"
  echo "Created $CONFIG — fill in the server IP and SSH key path, then run again."; exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG"
SSH_KEY="${SSH_KEY/#\~/$HOME}"
SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)
APP=/opt/qutncandy
COMPOSE="docker compose --env-file backend/.env.production -f docker-compose.prod.yml"
remote() { ssh "${SSH_OPTS[@]}" "$SERVER" "$@"; }

ensure_env() {
  local env=backend/.env.production
  [ -f "$env" ] && return
  echo "== Creating $env with fresh secrets (kept on this Mac and the server only)"
  python3 - "$env" <<'PY'
import re, secrets, sys
out = sys.argv[1]
text = open("backend/.env.production.example").read()
text = text.replace("JWT_SECRET=\n", f"JWT_SECRET={secrets.token_urlsafe(48)}\n")
text = text.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={secrets.token_urlsafe(24)}\n")
try:  # reuse the (public) Google client ID from local dev
    m = re.search(r"^GOOGLE_CLIENT_ID=(.+)$", open("backend/.env").read(), re.M)
    if m: text = text.replace("GOOGLE_CLIENT_ID=\n", f"GOOGLE_CLIENT_ID={m.group(1).strip()}\n")
except FileNotFoundError:
    pass
open(out, "w").write(text)
PY
  chmod 600 "$env"
}

case "${1:-deploy}" in
  setup)
    scp "${SSH_OPTS[@]}" deploy/server-setup.sh "$SERVER:/tmp/server-setup.sh"
    remote "sudo bash /tmp/server-setup.sh"
    ;;
  deploy)
    ensure_env
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      echo "Note: you have uncommitted changes; they will be deployed too."
    fi
    git rev-parse --short HEAD > REVISION 2>/dev/null || echo unknown > REVISION
    echo "== Copying code ($(cat REVISION)) to $SERVER"
    rsync -az --delete -e "ssh ${SSH_OPTS[*]}" \
      --exclude .git --exclude node_modules --exclude .venv --exclude dist --exclude __pycache__ \
      --exclude .pytest_cache --exclude backend/media --exclude backups --exclude backend/.env \
      --exclude deploy/.env.server --exclude brand \
      ./ "$SERVER:$APP/"
    rm -f REVISION
    echo "== Building and starting"
    remote "cd $APP && $COMPOSE up -d --build --remove-orphans && docker image prune -f >/dev/null && $COMPOSE ps"
    domain=$(grep -E '^DOMAIN=' backend/.env.production | cut -d= -f2)
    echo "Done. Open https://$domain"
    ;;
  admin)
    [ $# -ge 3 ] || { echo 'Usage: ./deploy.sh admin EMAIL "NAME"'; exit 1; }
    ssh -t "${SSH_OPTS[@]}" "$SERVER" "cd $APP && $COMPOSE exec backend python -m app.cli create-admin --email '$2' --name '$3'"
    ;;
  seed)    remote "cd $APP && $COMPOSE exec -T backend python -m app.cli seed" ;;
  status)  remote "cd $APP && $COMPOSE ps && cat REVISION 2>/dev/null" ;;
  logs)    ssh -t "${SSH_OPTS[@]}" "$SERVER" "cd $APP && $COMPOSE logs -f --tail=100 ${2:-}" ;;
  backups)
    mkdir -p backups
    rsync -az -e "ssh ${SSH_OPTS[*]}" "$SERVER:$APP/backups/" backups/
    ls -lh backups | tail -5
    ;;
  *) sed -n '2,15p' "$0"; exit 1 ;;
esac
