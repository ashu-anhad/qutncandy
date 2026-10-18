#!/usr/bin/env bash
# One-time server preparation (Ubuntu on Oracle Cloud). Run as root via: ./deploy.sh setup
set -euo pipefail
APP_USER="${SUDO_USER:-ubuntu}"

echo "== Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
usermod -aG docker "$APP_USER"

echo "== Firewall: open 80/443 (Oracle's Ubuntu image rejects them by default)"
open_port() {  # proto port
  iptables -C INPUT -p "$1" --dport "$2" -j ACCEPT 2>/dev/null && return
  line=$(iptables -L INPUT --line-numbers | awk '/REJECT/ {print $1; exit}')
  if [ -n "$line" ]; then iptables -I INPUT "$line" -p "$1" --dport "$2" -j ACCEPT
  else iptables -A INPUT -p "$1" --dport "$2" -j ACCEPT; fi
}
open_port tcp 80; open_port tcp 443; open_port udp 443
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent rsync unattended-upgrades >/dev/null
netfilter-persistent save

echo "== Swap (2 GB) so builds don't run out of memory"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== App folder"
mkdir -p /opt/qutncandy/backups
chown -R "$APP_USER": /opt/qutncandy

echo "Server ready."
