#!/usr/bin/env bash
# One-time Contabo VPS bootstrap for Talk2Record.
# Run as a user with sudo. Re-runnable; only does missing pieces.
#
# Usage:
#   sudo ./bootstrap.sh
#
# After this script:
#   - Docker + compose plugin installed
#   - UFW firewall enabled (22, 80, 443)
#   - /opt/talk2record directory layout created
#   - External Docker networks talk2record_prod / talk2record_staging created
#   - "deploy" user added to docker group
#
# You still need to:
#   - Place env files under /opt/talk2record/envs/{prod,staging}/
#   - git clone the repo into /opt/talk2record/repo
#   - Start Traefik: docker compose -f deploy/traefik/docker-compose.yml -p talk2record-edge up -d

set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/talk2record/repo}"
BASE_DIR="/opt/talk2record"
DEPLOY_USER="${DEPLOY_USER:-deploy}"

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Re-running with sudo..."
    exec sudo -E bash "$0" "$@"
  fi
}

install_packages() {
  apt-get update -y
  apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release git ufw fail2ban
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    echo "Docker already installed: $(docker --version)"
    return
  fi
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

ensure_deploy_user() {
  if id "$DEPLOY_USER" >/dev/null 2>&1; then
    echo "User '$DEPLOY_USER' already exists"
  else
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
  fi
  usermod -aG docker "$DEPLOY_USER"
  install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 0700 "/home/$DEPLOY_USER/.ssh"
  touch "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chmod 0600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
  echo "Append the GitHub Actions deploy public key to /home/$DEPLOY_USER/.ssh/authorized_keys"
}

setup_firewall() {
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  if ! ufw status | grep -q "Status: active"; then
    echo "y" | ufw enable
  fi
}

create_directories() {
  install -d -m 0755 "$BASE_DIR"
  install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$BASE_DIR/envs"
  install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$BASE_DIR/envs/prod"
  install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$BASE_DIR/envs/staging"
  install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$BASE_DIR/state"
  chown -R "$DEPLOY_USER:$DEPLOY_USER" "$BASE_DIR"
}

create_networks() {
  for net in talk2record_prod talk2record_staging; do
    if ! docker network inspect "$net" >/dev/null 2>&1; then
      docker network create "$net"
    fi
  done
}

# Monorepo deploy uses a single git root at REPO_DIR. A nested backend/.git (or
# frontend/.git) usually means an old per-service clone was copied in; remove it
# so deploy.sh git fetch/checkout at the repo root is authoritative.
remove_nested_git_repos() {
  if [[ ! -d "$REPO_DIR" ]]; then
    return
  fi
  for sub in backend frontend; do
    if [[ -d "$REPO_DIR/$sub/.git" ]]; then
      echo "Removing nested git repo at $REPO_DIR/$sub/.git"
      rm -rf "$REPO_DIR/$sub/.git"
    fi
  done
}

main() {
  require_root "$@"
  install_packages
  install_docker
  ensure_deploy_user
  setup_firewall
  create_directories
  create_networks
  remove_nested_git_repos
  cat <<EOF

Bootstrap complete.

Next steps:
  1. Add the GitHub Actions deploy public key to:
     /home/$DEPLOY_USER/.ssh/authorized_keys
  2. As '$DEPLOY_USER', clone the repo:
     git clone <your-repo-url> $REPO_DIR
  3. Copy deploy/env/*.example files into:
     $BASE_DIR/envs/prod/  and  $BASE_DIR/envs/staging/
     then fill in secrets.
  4. Start Traefik:
     cd $REPO_DIR/deploy/traefik
     docker compose -p talk2record-edge up -d
EOF
}

main "$@"
