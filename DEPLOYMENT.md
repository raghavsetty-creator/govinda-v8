# GOVINDA v8 — Azure Deployment Guide

## What You Need to Share (One-Time Setup)

Share these details securely — they will be stored in Azure Key Vault, never in code:

| Item | Where to get it |
|------|----------------|
| **Azure Subscription ID** | Azure Portal → Subscriptions |
| **Anthropic API Key** | console.anthropic.com → API Keys |
| **OpenAI API Key** (optional) | platform.openai.com |
| **Gemini API Key** (optional) | aistudio.google.com |
| **Broker token** (Dhan/Fyers/Zerodha) | Broker developer portal |
| **Telegram Bot Token** | @BotFather on Telegram |
| **Telegram Chat ID** | Send msg to bot, then api.telegram.org/bot{TOKEN}/getUpdates |
| **Your public IP** | whatismyip.com (for SSH whitelist) |

---

## Step 1 — Prerequisites (Run Once on Your Machine)

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash  # Linux/Mac
# Or: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Install Terraform
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip && sudo mv terraform /usr/local/bin/

# Login to Azure
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

## Step 2 — Bootstrap Terraform State Storage

```bash
cd govinda-v8
bash azure/scripts/bootstrap_tfstate.sh
```

## Step 3 — Configure Variables

```bash
cp azure/terraform/terraform.tfvars.example azure/terraform/terraform.tfvars
# Edit terraform.tfvars — fill in passwords, API keys, your IP
nano azure/terraform/terraform.tfvars
```

## Step 4 — Deploy Infrastructure

```bash
cd azure/terraform
terraform init
terraform plan      # Preview what will be created
terraform apply     # Creates VM, Key Vault, Storage (~8 minutes)
```

Terraform will output:
- `vm_public_ip` — your VM's IP address
- `dashboard_url` — http://IP:8501
- `ssh_command` — ready-to-use SSH command

## Step 5 — Deploy Application Code

```bash
cd govinda-v8
bash azure/scripts/deploy.sh <VM_IP>
```

This will:
1. SSH into the VM
2. Sync all Python code
3. Install dependencies in the virtualenv
4. Load secrets from Key Vault into `.env`
5. Start `govinda-engine` and `govinda-dashboard` systemd services

## Step 6 — Verify

```bash
# Check engine is running
ssh govindaadmin@<VM_IP> "sudo systemctl status govinda-engine"

# View live logs
ssh govindaadmin@<VM_IP> "tail -f /opt/govinda/logs/govinda_v8.log"

# Dashboard
open http://<VM_IP>:8501
```

---

## Monthly Cost Estimate (Central India region)

| Resource | Size | Cost |
|----------|------|------|
| VM B2ms (2 vCPU/8GB) | 24×7 | ~₹4,500/month |
| Storage (100GB) | LRS | ~₹200/month |
| Key Vault | Standard | ~₹100/month |
| Public IP | Static | ~₹200/month |
| **Total** | | **~₹5,000/month** |

> Upgrade to B4ms (4 vCPU/16GB) for heavier ML workloads: ~₹8,500/month

---

## Updates After Initial Deploy

Push code changes:
```bash
bash azure/scripts/deploy.sh <VM_IP>
```

Or push to `main` branch on GitHub — CI/CD auto-deploys.

---

## Key Corrections in v8 (vs earlier versions)

| What | Old (wrong) | New (correct) |
|------|------------|---------------|
| NIFTY lot size | 75 / 50 | **65** (NSE FAOP70616, Jan 2026) |
| BANKNIFTY lot size | 35 | **30** |
| March 2 holiday | Assumed closed | **Open** (only March 3 Holi is NSE holiday) |
| Expiry on Holi | March 3 | **Shifted to March 2** (NSE rule: shift to previous day) |
| Position sizing | Manual | **Auto-calculated** using `position_size_from_risk()` |
| Trade alerts | None | **Telegram** on every signal |
