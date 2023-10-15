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

provider "azurerm" {
  features {}
}

data "azuread_client_config" "current" {
}

resource "azuread_application" "sbt-ai-app" {
  display_name = "sbt-ai"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "sp-sbt-ai" {
  application_id               = azuread_application.sbt-ai-app.application_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]

}