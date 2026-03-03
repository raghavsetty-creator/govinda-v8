# GOVINDA v8 — Your Exact Deployment Steps

## Your Details
- **Subscription** : 05898ec6-ddec-44a5-827a-60ea367e7042
- **Region**       : Central India
- **IP Whitelist** : 122.171.22.72/32
- **VM Size**      : Standard_B2ms (2 vCPU / 8GB RAM)

---

## PHASE 1 — One-Time Machine Setup (15 mins)

### 1.1 Install Azure CLI

**Windows:**
```
https://aka.ms/installazurecliwindows  → download and run the MSI
```

**Mac:**
```bash
brew install azure-cli
```

**Linux/WSL:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### 1.2 Install Terraform

**Windows** — download from:
```
https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_windows_amd64.zip
Extract terraform.exe → add to PATH
```

**Mac:**
```bash
brew install terraform
```

**Linux/WSL:**
```bash
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

---

## PHASE 2 — Azure Login & Verify Credits (5 mins)

```bash
# Login — browser will open
az login

# Set your subscription
az account set --subscription "05898ec6-ddec-44a5-827a-60ea367e7042"

# Verify it's set correctly
az account show --query "{Name:name, ID:id, State:state}" -o table
```

Expected output:
```
Name                    ID                                    State
----------------------  ------------------------------------  -------
Azure Sponsorship       05898ec6-ddec-44a5-827a-60ea367e7042  Enabled
```

---

## PHASE 3 — Bootstrap Terraform State Storage (3 mins)

Run this ONCE before anything else:

```bash
cd govinda-v8
bash azure/scripts/bootstrap_tfstate.sh
```

You'll see:
```
✅ Terraform state storage ready
   Storage: govindatfs05898
   Container: tfstate
```

---

## PHASE 4 — Add Your API Keys (5 mins)

Edit `azure/terraform/terraform.tfvars` — fill in whichever keys you have:

```hcl
anthropic_api_key  = "sk-ant-..."     # Required for Claude AI
openai_api_key     = "sk-..."         # Optional
gemini_api_key     = "AIza..."        # Optional
dhan_client_id     = ""               # Fill if using Dhan
dhan_access_token  = ""
fyers_app_id       = ""               # Fill if using Fyers
fyers_access_token = ""
telegram_bot_token = ""               # For trade alerts
telegram_chat_id   = ""
trading_capital    = "500000"         # Your capital in ₹
```

---

## PHASE 5 — Deploy Infrastructure (10 mins)

```bash
cd govinda-v8/azure/terraform

# Initialize Terraform
terraform init

# Preview what will be created (no changes made)
terraform plan -var="admin_password=Govind@!9032639"

# CREATE everything on Azure
terraform apply -var="admin_password=Govind@!9032639"
```

Type **yes** when prompted.

After ~8 minutes you'll see:
```
Apply complete! Resources: 16 added.

Outputs:
vm_public_ip     = "20.xxx.xxx.xxx"
ssh_command      = "ssh govindaadmin@20.xxx.xxx.xxx"
dashboard_url    = "http://20.xxx.xxx.xxx:8501"
key_vault_url    = "https://govinda-prod-kv.vault.azure.net/"
```

**Save the VM IP address** — you'll need it in the next step.

---

## PHASE 6 — Deploy Application Code (5 mins)

```bash
cd govinda-v8

# Replace 20.xxx.xxx.xxx with your actual VM IP from above
bash azure/scripts/deploy.sh 20.xxx.xxx.xxx
```

---

## PHASE 7 — Verify Everything Is Running

```bash
# SSH into VM
ssh -i ~/.ssh/govinda_azure govindaadmin@20.xxx.xxx.xxx

# Check engine status
sudo systemctl status govinda-engine

# Watch live logs
tail -f /opt/govinda/logs/govinda_v8.log
```

Open your browser: `http://20.xxx.xxx.xxx:8501` → Streamlit dashboard

---

## Useful Commands After Deploy

```bash
# Restart engine (e.g. after code change)
sudo systemctl restart govinda-engine

# Check both services
sudo systemctl status govinda-engine govinda-dashboard

# View today's signals log
grep "SIGNAL" /opt/govinda/logs/govinda_v8.log | tail -20

# Manually trigger a signal now
cd /opt/govinda/app && source /opt/govinda/venv/bin/activate
python -c "from main import GOVINDA; g=GOVINDA(); g.initialize(); g.get_signal()"

# Update API keys in Key Vault (e.g. when broker token refreshes)
az keyvault secret set \
  --vault-name govinda-prod-kv \
  --name "DHAN-ACCESS-TOKEN" \
  --value "your-new-token"
# Then reload: sudo systemctl restart govinda-engine
```

---

## Monthly Cost on Founders Hub Credits

| Resource           | Cost/month |
|--------------------|-----------|
| VM B2ms            | ~$9 (~₹750) |
| Storage + Key Vault| ~$3 (~₹250) |
| **Total**          | **~$12/month** |

At $5,000 Founders Hub credits = **34 years of free runtime** 🎉

---

## Next Steps After Deploy

1. Add Telegram bot (get alerts on every signal)
2. Add broker API token (Dhan/Fyers) → enable live order execution
3. Upgrade to B4ms VM if ML training feels slow
