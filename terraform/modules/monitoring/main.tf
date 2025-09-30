# ============================================
# Monitoring Module - Multi-Region Alerts and Dashboards
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Action Group for alerts (Email + Slack)
resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  short_name          = "newsraag"
  
  # Email notifications
  email_receiver {
    name          = "admin-email"
    email_address = var.alert_email
  }
  
  # Slack webhook notifications (if provided)
  dynamic "webhook_receiver" {
    for_each = var.slack_webhook_url != "" ? [1] : []
    content {
      name                    = "slack-alerts"
      service_uri             = var.slack_webhook_url
      use_common_alert_schema = true
    }
  }
  
  tags = var.common_tags
}

# Metric Alerts for each App Service
resource "azurerm_monitor_metric_alert" "high_response_time" {
  for_each = var.app_services
  
  name                = "alert-response-time-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High response time alert for ${each.key} region"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "AverageResponseTime"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 5000 # 5 seconds
    
    dimension {
      name     = "Instance"
      operator = "Include"
      values   = ["*"]
    }
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# HTTP 5xx Error Rate Alerts
resource "azurerm_monitor_metric_alert" "high_error_rate" {
  for_each = var.app_services
  
  name                = "alert-error-rate-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High error rate alert for ${each.key} region"
  severity            = 1 # Critical
  frequency           = "PT1M"
  window_size         = "PT5M"
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10 # More than 10 5xx errors in 5 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}
# CPU Usage Alerts
resource "azurerm_monitor_metric_alert" "high_cpu" {
  for_each = var.app_services
  
  name                = "alert-cpu-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High CPU usage alert for ${each.key} region"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "CpuPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80 # 80% CPU usage
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Memory Usage Alerts
resource "azurerm_monitor_metric_alert" "high_memory" {
  for_each = var.app_services
  
  name                = "alert-memory-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High memory usage alert for ${each.key} region"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "MemoryPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 85 # 85% memory usage
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Availability Alert (for Traffic Manager)
resource "azurerm_monitor_metric_alert" "availability" {
  count = var.application_insights_id != null ? 1 : 0
  
  name                = "alert-availability-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [var.application_insights_id]
  description         = "Low availability alert for global endpoint"
  severity            = 1 # Critical
  frequency           = "PT1M"
  window_size         = "PT5M"
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "availabilityResults/availabilityPercentage"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 90 # Less than 90% availability
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}
