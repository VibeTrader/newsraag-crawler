# ============================================
# Monitoring Module Outputs
# ============================================

output "action_group_id" {
  description = "ID of the action group"
  value       = azurerm_monitor_action_group.main.id
}

output "action_group_name" {
  description = "Name of the action group"
  value       = azurerm_monitor_action_group.main.name
}

output "alert_ids" {
  description = "IDs of all created alerts"
  value = {
    response_time_alerts = { for k, v in azurerm_monitor_metric_alert.high_response_time : k => v.id }
    error_rate_alerts   = { for k, v in azurerm_monitor_metric_alert.high_error_rate : k => v.id }
    cpu_alerts          = { for k, v in azurerm_monitor_metric_alert.high_cpu : k => v.id }
    memory_alerts       = { for k, v in azurerm_monitor_metric_alert.high_memory : k => v.id }
    availability_alert  = var.application_insights_id != null ? azurerm_monitor_metric_alert.availability[0].id : null
  }
}

output "monitoring_summary" {
  description = "Summary of monitoring setup"
  value = {
    action_group    = azurerm_monitor_action_group.main.name
    alerts_created  = length(azurerm_monitor_metric_alert.high_response_time) + length(azurerm_monitor_metric_alert.high_error_rate) + length(azurerm_monitor_metric_alert.high_cpu) + length(azurerm_monitor_metric_alert.high_memory)
    regions_monitored = keys(var.app_services)
    email_notifications = var.alert_email
    slack_enabled      = var.slack_webhook_url != ""
  }
}
