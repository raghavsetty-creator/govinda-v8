#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# GOVINDA v8 — Code Deploy Script
# Pushes latest app code to Azure VM via SSH + rsync
# Usage: bash azure/scripts/deploy.sh <VM_IP>
# ═══════════════════════════════════════════════════════════════════

set -e

VM_IP="${1:?Usage: deploy.sh <VM_IP>}"
SSH_KEY="$HOME/.ssh/govinda_azure"
VM_USER="govindaadmin"
APP_DIR="/opt/govinda/app"
VENV="/opt/govinda/venv"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    GOVINDA v8 — Deploying to $VM_IP"
echo "╚══════════════════════════════════════════════════╝"

SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP"

# 1. Stop services
echo "▶ [1/6] Stopping services..."
$SSH "sudo systemctl stop govinda-engine govinda-dashboard 2>/dev/null || true"

# 2. Ensure app dir exists with correct permissions
echo "▶ [2/6] Preparing directories..."
$SSH "sudo mkdir -p $APP_DIR && sudo chown $VM_USER:$VM_USER $APP_DIR"

# 3. Sync code
echo "▶ [3/6] Syncing code..."
rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'saved_models/*.pkl' \
    --exclude 'saved_models/*.model' \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    ./app/ \
    "$VM_USER@$VM_IP:$APP_DIR/"

# 4. Install Python dependencies
echo "▶ [4/6] Installing dependencies..."
$SSH "source $VENV/bin/activate && pip install -q --upgrade pip && pip install -q -r $APP_DIR/requirements.txt"

# 5. Set Key Vault URL so load-secrets.sh can find secrets
KV_NAME="govinda-prod-kv"
$SSH "echo 'https://$KV_NAME.vault.azure.net/' | sudo tee /opt/govinda/.kv-url > /dev/null"
$SSH "sudo chown $VM_USER:$VM_USER /opt/govinda/.kv-url"

# 6. Load secrets from Key Vault into .env
echo "▶ [5/6] Loading secrets from Key Vault..."
$SSH "bash /opt/govinda/scripts/load-secrets.sh"

# 7. Start services
echo "▶ [6/6] Starting services..."
$SSH "sudo systemctl daemon-reload"
$SSH "sudo systemctl start govinda-engine"
sleep 5
$SSH "sudo systemctl start govinda-dashboard"

# Health check
sleep 8
ENGINE=$($SSH "sudo systemctl is-active govinda-engine" 2>/dev/null || echo "unknown")
DASH=$($SSH "sudo systemctl is-active govinda-dashboard" 2>/dev/null || echo "unknown")

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            DEPLOYMENT COMPLETE ✅                ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  VM IP     : $VM_IP"
echo "║  Engine    : $ENGINE"
echo "║  Dashboard : $DASH"
echo "║  URL       : http://$VM_IP:8501"
echo "║  Logs      : ssh -i ~/.ssh/govinda_azure $VM_USER@$VM_IP"
echo "║              tail -f /opt/govinda/logs/govinda_v8.log"
echo "╚══════════════════════════════════════════════════╝"

if [ "$ENGINE" != "active" ]; then
    echo ""
    echo "⚠️  Engine not running. Debug with:"
    echo "  $SSH 'sudo journalctl -u govinda-engine -n 30 --no-pager'"
fi
