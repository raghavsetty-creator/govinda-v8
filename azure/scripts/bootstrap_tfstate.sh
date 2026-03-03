#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# GOVINDA — Bootstrap Terraform Remote State Storage
# Run ONCE before first terraform init
# ═══════════════════════════════════════════════════════════════════

set -e

SUBSCRIPTION_ID="05898ec6-ddec-44a5-827a-60ea367e7042"
LOCATION="centralindia"
STATE_RG="govinda-tfstate-rg"
STATE_SA="govindatfs05898"      # Globally unique, lowercase
STATE_CONTAINER="tfstate"

echo "▶ Setting subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

echo "▶ Creating resource group for Terraform state..."
az group create \
    --name "$STATE_RG" \
    --location "$LOCATION"

echo "▶ Creating storage account for Terraform state..."
az storage account create \
    --name "$STATE_SA" \
    --resource-group "$STATE_RG" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --allow-blob-public-access false

echo "▶ Creating state container..."
az storage container create \
    --name "$STATE_CONTAINER" \
    --account-name "$STATE_SA" \
    --auth-mode login

echo ""
echo "✅ Terraform state storage ready"
echo "   Subscription : $SUBSCRIPTION_ID"
echo "   Storage      : $STATE_SA"
echo "   Container    : $STATE_CONTAINER"
echo ""
echo "Now run:"
echo "  cd azure/terraform"
echo "  terraform init"
