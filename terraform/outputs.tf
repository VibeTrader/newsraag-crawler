# ============================================
# Outputs for NewsRaag Multi-Region Fresh Deployment
# ============================================

# Global Resources
output "global_resource_group_name" {
  description = "Name of the global resource group"
  value       = azurerm_resource_group.global.name
}

# Traffic Manager
output "traffic_manager_fqdn" {
  description = "FQDN of the Traffic Manager endpoint - Your main global URL"
  value       = module.traffic_manager.fqdn
}

output "traffic_manager_url" {
  description = "Complete URL of the Traffic Manager endpoint"
  value       = "https://${module.traffic_manager.fqdn}"
}

# US Region
output "us_app_service_name" {
  description = "Name of US App Service"
  value       = module.app_service_us.app_service_name
}

output "us_app_service_url" {
  description = "URL of US App Service"
  value       = module.app_service_us.app_service_url
}

output "us_resource_group_name" {
  description = "Name of US resource group"
  value       = module.app_service_us.resource_group_name
}

# Europe Region
output "europe_app_service_name" {
  description = "Name of Europe App Service"
  value       = module.app_service_europe.app_service_name
}

output "europe_app_service_url" {
  description = "URL of Europe App Service"
  value       = module.app_service_europe.app_service_url
}

output "europe_resource_group_name" {
  description = "Name of Europe resource group"
  value       = module.app_service_europe.resource_group_name
}

# India Region
output "india_app_service_name" {
  description = "Name of India App Service"
  value       = module.app_service_india.app_service_name
}

output "india_app_service_url" {
  description = "URL of India App Service"
  value       = module.app_service_india.app_service_url
}

output "india_resource_group_name" {
  description = "Name of India resource group"
  value       = module.app_service_india.resource_group_name
}

# Monitoring
output "action_group_name" {
  description = "Name of the action group for alerts"
  value       = module.monitoring.action_group_name
}

output "monitoring_summary" {
  description = "Summary of monitoring setup"
  value       = module.monitoring.monitoring_summary
}

# Complete Deployment Summary
output "deployment_summary" {
  description = "Complete summary of your multi-region deployment"
  value = {
    environment           = var.environment
    traffic_manager_url   = "https://${module.traffic_manager.fqdn}"
    
    regions_deployed = {
      us = {
        name = module.app_service_us.app_service_name
        url  = module.app_service_us.app_service_url
        resource_group = module.app_service_us.resource_group_name
      }
      europe = {
        name = module.app_service_europe.app_service_name  
        url  = module.app_service_europe.app_service_url
        resource_group = module.app_service_europe.resource_group_name
      }
      india = {
        name = module.app_service_india.app_service_name
        url  = module.app_service_india.app_service_url
        resource_group = module.app_service_india.resource_group_name
      }
    }
    
    app_service_tier     = var.app_service_plan_sku
    monitoring_enabled   = true
    alerts_configured    = true
    health_checks_enabled = true
  }
}

# Quick Access URLs (for easy copy-paste)
output "quick_urls" {
  description = "Quick access URLs for testing"
  value = {
    "🌍 Global (Traffic Manager)" = "https://${module.traffic_manager.fqdn}"
    "🇺🇸 US Direct"             = module.app_service_us.app_service_url
    "🇪🇺 Europe Direct"          = module.app_service_europe.app_service_url  
    "🇮🇳 India Direct"           = module.app_service_india.app_service_url
    
    "Health Checks:" = "Add ${var.health_check_path} to any URL above"
  }
}
