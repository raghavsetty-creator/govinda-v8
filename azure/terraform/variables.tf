variable "environment"    { default = "prod" }
variable "location"       { default = "centralindia" }
variable "vm_size"        { default = "Standard_B2ps_v2" }
variable "admin_username" { default = "govindaadmin" }
variable "allowed_ssh_ip" { default = "122.171.22.72/32" }

variable "admin_password" {
  sensitive = true
}

variable "anthropic_api_key" {
  default   = ""
  sensitive = true
}

variable "openai_api_key" {
  default   = ""
  sensitive = true
}

variable "gemini_api_key" {
  default   = ""
  sensitive = true
}

variable "dhan_client_id" {
  default   = ""
  sensitive = true
}

variable "dhan_access_token" {
  default   = ""
  sensitive = true
}

variable "fyers_app_id" {
  default   = ""
  sensitive = true
}

variable "fyers_access_token" {
  default   = ""
  sensitive = true
}

variable "telegram_bot_token" {
  default   = ""
  sensitive = true
}

variable "telegram_chat_id" {
  default = ""
}

variable "trading_capital" {
  default = "500000"
}
