# ═══════════════════════════════════════════════════════════════════════════
# GOVINDA NIFTY AI v8 — Azure Infrastructure (Terraform)
# Subscription: 05898ec6-ddec-44a5-827a-60ea367e7042
# Region:       Central India
# ═══════════════════════════════════════════════════════════════════════════

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
  }
  backend "azurerm" {
    resource_group_name  = "govinda-tfstate-rg"
    storage_account_name = "govindatfs05898"
    container_name       = "tfstate"
    key                  = "govinda.prod.tfstate"
  }
}

provider "azurerm" {
  subscription_id = "05898ec6-ddec-44a5-827a-60ea367e7042"
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# VARIABLES
# ─────────────────────────────────────────────────────────────────────────────



locals {
  prefix = "govinda-${var.environment}"
  tags = {
    Project     = "GOVINDA-NiftyAI"
    Environment = var.environment
    Owner       = "Raghav"
    Version     = "v8"
    CostCenter  = "AlgoTrading"
  }
}

data "azurerm_client_config" "current" {}

# ─────────────────────────────────────────────────────────────────────────────
# RESOURCE GROUP
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "rg" {
  name     = "${local.prefix}-rg"
  location = var.location
  tags     = local.tags
}

# ─────────────────────────────────────────────────────────────────────────────
# NETWORKING
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_virtual_network" "vnet" {
  name                = "${local.prefix}-vnet"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  address_space       = ["10.0.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "subnet" {
  name                 = "${local.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = "${local.prefix}-nsg"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags

  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.allowed_ssh_ip
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowDashboard"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8501"
    source_address_prefix      = var.allowed_ssh_ip
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "nsg_assoc" {
  subnet_id                 = azurerm_subnet.subnet.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_public_ip" "pip" {
  name                = "${local.prefix}-pip"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_network_interface" "nic" {
  name                = "${local.prefix}-nic"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# VIRTUAL MACHINE
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_linux_virtual_machine" "vm" {
  name                = "${local.prefix}-vm"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = var.vm_size
  admin_username      = var.admin_username
  admin_password      = var.admin_password
  tags                = local.tags

  disable_password_authentication = false

  admin_ssh_key {
    username   = var.admin_username
    public_key = file("~/.ssh/govinda_azure.pub")
  }

  identity { type = "SystemAssigned" }

  network_interface_ids = [azurerm_network_interface.nic.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-arm64"
    version   = "latest"
  }

  custom_data = base64encode(file("${path.module}/../scripts/vm_bootstrap.sh"))
}

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE ACCOUNT
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_storage_account" "storage" {
  name                     = "govindast05898prod"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_container" "logs"    {
  name                  = "govinda-logs"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "models"  {
  name                  = "govinda-models"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "signals" {
  name                  = "govinda-signals"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# ─────────────────────────────────────────────────────────────────────────────
# KEY VAULT
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_key_vault" "kv" {
  name                       = "govinda-prod-kv"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  sku_name                   = "standard"
  tags                       = local.tags

  # Your account (deployer) — full access
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    secret_permissions = ["Get","List","Set","Delete","Purge","Recover"]
  }
}

# VM managed identity — read only
resource "azurerm_key_vault_access_policy" "vm_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_virtual_machine.vm.identity[0].principal_id
  secret_permissions = ["Get","List"]
}

# ── Store secrets ─────────────────────────────────────────────────────────────

resource "azurerm_key_vault_secret" "storage_conn" {
  name         = "AZURE-STORAGE-CONNECTION-STRING"
  value        = azurerm_storage_account.storage.primary_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "anthropic" {
  count        = var.anthropic_api_key != "" ? 1 : 0
  name         = "ANTHROPIC-API-KEY"
  value        = var.anthropic_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "openai" {
  count        = var.openai_api_key != "" ? 1 : 0
  name         = "OPENAI-API-KEY"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "gemini" {
  count        = var.gemini_api_key != "" ? 1 : 0
  name         = "GEMINI-API-KEY"
  value        = var.gemini_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "dhan_id" {
  count        = var.dhan_client_id != "" ? 1 : 0
  name         = "DHAN-CLIENT-ID"
  value        = var.dhan_client_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "dhan_token" {
  count        = var.dhan_access_token != "" ? 1 : 0
  name         = "DHAN-ACCESS-TOKEN"
  value        = var.dhan_access_token
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "fyers_id" {
  count        = var.fyers_app_id != "" ? 1 : 0
  name         = "FYERS-APP-ID"
  value        = var.fyers_app_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "fyers_token" {
  count        = var.fyers_access_token != "" ? 1 : 0
  name         = "FYERS-ACCESS-TOKEN"
  value        = var.fyers_access_token
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "telegram_token" {
  count        = var.telegram_bot_token != "" ? 1 : 0
  name         = "TELEGRAM-BOT-TOKEN"
  value        = var.telegram_bot_token
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "telegram_chat" {
  count        = var.telegram_chat_id != "" ? 1 : 0
  name         = "TELEGRAM-CHAT-ID"
  value        = var.telegram_chat_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

resource "azurerm_key_vault_secret" "capital" {
  name         = "TRADING-CAPITAL"
  value        = var.trading_capital
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault.kv]
}

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────

output "vm_public_ip"        { value = azurerm_public_ip.pip.ip_address }
output "ssh_command"         { value = "ssh govindaadmin@${azurerm_public_ip.pip.ip_address}" }
output "dashboard_url"       { value = "http://${azurerm_public_ip.pip.ip_address}:8501" }
output "key_vault_url"       { value = azurerm_key_vault.kv.vault_uri }
output "storage_account"     { value = azurerm_storage_account.storage.name }
output "resource_group"      { value = azurerm_resource_group.rg.name }
