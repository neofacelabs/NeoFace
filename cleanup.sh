#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# NeoFace — Docker Storage Cleanup Script
# Safely reclaims disk space used by Docker on your Mac.
#
# Usage:
#   ./cleanup.sh          — Smart prune (safe: unused resources only)
#   ./cleanup.sh --deep   — Deep clean (removes volumes too — resets DB)
#   ./cleanup.sh --status — Just show how much space Docker is using
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOLD="\033[1m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; RED="\033[0;31m"; CYAN="\033[0;36m"; RESET="\033[0m"

info()    { echo -e "${GREEN}  ✅ $*${RESET}"; }
step()    { echo -e "\n${BOLD}${CYAN}$*${RESET}"; }
warn()    { echo -e "${YELLOW}  ⚠️  $*${RESET}"; }
danger()  { echo -e "${RED}  🗑️  $*${RESET}"; }

DEEP=false
STATUS_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --deep)   DEEP=true ;;
        --status) STATUS_ONLY=true ;;
    esac
done

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   🧹  NeoFace Docker Cleanup             ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"

# ── Check Docker is running ───────────────────────────────────────────────────
if ! docker info &>/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${RESET}"
    exit 1
fi

# ── Show current usage ────────────────────────────────────────────────────────
step "📊 Current Docker disk usage:"
docker system df

if [ "$STATUS_ONLY" = true ]; then
    echo ""
    info "Status check complete."
    exit 0
fi

# ── Stop NeoFace containers (if running) ──────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

step "🛑 Stopping NeoFace services (if running)..."
docker compose stop 2>/dev/null && info "Services stopped." || true

# ─────────────────────────────────────────────────────────────────────────────
# SMART PRUNE (safe — runs every time)
# Removes:
#   • All stopped containers
#   • All dangling images (untagged layers from old builds)
#   • All unused networks
#   • Build cache older than 24h
# Does NOT remove:
#   • Named volumes (your Postgres data)
#   • Images that are still tagged/referenced
# ─────────────────────────────────────────────────────────────────────────────
step "🧹 Pruning stopped containers..."
REMOVED_CONTAINERS=$(docker container prune -f 2>/dev/null | grep "Total reclaimed" || echo "  Nothing to remove.")
echo "  $REMOVED_CONTAINERS"

step "🧹 Pruning dangling images (leftover build layers)..."
REMOVED_IMAGES=$(docker image prune -f 2>/dev/null | grep "Total reclaimed" || echo "  Nothing to remove.")
echo "  $REMOVED_IMAGES"

step "🧹 Pruning unused networks..."
docker network prune -f 2>/dev/null | grep -v "^$" || true

step "🧹 Pruning build cache (keeping last 24h)..."
docker builder prune -f --filter "until=24h" 2>/dev/null | grep "Total reclaimed" || \
    echo "  Nothing to remove."

# ─────────────────────────────────────────────────────────────────────────────
# DEEP CLEAN (only with --deep flag)
# Removes EVERYTHING including:
#   • All NeoFace images (will need full rebuild on next start)
#   • Named volumes (⚠️  THIS DELETES YOUR LOCAL DATABASE DATA)
#   • All build cache
# ─────────────────────────────────────────────────────────────────────────────
if [ "$DEEP" = true ]; then
    echo ""
    echo -e "${RED}${BOLD}  ⚠️  DEEP CLEAN — This will delete your local database!${RESET}"
    echo -e "${YELLOW}  This removes ALL NeoFace Docker images and volumes.${RESET}"
    echo -e "${YELLOW}  Your source code and .env files are safe.${RESET}"
    echo ""
    read -r -p "  Are you sure? Type 'yes' to confirm: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        warn "Cancelled."
        exit 0
    fi

    step "🗑️  Removing NeoFace containers and volumes..."
    docker compose down --remove-orphans --volumes 2>/dev/null || true

    step "🗑️  Removing NeoFace images..."
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "^neoface" | \
        xargs docker rmi -f 2>/dev/null || true
    # Also remove dangling images from the build
    docker image prune -f 2>/dev/null || true

    step "🗑️  Removing all build cache..."
    docker builder prune -af 2>/dev/null | grep "Total reclaimed" || true

    # Reset the hash cache so start.sh rebuilds everything
    CACHE_DIR="$SCRIPT_DIR/.neoface-cache"
    rm -f "$CACHE_DIR"/*.hash
    danger "Hash cache cleared — next start.sh will rebuild image and npm install."
fi

# ── Final status ──────────────────────────────────────────────────────────────
step "📊 Docker disk usage after cleanup:"
docker system df

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║  ✅ Cleanup complete! Run ./start.sh to restart NeoFace. ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
if [ "$DEEP" = false ]; then
    echo -e "  ${CYAN}Tip: Run ${BOLD}./cleanup.sh --deep${RESET}${CYAN} to also remove images & volumes (resets DB).${RESET}"
fi
echo ""
