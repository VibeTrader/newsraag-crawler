# ============================================
# Variables for NewsRaag Multi-Region Fresh Deployment
# ============================================

# Environment Configuration
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# Existing Application Insights (we'll use your existing one)
variable "existing_application_insights_name" {
  description = "Name of existing Application Insights resource"
  type        = string
  # You'll need to update this with your actual App Insights name
  default     = "newsraag-insights" # Update this
}

variable "existing_application_insights_rg" {
  description = "Resource group of existing Application Insights"
  type        = string
  # You'll need to update this with your actual RG name where App Insights is located
  default     = "newsraag-rg" # Update this
}

# App Service Configuration - Basic tier for now
variable "app_service_plan_sku" {
  description = "SKU for App Service Plans (Basic for now, will scale later)"
  type        = string
  default     = "B1" # Basic tier - cheapest option for testing
}

variable "app_service_plan_tier" {
  description = "Tier for App Service Plans"
  type        = string
  default     = "Basic"
}

# Scaling Configuration (Basic tier has limited scaling)
variable "min_instances" {
  description = "Minimum number of instances for auto-scaling"
  type        = number
  default     = 1 # Basic tier minimum
}

variable "max_instances" {
  description = "Maximum number of instances for auto-scaling"
  type        = number
  default     = 3 # Basic tier maximum
}

# Application Settings (passed to all App Services)
variable "app_settings" {
  description = "Application settings for App Services"
  type        = map(string)
  default = {
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    WEBSITES_PORT                       = "8000"
    SCM_DO_BUILD_DURING_DEPLOYMENT      = "true"
    ENABLE_ORYX_BUILD                   = "true"
    
    # Python specific
    PYTHON_VERSION = "3.12"
    
    # Application specific
    ENVIRONMENT = "production"
    
    # Health check
    HEALTH_CHECK_ENABLED = "true"
    
    # You'll add your actual app settings here:
    # OPENAI_BASE_URL = "https://your-endpoint.openai.azure.com/"
    # AZURE_OPENAI_API_VERSION = "2024-02-01"
    # Add other environment variables from your .env file
  }
  sensitive = false # Set to true if you add sensitive values
}

# Health Check Configuration
variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health" # Update based on your app's health endpoint
}

# Monitoring and Alerting
variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = "admin@yourcompany.com" # Update with your email
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  default     = "" # You mentioned you have this webhook
  sensitive   = true
}
