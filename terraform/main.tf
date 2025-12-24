locals {
  project_name = var.project_name
  environment  = var.environment
  
  # Base tags applied to all resources (Policy Compliant)
  base_tags = {
    "environment"  = var.environment
    "project"      = var.project_name
    "created-by"   = var.created_by
    "created-date" = var.created_date
    "Terraform"    = "true"
  }
}

# Core Infrastructure RG
data "azurerm_resource_group" "rg" {
  name = var.existing_resource_group_name
}

# ACR
resource "azurerm_container_registry" "acr" {
  name                = var.container_registry_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = merge(local.base_tags, { "service" = "apiacrimage" })
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "log" {
  name                = "logs-${local.project_name}-${local.environment}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = merge(local.base_tags, { "service" = "logging" })
}

# Application Insights
resource "azurerm_application_insights" "app" {
  name                = "appintr-${local.project_name}-${local.environment}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.log.id
  application_type    = "web"

  tags = merge(local.base_tags, { "service" = "logging" })
}

# Container App Environment
resource "azurerm_container_app_environment" "env" {
  name                       = "env-${local.project_name}-${local.environment}"
  location                   = data.azurerm_resource_group.rg.location
  resource_group_name        = data.azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.log.id

  tags = merge(local.base_tags, { "service" = "compute" })
}

# Container App Job
resource "azurerm_container_app_job" "job" {
  name                = "job-${local.project_name}-${local.environment}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  container_app_environment_id = azurerm_container_app_environment.env.id

  replica_timeout_in_seconds = 1800 # 30 minutes max execution time
  replica_retry_limit        = 1
  schedule_trigger_config {
    cron_expression = "0 */3 * * *" # Every 3 hours
    parallelism     = 1
    replica_completion_count = 1
  }

  template {
    container {
      name   = "newsraag-crawler"
      image  = "${azurerm_container_registry.acr.login_server}/${var.image_name}:${var.image_tag}"
      cpu    = 0.5
      memory = "1.0Gi"

      command = ["python", "main.py", "--single-cycle"]

      # --- Azure OpenAI ---
      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }
      env {
        name        = "OPENAI_BASE_URL"
        value       = var.openai_base_url
      }
      env {
        name        = "AZURE_OPENAI_API_VERSION"
        value       = var.azure_openai_api_version
      }
      env {
        name        = "AZURE_OPENAI_DEPLOYMENT"
        value       = var.azure_openai_deployment
      }
      env {
        name        = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value       = var.azure_openai_embedding_deployment
      }
      env {
        name        = "AZURE_OPENAI_EMBEDDING_MODEL"
        value       = var.azure_openai_embedding_model
      }
      env {
        name        = "EMBEDDING_DIMENSION"
        value       = var.embedding_dimension
      }

      # --- Qdrant ---
      env {
        name        = "QDRANT_URL"
        value       = var.qdrant_url
      }
      env {
        name        = "QDRANT_API_KEY"
        secret_name = "qdrant-api-key"
      }
      env {
        name        = "QDRANT_COLLECTION_NAME"
        value       = var.qdrant_collection_name
      }
      env {
        name        = "VECTOR_BACKEND"
        value       = var.vector_backend
      }

      # --- Azure Storage ---
      env {
        name        = "AZ_ACCOUNT_NAME"
        value       = var.az_account_name
      }
      env {
        name        = "AZ_ACCOUNT_KEY"
        secret_name = "az-account-key"
      }
      env {
        name        = "AZ_BLOB_ACCESS_KEY"
        secret_name = "az-account-key"
      }
      env {
        name        = "AZ_CONTAINER_NAME"
        value       = var.az_container_name
      }

      # --- Monitoring ---
      env {
        name        = "APPINSIGHTS_INSTRUMENTATIONKEY"
        secret_name = "appinsights-key"
      }
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }
      env {
        name = "ApplicationInsightsAgent_EXTENSION_VERSION"
        value = "~3"
      }
      env {
        name = "XDT_MicrosoftApplicationInsights_Mode"
        value = "recommended"
      }
    }
  }

  # --- Secrets Definition ---
  secret {
    name  = "openai-api-key"
    value = var.openai_api_key
  }
  secret {
    name  = "qdrant-api-key"
    value = var.qdrant_api_key
  }
  secret {
    name  = "az-account-key"
    value = var.az_account_key
  }

  # Secrets from newly created resource
  secret {
    name  = "appinsights-key"
    value = azurerm_application_insights.app.instrumentation_key
  }
  secret {
    name  = "appinsights-connection-string"
    value = azurerm_application_insights.app.connection_string
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }
  
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  tags = merge(local.base_tags, { "service" = "api" })

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]
  }
}
