#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# NeoFace — Local Development Startup Script (Storage-Efficient)
#
# What this script does differently:
#   ✅ Only rebuilds Docker image when source files actually changed
#   ✅ Only runs npm install when package.json/package-lock.json changed
#   ✅ Auto-prunes dangling images, dead containers, unused networks on start
#   ✅ Never accumulates stale Docker layers on your Mac
#
# Usage:
#   ./start.sh                  — Normal start (skip rebuilds if nothing changed)
#   ./start.sh --force-rebuild  — Force full Docker rebuild + npm install
#   ./start.sh --clean          — Deep clean all Docker data, then start fresh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
BOLD="\033[1m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; RED="\033[0;31m"; CYAN="\033[0;36m"; RESET="\033[0m"

info()    { echo -e "${BOLD}${GREEN}  ✅ $*${RESET}"; }
step()    { echo -e "\n${BOLD}${CYAN}$*${RESET}"; }
warn()    { echo -e "${YELLOW}  ⚠️  $*${RESET}"; }
cleanup_msg() { echo -e "${RED}  🧹 $*${RESET}"; }

# ── Flags ──────────────────────────────────────────────────────────────────────
FORCE_REBUILD=false
DEEP_CLEAN=false
for arg in "$@"; do
    case "$arg" in
        --force-rebuild) FORCE_REBUILD=true ;;
        --clean)         DEEP_CLEAN=true ;;
    esac
done

# ── Script directory (always run relative to project root) ─────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Cache directory for storing change hashes ─────────────────────────────────
CACHE_DIR="$SCRIPT_DIR/.neoface-cache"
mkdir -p "$CACHE_DIR"

# Copy backend/.env to root .env so docker compose can read it
if [ -f "backend/.env" ]; then
    cp backend/.env .env
fi

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   🚀  NeoFace Local Environment          ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# CLEANUP on CTRL+C / SIGTERM
# ─────────────────────────────────────────────────────────────────────────────
FRONTEND_PID=""
cleanup() {
    echo ""
    step "🛑 Shutting down services..."
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "   Stopping frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "   Stopping Docker services (containers preserved for fast restart)..."
    docker compose stop 2>/dev/null || true
    echo -e "\n${BOLD}👋 All services stopped. Run ./start.sh to resume.${RESET}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0: DEEP CLEAN (only when --clean flag is passed)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$DEEP_CLEAN" = true ]; then
    step "🗑️  0. Deep clean — removing all NeoFace Docker data..."
    docker compose down --remove-orphans --volumes 2>/dev/null || true
    # Remove project images
    docker images --format "{{.Repository}}:{{.Tag}}" | grep "neoface" | \
        xargs docker rmi -f 2>/dev/null || true
    # System-wide prune (safe: only removes truly unused resources)
    docker system prune -f --volumes 2>/dev/null || true
    # Remove cache so everything rebuilds fresh
    rm -f "$CACHE_DIR"/*.hash
    info "Deep clean complete. Starting fresh..."
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: PRUNE DANGLING/UNUSED DOCKER RESOURCES (always, keeps Mac clean)
# ─────────────────────────────────────────────────────────────────────────────
step "🧹 1. Pruning unused Docker resources (keeps your Mac storage clean)..."

# Count dangling images before pruning
DANGLING_COUNT=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l | tr -d ' ')
if [ "$DANGLING_COUNT" -gt "0" ]; then
    cleanup_msg "Removing $DANGLING_COUNT dangling image(s)..."
    docker image prune -f 2>/dev/null || true
fi

# Remove stopped/dead containers (not running ones)
DEAD_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "status=dead" \
    --filter "status=created" -q 2>/dev/null | wc -l | tr -d ' ')
if [ "$DEAD_CONTAINERS" -gt "0" ]; then
    cleanup_msg "Removing $DEAD_CONTAINERS stopped container(s)..."
    docker container prune -f 2>/dev/null || true
fi

# Remove unused networks (not connected to any container)
docker network prune -f 2>/dev/null || true

info "Pruning done."

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: CHECK IF DOCKER IMAGE NEEDS REBUILD
# Hash the files that affect the Docker image: Dockerfile + requirements.txt
# If unchanged → skip rebuild (saves 5–15 min and hundreds of MB)
# ─────────────────────────────────────────────────────────────────────────────
step "🔍 2. Checking if Docker image needs rebuild..."

HASH_FILE="$CACHE_DIR/backend.hash"
CURRENT_HASH=$(md5 -q backend/Dockerfile backend/requirements.txt 2>/dev/null || \
               md5sum backend/Dockerfile backend/requirements.txt 2>/dev/null | md5sum | cut -d' ' -f1)

STORED_HASH=""
[ -f "$HASH_FILE" ] && STORED_HASH=$(cat "$HASH_FILE")

# Also check if the image actually exists
IMAGE_EXISTS=$(docker images -q "neoface-api" 2>/dev/null | wc -l | tr -d ' ')
if docker images --format "{{.Repository}}" | grep -q "^neoface" 2>/dev/null; then
    IMAGE_EXISTS=1
else
    IMAGE_EXISTS=0
fi

NEEDS_BUILD=false
if [ "$FORCE_REBUILD" = true ]; then
    warn "Force rebuild requested — will rebuild image."
    NEEDS_BUILD=true
elif [ "$CURRENT_HASH" != "$STORED_HASH" ] || [ "$IMAGE_EXISTS" -eq "0" ]; then
    warn "Dockerfile or requirements.txt changed (or image missing) — will rebuild."
    NEEDS_BUILD=true
else
    info "Docker image is up-to-date. Skipping rebuild."
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: STOP STALE CONTAINERS (without removing image/volumes)
# ─────────────────────────────────────────────────────────────────────────────
step "🧹 3. Stopping any stale containers..."
# Use 'stop' + 'rm' instead of 'down --volumes' to preserve DB data between runs
docker compose stop 2>/dev/null || true
for name in neoface_api neoface_worker neoface_beat neoface_flower neoface_postgres neoface_redis; do
    if docker inspect "$name" &>/dev/null 2>&1; then
        docker rm -f "$name" 2>/dev/null || true
    fi
done
info "Stale containers cleared."

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: START BACKEND DOCKER STACK
# ─────────────────────────────────────────────────────────────────────────────
step "📦 4. Starting backend (Postgres, Redis, API, Celery)..."

if [ "$NEEDS_BUILD" = true ]; then
    echo "   Building Docker image (only happens when Dockerfile/requirements changed)..."
    # Build with BuildKit caching enabled for faster layer reuse
    DOCKER_BUILDKIT=1 docker compose build --no-cache api worker beat
    # Save the hash so next run skips the build
    echo "$CURRENT_HASH" > "$HASH_FILE"
    info "Image built and cached."
fi

# Start all services (no --build flag = uses existing image)
docker compose up -d

# After starting, prune any intermediate build images that got created
docker image prune -f 2>/dev/null || true

info "Backend services starting..."

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: FRONTEND — Only run npm install if package lock changed
# ─────────────────────────────────────────────────────────────────────────────
step "💻 5. Starting frontend dev server..."

cd frontend

# Check if node_modules needs updating
NPM_HASH_FILE="$CACHE_DIR/npm.hash"
LOCK_FILE=""
[ -f "package-lock.json" ] && LOCK_FILE="package-lock.json"
[ -f "yarn.lock" ]         && LOCK_FILE="yarn.lock"
[ -f "pnpm-lock.yaml" ]    && LOCK_FILE="pnpm-lock.yaml"

NEEDS_NPM_INSTALL=false

if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    warn "node_modules missing — running npm install..."
    NEEDS_NPM_INSTALL=true
elif [ "$FORCE_REBUILD" = true ]; then
    warn "Force rebuild: running npm install..."
    NEEDS_NPM_INSTALL=true
elif [ -n "$LOCK_FILE" ]; then
    NPM_CURRENT=$(md5 -q "$LOCK_FILE" 2>/dev/null || md5sum "$LOCK_FILE" 2>/dev/null | cut -d' ' -f1)
    NPM_STORED=""
    [ -f "$NPM_HASH_FILE" ] && NPM_STORED=$(cat "$NPM_HASH_FILE")
    if [ "$NPM_CURRENT" != "$NPM_STORED" ]; then
        warn "package-lock.json changed — running npm install..."
        NEEDS_NPM_INSTALL=true
    fi
fi

if [ "$NEEDS_NPM_INSTALL" = true ]; then
    npm install --prefer-offline
    # Save hash of lock file
    if [ -n "$LOCK_FILE" ]; then
        md5 -q "$LOCK_FILE" 2>/dev/null > "$NPM_HASH_FILE" || \
        md5sum "$LOCK_FILE" 2>/dev/null | cut -d' ' -f1 > "$NPM_HASH_FILE"
    fi
    info "npm install done."
else
    info "node_modules up-to-date. Skipping npm install."
fi

npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   ✨ NeoFace is live!                    ║${RESET}"
echo -e "${BOLD}╠══════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}║  Frontend  →  http://localhost:3000      ║${RESET}"
echo -e "${BOLD}║  API Docs  →  http://localhost:8000/docs ║${RESET}"
echo -e "${BOLD}║  Flower    →  http://localhost:5555      ║${RESET}"
echo -e "${BOLD}║             (admin / neoface_flower_pass)║${RESET}"
echo -e "${BOLD}╠══════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}║  Press CTRL+C to stop all services       ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${CYAN}Tip: Run ${BOLD}./start.sh --clean${RESET}${CYAN} to free Docker storage.${RESET}"
echo -e "  ${CYAN}Tip: Run ${BOLD}./start.sh --force-rebuild${RESET}${CYAN} to force a full rebuild.${RESET}"
echo ""

# Wait for frontend process
wait "$FRONTEND_PID"
