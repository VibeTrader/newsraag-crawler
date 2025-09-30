# ============================================
# Development Environment Configuration
# ============================================

environment = "dev"

# Basic tier - cheapest for development
app_service_plan_sku  = "B1"
app_service_plan_tier = "Basic"

# Minimal scaling for dev
min_instances = 1
max_instances = 2

# Your existing Application Insights details
existing_application_insights_name = "newscrawler"
existing_application_insights_rg   = "ragvector"

# Development app settings
app_settings = {
  WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
  WEBSITES_PORT                       = "8000"
  SCM_DO_BUILD_DURING_DEPLOYMENT      = "true"
  ENABLE_ORYX_BUILD                   = "true"
  PYTHON_VERSION                      = "3.12"
  ENVIRONMENT                         = "development"
  DEBUG                              = "true"
  
  # Add your development environment variables here
  # LLM_CLEANING_ENABLED = "false"
  # LLM_TRACK_USAGE = "false"
}

# Alert settings for dev
alert_email = "dev-team@yourcompany.com"
slack_webhook_url = "" # Leave empty for dev if you don't want Slack alerts

# Health check endpoint
health_check_path = "/health"
