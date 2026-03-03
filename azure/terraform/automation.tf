# ═══════════════════════════════════════════════════════════════════════════
# GOVINDA NIFTY AI v8 — Azure Automation (Auto Start/Stop)
# Add this file to: /c/govinda-v8/azure/terraform/automation.tf
#
# Auto-start : 08:25 AM IST (Mon–Fri)
# Auto-stop  : 04:30 PM IST (Mon–Fri)
# ═══════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# AUTOMATION ACCOUNT
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_automation_account" "govinda" {
  name                = "${local.prefix}-automation"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "Basic"

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ─────────────────────────────────────────────────────────────────────────────
# PERMISSIONS — Allow Automation Account to start/stop VM
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_role_assignment" "automation_vm_contributor" {
  scope                = azurerm_linux_virtual_machine.vm.id
  role_definition_name = "Virtual Machine Contributor"
  principal_id         = azurerm_automation_account.govinda.identity[0].principal_id
}

# ─────────────────────────────────────────────────────────────────────────────
# RUNBOOK — Start VM
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_automation_runbook" "start_vm" {
  name                    = "StartGovindaVM"
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.govinda.name
  log_verbose             = false
  log_progress            = false
  runbook_type            = "PowerShell"
  tags                    = local.tags

  content = <<-SCRIPT
    # GOVINDA VM Auto-Start
    # Fires at 08:25 AM IST — VM ready before 09:15 AM market open

    Write-Output "=== GOVINDA Auto-Start ==="
    Write-Output "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') UTC"

    try {
        Connect-AzAccount -Identity
        Write-Output "Azure login: OK"

        $status = (Get-AzVM `
            -ResourceGroupName "${azurerm_resource_group.rg.name}" `
            -Name "${azurerm_linux_virtual_machine.vm.name}" `
            -Status).Statuses | Where-Object { $_.Code -like "PowerState/*" }

        Write-Output "Current VM state: $($status.DisplayStatus)"

        if ($status.DisplayStatus -eq "VM running") {
            Write-Output "VM already running — skipping start"
        } else {
            $result = Start-AzVM `
                -ResourceGroupName "${azurerm_resource_group.rg.name}" `
                -Name "${azurerm_linux_virtual_machine.vm.name}"
            Write-Output "VM start result: $($result.Status)"
            Write-Output "GOVINDA engine will load state and start by 08:30 AM IST"
            Write-Output "First signal at 09:15 AM IST"
        }
    }
    catch {
        Write-Error "Start failed: $_"
        throw
    }
  SCRIPT
}

# ─────────────────────────────────────────────────────────────────────────────
# RUNBOOK — Stop VM
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_automation_runbook" "stop_vm" {
  name                    = "StopGovindaVM"
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.govinda.name
  log_verbose             = false
  log_progress            = false
  runbook_type            = "PowerShell"
  tags                    = local.tags

  content = <<-SCRIPT
    # GOVINDA VM Auto-Stop
    # Fires at 04:30 PM IST — after market close
    # systemd shutdown hook saves state before VM powers off

    Write-Output "=== GOVINDA Auto-Stop ==="
    Write-Output "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') UTC"

    try {
        Connect-AzAccount -Identity
        Write-Output "Azure login: OK"

        $status = (Get-AzVM `
            -ResourceGroupName "${azurerm_resource_group.rg.name}" `
            -Name "${azurerm_linux_virtual_machine.vm.name}" `
            -Status).Statuses | Where-Object { $_.Code -like "PowerState/*" }

        Write-Output "Current VM state: $($status.DisplayStatus)"

        if ($status.DisplayStatus -ne "VM running") {
            Write-Output "VM already stopped — skipping"
        } else {
            # Give systemd 60 seconds to save state before forcing shutdown
            Write-Output "Waiting 60s for GOVINDA to save state..."
            Start-Sleep -Seconds 60

            $result = Stop-AzVM `
                -ResourceGroupName "${azurerm_resource_group.rg.name}" `
                -Name "${azurerm_linux_virtual_machine.vm.name}" `
                -Force
            Write-Output "VM stop result: $($result.Status)"
            Write-Output "State saved. GOVINDA will resume tomorrow at 08:25 AM IST"
        }
    }
    catch {
        Write-Error "Stop failed: $_"
        throw
    }
  SCRIPT
}

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULE — Start at 08:25 AM IST Mon–Fri
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_automation_schedule" "start_schedule" {
  name                    = "govinda-daily-start"
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.govinda.name
  frequency               = "Week"
  interval                = 1
  timezone                = "Asia/Kolkata"
  start_time              = "2026-03-04T08:25:00+05:30"
  description             = "Start GOVINDA VM at 08:25 AM IST Mon-Fri"

  week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULE — Stop at 04:30 PM IST Mon–Fri
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_automation_schedule" "stop_schedule" {
  name                    = "govinda-daily-stop"
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.govinda.name
  frequency               = "Week"
  interval                = 1
  timezone                = "Asia/Kolkata"
  start_time              = "2026-03-04T16:30:00+05:30"
  description             = "Stop GOVINDA VM at 04:30 PM IST Mon-Fri"

  week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}

# ─────────────────────────────────────────────────────────────────────────────
# LINK RUNBOOKS TO SCHEDULES
# ─────────────────────────────────────────────────────────────────────────────

resource "azurerm_automation_job_schedule" "start_job" {
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.govinda.name
  runbook_name            = azurerm_automation_runbook.start_vm.name
  schedule_name           = azurerm_automation_schedule.start_schedule.name
}

resource "azurerm_automation_job_schedule" "stop_job" {
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.govinda.name
  runbook_name            = azurerm_automation_runbook.stop_vm.name
  schedule_name           = azurerm_automation_schedule.stop_schedule.name
}

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────

output "automation_account_name" {
  value = azurerm_automation_account.govinda.name
}

output "automation_schedule" {
  value = {
    start = "08:25 AM IST Mon-Fri"
    stop  = "04:30 PM IST Mon-Fri"
  }
}
