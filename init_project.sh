#!/usr/bin/env bash
# ============================================================
# BidGuard AI - Project Initialization Script
# SIH26100: AI-Powered Integrated Bid Compliance Verification
# Platform for GeM Procurement
#
# Creates the full monorepo directory layout, Python package
# markers, and starter files. Safe to re-run (idempotent).
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { echo -e "${BLUE}[BidGuard AI]${NC} $1"; }
ok()   { echo -e "${GREEN}  ✓${NC} $1"; }

# ----------------------------------------------------------
# 1. Directory structure
# ----------------------------------------------------------
log "Creating directory structure..."

BACKEND_DIRS=(
  backend/app
  backend/app/api
  backend/app/api/v1
  backend/app/api/v1/routes
  backend/app/api/v1/mock
  backend/app/core
  backend/app/models
  backend/app/schemas
  backend/app/services
  backend/app/services/parsing
  backend/app/services/compliance
  backend/app/services/gateways
  backend/app/workers
  backend/tests
  backend/tests/unit
  backend/tests/integration
  backend/uploads
)

FRONTEND_DIRS=(
  "frontend/app"
  "frontend/app/(dashboard)"
  "frontend/app/(dashboard)/bids"
  "frontend/app/(dashboard)/compliance"
  "frontend/app/(dashboard)/reports"
  "frontend/components"
  "frontend/components/ui"
  "frontend/lib"
  "frontend/hooks"
  "frontend/types"
  "frontend/public"
)

for dir in "${BACKEND_DIRS[@]}" "${FRONTEND_DIRS[@]}"; do
  mkdir -p "$dir"
  ok "mkdir -p $dir"
done

# ----------------------------------------------------------
# 2. Python package markers (__init__.py)
# ----------------------------------------------------------
log "Creating Python package markers..."

PYTHON_PACKAGES=(
  backend/app
  backend/app/api
  backend/app/api/v1
  backend/app/api/v1/routes
  backend/app/api/v1/mock
  backend/app/core
  backend/app/models
  backend/app/schemas
  backend/app/services
  backend/app/services/parsing
  backend/app/services/compliance
  backend/app/services/gateways
  backend/app/workers
  backend/tests
)

for pkg in "${PYTHON_PACKAGES[@]}"; do
  touch "$pkg/__init__.py"
  ok "touch $pkg/__init__.py"
done

# ----------------------------------------------------------
# 3. Environment file
# ----------------------------------------------------------
log "Setting up environment file..."

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  ok "Copied .env.example -> .env"
else
  ok ".env already exists (skipped)"
fi

# ----------------------------------------------------------
# 4. Starter backend entrypoint (only if missing)
# ----------------------------------------------------------
log "Checking backend entrypoint..."

if [ ! -f backend/main.py ]; then
  cat > backend/main.py <<'EOF'
from fastapi import FastAPI

app = FastAPI(
    title="BidGuard AI",
    description="AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "bidguard-ai"}
EOF
  ok "Created backend/main.py"
else
  ok "backend/main.py already exists (skipped)"
fi

# ----------------------------------------------------------
# 5. Done
# ----------------------------------------------------------
echo ""
log "Initialization complete!"
echo ""
echo "  Next steps:"
echo "    1. python3.11 -m venv backend/.venv && source backend/.venv/bin/activate"
echo "    2. pip install -r backend/requirements.txt"
echo "    3. cd frontend && npm install"
echo "    4. docker compose up --build"
echo ""
