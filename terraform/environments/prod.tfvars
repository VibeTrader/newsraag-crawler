# ============================================
# Production Environment Configuration
# ============================================

# Basic tier configuration for testing
environment = "prod"

# Update these with your actual Azure resource names
existing_application_insights_name = "newscrawler-insights"  # Check in Azure Portal
existing_application_insights_rg   = "DefaultResourceGroup-EUS"  # Check in Azure Portal

# Basic tier for cost-effective testing
app_service_plan_sku  = "B1"  # Basic tier - $13.14/month per region
app_service_plan_tier = "Basic"

# Basic tier scaling limits
min_instances = 1
max_instances = 3

# Health check endpoint (update based on your app)
health_check_path = "/health"  # Make sure your app has this endpoint

# Your contact information
alert_email = "your-email@domain.com"  # Update with your email

# Slack webhook (if you have one)
slack_webhook_url = ""  # Add your Slack webhook URL here

# Application settings for your NewsRaag app
app_settings = {
  # Basic settings
  WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
  WEBSITES_PORT                       = "8000"
  SCM_DO_BUILD_DURING_DEPLOYMENT      = "true"
  ENABLE_ORYX_BUILD                   = "true"
  
  # Python configuration
  PYTHON_VERSION = "3.12"
  
  # Application environment
  ENVIRONMENT = "production"
  
  # Health check
  HEALTH_CHECK_ENABLED = "true"
  
  # Add your application-specific settings here:
  # OPENAI_BASE_URL = "https://your-endpoint.openai.azure.com/"
  # AZURE_OPENAI_API_VERSION = "2024-02-01"
  # AZURE_OPENAI_DEPLOYMENT = "your-deployment-name"
  # AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "your-embedding-deployment"
  # AZURE_OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
  # EMBEDDING_DIMENSION = "3072"
  # LLM_CLEANING_ENABLED = "true"
  # LLM_TOKEN_LIMIT_PER_REQUEST = "4000"
  # LLM_MAX_CONTENT_LENGTH = "100000"
  # LLM_TEMPERATURE = "0.1"
  # LLM_TRACK_USAGE = "true"
  # LLM_DAILY_TOKEN_LIMIT = "1000000"
  # LLM_MONTHLY_TOKEN_LIMIT = "30000000"
  # LLM_ALERT_AT_PERCENT = "80"
}
