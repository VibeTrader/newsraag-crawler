# ============================================
# Traffic Manager Module Outputs
# ============================================

output "profile_name" {
  description = "Name of the Traffic Manager profile"
  value       = azurerm_traffic_manager_profile.main.name
}

output "profile_id" {
  description = "ID of the Traffic Manager profile"
  value       = azurerm_traffic_manager_profile.main.id
}

output "fqdn" {
  description = "Fully qualified domain name of the Traffic Manager"
  value       = azurerm_traffic_manager_profile.main.fqdn
}

output "dns_name" {
  description = "DNS name of the Traffic Manager"
  value       = azurerm_traffic_manager_profile.main.dns_config[0].relative_name
}

output "traffic_manager_url" {
  description = "Complete URL of the Traffic Manager endpoint"
  value       = "https://${azurerm_traffic_manager_profile.main.fqdn}"
}

# Endpoint outputs
output "us_endpoint_id" {
  description = "ID of US endpoint"
  value       = azurerm_traffic_manager_azure_endpoint.us.id
}

output "europe_endpoint_id" {
  description = "ID of Europe endpoint (if created)"
  value       = var.europe_app_service_id != null ? azurerm_traffic_manager_azure_endpoint.europe[0].id : null
}

output "india_endpoint_id" {
  description = "ID of India endpoint (if created)"
  value       = var.india_app_service_id != null ? azurerm_traffic_manager_azure_endpoint.india[0].id : null
}
