terraform {
  backend "local" {
  }
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
    }
    azuread = {
      source  = "hashicorp/azuread"
    }
  }
}

locals {
  yaml_settings     = yamldecode(file("../settings.yaml"))
  ip_whitelist_cidr = local.yaml_settings.ip_addresses_cidr
  ip_whitelist      = local.yaml_settings.ip_addresses
  app_name          = "sbt-ai"
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {
}

data "azuread_service_principal" "sp-sbt-ai"{
  display_name = local.app_name
}

data "azurerm_resource_group" "rg-data" {
    name = "rg-${local.app_name}-data"
}

resource "azurerm_key_vault" "kv-sbt-ai" {
  name                        = "kv-${local.app_name}"
  location                    = data.azurerm_resource_group.rg-data.location
  resource_group_name         = data.azurerm_resource_group.rg-data.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  network_acls {
    bypass = "AzureServices"
    default_action = "Deny"
    ip_rules = local.ip_whitelist_cidr
  }
}

resource "azurerm_cognitive_account" "cog-acc-sbt-ai" {
  name                = "cog-acc-speech-${local.app_name}"
  location            = data.azurerm_resource_group.rg-data.location
  resource_group_name = data.azurerm_resource_group.rg-data.name
  kind                = "SpeechServices"

  sku_name = "S0"
  custom_subdomain_name = "cog-acc-speech-${local.app_name}"

  network_acls {
    default_action = "Deny"
    ip_rules = local.ip_whitelist
  }

  identity {
    type = "SystemAssigned"
  }

}