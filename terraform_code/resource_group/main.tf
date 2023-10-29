terraform {
  backend "local" {
  }
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "ai_rg" {
    name = "rg-sbt-ai-data"
    location = "eastus"
}

resource "azurerm_resource_group" "ai_network" {
    name = "rg-sbt-ai-network"
    location = "eastus"
}