# ============================================
# Main Terraform Configuration for NewsRaag Multi-Region Deployment  
# Fresh deployment approach - 3 new App Services
# ============================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Data sources
data "azurerm_client_config" "current" {}

# Local values for consistent naming
locals {
  project_name = "newsraag"
  environment  = var.environment
  
  regions = {
    us = {
      location      = "East US"
      short_name    = "us"
    }
    europe = {
      location      = "West Europe"
      short_name    = "eu"
    }
    india = {
      location      = "South India"
      short_name    = "in"
    }
  }
  
  # Tags applied to all resources
  common_tags = {
    Environment = var.environment
    Project     = local.project_name
    ManagedBy   = "Terraform"
    Owner       = "NewsRaag-Team"
    DeployedAt  = timestamp()
  }
}

# Resource Group for global resources (Traffic Manager, shared monitoring)
resource "azurerm_resource_group" "global" {
  name     = "rg-${local.project_name}-global-${local.environment}"
  location = "East US"
  tags     = local.common_tags
}

# Data source for existing Application Insights (we'll use your existing one)
data "azurerm_application_insights" "existing" {
  name                = var.existing_application_insights_name
  resource_group_name = var.existing_application_insights_rg
}

# Deploy US App Service
module "app_service_us" {
  source = "./modules/app-service"
  
  project_name     = local.project_name
  environment      = local.environment
  region           = local.regions.us
  
  # App Service configuration - Basic tier for now
  app_service_plan_sku  = var.app_service_plan_sku
  app_service_plan_tier = var.app_service_plan_tier
  min_instances        = var.min_instances
  max_instances        = var.max_instances
  
  # Use existing Application Insights
  application_insights_id                = data.azurerm_application_insights.existing.id
  application_insights_instrumentation_key = data.azurerm_application_insights.existing.instrumentation_key
  application_insights_connection_string = data.azurerm_application_insights.existing.connection_string
  
  # Application configuration
  app_settings = var.app_settings
  
  common_tags = local.common_tags
}

# Deploy Europe App Service
module "app_service_europe" {
  source = "./modules/app-service"
  
  project_name     = local.project_name
  environment      = local.environment
  region           = local.regions.europe
  
  # App Service configuration - Basic tier for now
  app_service_plan_sku  = var.app_service_plan_sku
  app_service_plan_tier = var.app_service_plan_tier
  min_instances        = var.min_instances
  max_instances        = var.max_instances
  
  # Use existing Application Insights
  application_insights_id                = data.azurerm_application_insights.existing.id
  application_insights_instrumentation_key = data.azurerm_application_insights.existing.instrumentation_key
  application_insights_connection_string = data.azurerm_application_insights.existing.connection_string
  
  # Application configuration
  app_settings = var.app_settings
  
  common_tags = local.common_tags
}

# Deploy India App Service
module "app_service_india" {
  source = "./modules/app-service"
  
  project_name     = local.project_name
  environment      = local.environment
  region           = local.regions.india
  
  # App Service configuration - Basic tier for now
  app_service_plan_sku  = var.app_service_plan_sku
  app_service_plan_tier = var.app_service_plan_tier
  min_instances        = var.min_instances
  max_instances        = var.max_instances
  
  # Use existing Application Insights
  application_insights_id                = data.azurerm_application_insights.existing.id
  application_insights_instrumentation_key = data.azurerm_application_insights.existing.instrumentation_key
  application_insights_connection_string = data.azurerm_application_insights.existing.connection_string
  
  # Application configuration
  app_settings = var.app_settings
  
  common_tags = local.common_tags
}
# Traffic Manager for global load balancing
module "traffic_manager" {
  source = "./modules/traffic-manager"
  
  project_name         = local.project_name
  environment          = local.environment
  resource_group_name  = azurerm_resource_group.global.name
  
  # All three app service endpoints
  existing_app_service_id   = module.app_service_us.app_service_id
  existing_app_service_name = module.app_service_us.app_service_name
  
  europe_app_service_id   = module.app_service_europe.app_service_id
  europe_app_service_name = module.app_service_europe.app_service_name
  
  india_app_service_id   = module.app_service_india.app_service_id
  india_app_service_name = module.app_service_india.app_service_name
  
  # Health check configuration
  health_check_path = var.health_check_path
  
  # Use existing Application Insights for availability tests
  application_insights_id = data.azurerm_application_insights.existing.id
  
  common_tags = local.common_tags
}

# Enhanced monitoring for multi-region setup
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name         = local.project_name
  environment          = local.environment
  resource_group_name  = azurerm_resource_group.global.name
  
  # Use existing Application Insights
  application_insights_id = data.azurerm_application_insights.existing.id
  
  # All app services to monitor
  app_services = {
    us = {
      id     = module.app_service_us.app_service_id
      name   = module.app_service_us.app_service_name
      region = "us"
    }
    europe = {
      id     = module.app_service_europe.app_service_id
      name   = module.app_service_europe.app_service_name
      region = "europe"
    }
    india = {
      id     = module.app_service_india.app_service_id
      name   = module.app_service_india.app_service_name
      region = "india"
    }
  }
  
  # Alert configuration
  alert_email       = var.alert_email
  slack_webhook_url = var.slack_webhook_url
  
  common_tags = local.common_tags
}
