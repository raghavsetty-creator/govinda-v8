# GOVINDA v8 — Detailed Azure Deployment Guide
## Every Command Explained Step by Step

---

## PREREQUISITES — What You Need on Your Laptop

- Windows 10/11 laptop (all commands below are for Windows)
- Internet connection
- The GOVINDA_v8_AzureReady.zip file (already downloaded)

---

## PART A — Install Tools (One Time Only)

### A1. Install Azure CLI

1. Open your browser and go to:
   ```
   https://aka.ms/installazurecliwindows
   ```
2. It will download a file called `azure-cli-*.msi`
3. Double-click it → click Next → Next → Install → Finish
4. **Verify it worked** — open Command Prompt (press Win+R, type `cmd`, press Enter):
   ```cmd
   az --version
   ```
   You should see something like: `azure-cli 2.58.0`

---

### A2. Install Terraform

1. Go to:
   ```
   https://developer.hashicorp.com/terraform/install#windows
   ```
2. Under "Windows" → click **AMD64** to download the zip
3. Extract the zip — you'll get a single file: `terraform.exe`
4. Move `terraform.exe` to `C:\Windows\System32\` (so it works from any folder)
5. **Verify it worked** — in Command Prompt:
   ```cmd
   terraform --version
   ```
   You should see: `Terraform v1.7.x`

---

### A3. Install Git (needed for rsync/deploy)

1. Download from: `https://git-scm.com/download/win`
2. Run the installer → all defaults → Finish
3. **Verify:**
   ```cmd
   git --version
   ```

---

### A4. Extract the GOVINDA Package

1. Find `GOVINDA_v8_AzureReady.zip` in your Downloads folder
2. Right-click → Extract All → Extract to `C:\govinda-v8\`
3. You should now have: `C:\govinda-v8\` with folders: `app\`, `azure\`, `Dockerfile`, etc.

---

## PART B — Open the Right Terminal

> **Important:** Use **Git Bash** (not regular CMD) for all commands below.
> Git Bash was installed with Git in step A3.

**How to open Git Bash:**
- Press Win key → type `Git Bash` → press Enter
- You'll see a black terminal with a `$` prompt

**Navigate to your project:**
```bash
cd /c/govinda-v8
```

Verify you're in the right place:
```bash
ls
```
You should see: `app/  azure/  Dockerfile  docker-compose.yml  DEPLOYMENT.md`

---

## PART C — Azure Login

### C1. Login to Azure

```bash
az login
```

**What happens:**
- A browser window opens automatically
- Sign in with your Microsoft account (the one linked to Founders Hub)
- After login, the browser says "You have logged in" — close it
- Back in terminal you'll see a JSON list of your subscriptions

### C2. Set Your Subscription

```bash
az account set --subscription "05898ec6-ddec-44a5-827a-60ea367e7042"
```

**Verify it worked:**
```bash
az account show --query "{Name:name, SubscriptionId:id, State:state}" -o table
```

Expected output:
```
Name                SubscriptionId                        State
------------------  ------------------------------------  -------
Azure Sponsorship   05898ec6-ddec-44a5-827a-60ea367e7042  Enabled
```

If you see `Azure Sponsorship` — your Founders Hub credits are active ✅

---

## PART D — Generate SSH Key (For VM Access)

This creates a key pair so you can SSH into the VM securely (no password needed for SSH).

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/govinda_azure -N "" -C "govinda-azure"
```

**What this does:** Creates two files:
- `~/.ssh/govinda_azure` — your private key (keep secret)
- `~/.ssh/govinda_azure.pub` — public key (goes to VM)

**Verify:**
```bash
ls ~/.ssh/govinda_azure*
```
You should see both files.

---

## PART E — Bootstrap Terraform State Storage

> This runs ONCE before anything else. It creates a storage account in Azure
> where Terraform saves its state (like a database of what's been deployed).

```bash
cd /c/govinda-v8
bash azure/scripts/bootstrap_tfstate.sh
```

**What you'll see:**
```
▶ Setting subscription...
▶ Creating resource group for Terraform state...
{
  "id": "/subscriptions/05898ec6.../resourceGroups/govinda-tfstate-rg",
  "location": "centralindia",
  "name": "govinda-tfstate-rg",
  ...
}
▶ Creating storage account for Terraform state...
▶ Creating state container...
✅ Terraform state storage ready
   Storage: govindatfs05898
   Container: tfstate
```

**If you get an error** "Storage account name already taken":
```bash
# The name govindatfs05898 is already taken globally — add random suffix
# Edit the script:
nano azure/scripts/bootstrap_tfstate.sh
# Change STATE_SA="govindatfs05898" to STATE_SA="govindatfs05898x"
# Save: Ctrl+O, Enter, Ctrl+X
# Also update main.tf:
nano azure/terraform/main.tf
# Find "govindatfs05898" and change to "govindatfs05898x"
# Run the script again
```

---

## PART F — Add Your API Keys to terraform.tfvars

```bash
nano /c/govinda-v8/azure/terraform/terraform.tfvars
```

The file will open in the terminal editor. You'll see:

```hcl
environment    = "prod"
location       = "centralindia"
vm_size        = "Standard_B2ms"
admin_username = "govindaadmin"
allowed_ssh_ip = "122.171.22.72/32"

anthropic_api_key  = ""    ← PUT YOUR NEW KEY HERE between the quotes
openai_api_key     = ""
gemini_api_key     = ""
dhan_client_id     = ""
dhan_access_token  = ""
fyers_app_id       = ""
fyers_access_token = ""
telegram_bot_token = ""
telegram_chat_id   = ""
trading_capital    = "500000"
```

**How to edit in nano:**
- Arrow keys to move cursor
- Type to add text
- Save: press `Ctrl+O` then `Enter`
- Exit: press `Ctrl+X`

> Add your **new** Anthropic key (after revoking the old one).
> Leave broker keys blank for now — add after deploy via Key Vault.

---

## PART G — Deploy Infrastructure with Terraform

### G1. Navigate to terraform folder

```bash
cd /c/govinda-v8/azure/terraform
```

### G2. Initialize Terraform

```bash
terraform init
```

**What happens:** Terraform downloads the Azure provider plugin (~30 MB).

**Expected output:**
```
Initializing the backend...
Successfully configured the backend "azurerm"!

Initializing provider plugins...
- Finding hashicorp/azurerm versions matching "~> 3.85"...
- Installing hashicorp/azurerm v3.85.0...

Terraform has been successfully initialized!
```

**If you get error "storage account not found":**
Make sure Part E (bootstrap) completed successfully first.

---

### G3. Preview the Deployment Plan

```bash
terraform plan -var="admin_password=Govind@!9032639"
```

**What happens:** Terraform shows everything it WILL create — no actual changes yet.

**Expected output (last few lines):**
```
Plan: 16 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + dashboard_url   = (known after apply)
  + ssh_command     = (known after apply)
  + vm_public_ip    = (known after apply)
  + key_vault_url   = "https://govinda-prod-kv.vault.azure.net/"
```

If you see `16 to add` — everything looks correct ✅

---

### G4. Apply — Actually Create Everything

```bash
terraform apply -var="admin_password=Govind@!9032639"
```

Terraform shows the plan again and asks:

```
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value:
```

Type `yes` and press Enter.

**What gets created (takes ~8-10 minutes):**
```
azurerm_resource_group.rg         — creates resource group
azurerm_virtual_network.vnet      — creates network
azurerm_subnet.subnet             — creates subnet
azurerm_network_security_group.nsg — creates firewall rules
azurerm_public_ip.pip             — reserves your static IP
azurerm_network_interface.nic     — creates network card
azurerm_linux_virtual_machine.vm  — creates the VM (takes ~5 min)
azurerm_storage_account.storage   — creates storage
azurerm_storage_container.logs    — creates logs container
azurerm_storage_container.models  — creates models container
azurerm_storage_container.signals — creates signals container
azurerm_key_vault.kv              — creates Key Vault
azurerm_key_vault_access_policy.* — sets permissions
azurerm_key_vault_secret.*        — stores your API keys
```

**Final output (SAVE THIS):**
```
Apply complete! Resources: 16 added, 0 changed, 0 destroyed.

Outputs:

dashboard_url    = "http://20.192.xx.xx:8501"
key_vault_url    = "https://govinda-prod-kv.vault.azure.net/"
resource_group   = "govinda-prod-rg"
ssh_command      = "ssh govindaadmin@20.192.xx.xx"
storage_account  = "govindast05898prod"
vm_public_ip     = "20.192.xx.xx"
```

**Copy and save the `vm_public_ip` value** — you need it next.

---

## PART H — Wait for VM Bootstrap to Complete

The VM runs a bootstrap script automatically on first boot that installs Python, sets up directories, and creates systemd services. This takes about **5 minutes** after the VM is created.

**Check if bootstrap is done:**
```bash
# Replace 20.192.xx.xx with your actual VM IP
ssh -i ~/.ssh/govinda_azure govindaadmin@20.192.xx.xx "tail -5 /var/log/govinda-bootstrap.log"
```

Wait until you see:
```
=== GOVINDA Bootstrap Complete: Sat Feb 28 ...
Next: run azure/scripts/deploy.sh to push the application code
```

If the file doesn't exist yet, the bootstrap is still running — wait 2 more minutes and try again.

---

## PART I — Deploy Application Code

Go back to the project root:
```bash
cd /c/govinda-v8
```

Run deploy (replace with your actual IP):
```bash
bash azure/scripts/deploy.sh 20.192.xx.xx
```

**What you'll see:**
```
╔══════════════════════════════════════════════════════╗
║    GOVINDA v8 — Deploying to 20.192.xx.xx
╚══════════════════════════════════════════════════════╝

▶ [1/6] Stopping services...
▶ [2/6] Preparing directories...
▶ [3/6] Syncing code...
sending incremental file list
config.py
main.py
utils/holiday_checker.py
utils/lot_sizes.py
utils/notifier.py
...
▶ [4/6] Installing dependencies...
▶ [5/6] Loading secrets from Key Vault...
Secrets loaded from Key Vault: govinda-prod-kv
▶ [6/6] Starting services...

╔══════════════════════════════════════════════════════╗
║            DEPLOYMENT COMPLETE ✅                    ║
╠══════════════════════════════════════════════════════╣
║  VM IP     : 20.192.xx.xx
║  Engine    : active
║  Dashboard : active
║  URL       : http://20.192.xx.xx:8501
╚══════════════════════════════════════════════════════╝
```

---

## PART J — Verify Everything Is Running

### J1. Open the Dashboard

In your browser, go to:
```
http://20.192.xx.xx:8501
```
You should see the GOVINDA Streamlit dashboard.

### J2. SSH In and Watch Live Logs

```bash
ssh -i ~/.ssh/govinda_azure govindaadmin@20.192.xx.xx
```

Once inside the VM:
```bash
# Check both services are running
sudo systemctl status govinda-engine govinda-dashboard

# Watch live signal logs
tail -f /opt/govinda/logs/govinda_v8.log

# Check if today is a trading day and what mode system is in
cd /opt/govinda/app
source /opt/govinda/venv/bin/activate
python3 -c "
from utils.holiday_checker import should_system_run, trade_calendar_summary
r = should_system_run()
c = trade_calendar_summary()
print(f'Mode   : {r[\"mode\"]}')
print(f'Reason : {r[\"reason\"]}')
print(f'Entry  : {c[\"entry_day\"]}')
print(f'Expiry : {c[\"expiry_date\"]} ({c[\"days_to_expiry\"]}d)')
"
```

---

## PART K — Add Broker API Key (After Deploy)

When you have your Dhan/Fyers token ready, add directly via Key Vault — no code changes needed:

**For Dhan:**
```bash
az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "DHAN-CLIENT-ID" \
  --value "YOUR_DHAN_CLIENT_ID"

az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "DHAN-ACCESS-TOKEN" \
  --value "YOUR_DHAN_TOKEN"
```

**For Fyers:**
```bash
az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "FYERS-APP-ID" \
  --value "YOUR_FYERS_APP_ID"

az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "FYERS-ACCESS-TOKEN" \
  --value "YOUR_FYERS_TOKEN"
```

**Then restart the engine to pick up new secrets:**
```bash
ssh -i ~/.ssh/govinda_azure govindaadmin@20.192.xx.xx \
  "sudo systemctl restart govinda-engine"
```

---

## PART L — Add Telegram Alerts (Optional but Recommended)

### L1. Create a Telegram Bot

1. Open Telegram → search for `@BotFather`
2. Send: `/newbot`
3. Give it a name: `GOVINDA Trading Bot`
4. Give it a username: `govinda_nifty_bot` (must end in `bot`)
5. BotFather gives you a token like: `7123456789:AAHxxx...`

### L2. Get Your Chat ID

1. Send any message to your new bot
2. Open in browser (replace TOKEN):
   ```
   https://api.telegram.org/bot7123456789:AAHxxx.../getUpdates
   ```
3. Look for `"id"` inside `"chat"` — that's your chat ID (e.g. `987654321`)

### L3. Add to Key Vault

```bash
az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "TELEGRAM-BOT-TOKEN" \
  --value "7123456789:AAHxxx..."

az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "TELEGRAM-CHAT-ID" \
  --value "987654321"

# Restart to pick up
ssh -i ~/.ssh/govinda_azure govindaadmin@20.192.xx.xx \
  "sudo systemctl restart govinda-engine"
```

From now on, every trade signal sends you a Telegram message instantly.

---

## PART M — Add New Anthropic Key (After Revoking Old One)

```bash
az keyvault secret set \
  --vault-name "govinda-prod-kv" \
  --name "ANTHROPIC-API-KEY" \
  --value "sk-ant-YOUR-NEW-KEY-HERE"

ssh -i ~/.ssh/govinda_azure govindaadmin@20.192.xx.xx \
  "sudo systemctl restart govinda-engine"
```

---

## Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| `az: command not found` | Azure CLI not installed or restart terminal |
| `terraform: command not found` | terraform.exe not in System32 |
| `storage account name taken` | Change `govindatfs05898` to `govindatfs05898x` in both files |
| `VM not reachable via SSH` | Check your IP hasn't changed — run `whatismyip.com` and update NSG if needed |
| `Engine service not active` | `ssh in → sudo journalctl -u govinda-engine -n 50` to see error |
| `Key Vault access denied` | Make sure you ran `az login` before terraform apply |
| Bootstrap not complete | Wait 5 min, check `/var/log/govinda-bootstrap.log` |

---

## Quick Reference — All Key Commands

```bash
# Login
az login
az account set --subscription "05898ec6-ddec-44a5-827a-60ea367e7042"

# Deploy infrastructure
cd /c/govinda-v8/azure/terraform
terraform init
terraform apply -var="admin_password=Govind@!9032639"

# Deploy code
cd /c/govinda-v8
bash azure/scripts/deploy.sh <VM_IP>

# SSH in
ssh -i ~/.ssh/govinda_azure govindaadmin@<VM_IP>

# Watch logs
tail -f /opt/govinda/logs/govinda_v8.log

# Restart engine
sudo systemctl restart govinda-engine

# Add/update any secret
az keyvault secret set --vault-name "govinda-prod-kv" --name "SECRET-NAME" --value "value"
```
