terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  backend "azurerm" {
    # Backend configuration should be provided via partial configuration or CLI
    # resource_group_name  = "tfstate-rg"
    # storage_account_name = "tfstate"
    # container_name       = "tfstate"
    # key                  = "newsraag-crawler.tfstate"
  }
}

provider "azurerm" {
  features {}
}
