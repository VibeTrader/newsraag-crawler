variable "environment" {
  description = "The deployment environment (e.g., dev, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "newsraag-crawler"
}

variable "existing_resource_group_name" {
  description = "The name of the existing core resource group"
  type        = string
  default     = "vibetraderCoreProduction"
}

variable "location" {
  description = "The Azure region to deploy resources"
  type        = string
  default     = "westus"
}

variable "container_registry_name" {
  description = "The name of the Azure Container Registry"
  type        = string
  default     = "newsraagacr"
}

variable "image_name" {
  description = "The name of the container image"
  type        = string
  default     = "newsraag-crawler"
}

variable "image_tag" {
  description = "The tag of the container image to deploy initially"
  type        = string
  default     = "latest"
}

# Azure OpenAI
variable "openai_api_key" {
  description = "Azure OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "openai_base_url" {
  description = "Azure OpenAI Base URL"
  type        = string
}

variable "azure_openai_api_version" {
  description = "Azure OpenAI API Version"
  type        = string
}

variable "azure_openai_deployment" {
  description = "Azure OpenAI Deployment Name"
  type        = string
}

variable "azure_openai_embedding_deployment" {
  description = "Azure OpenAI Embedding Deployment Name"
  type        = string
}

variable "azure_openai_embedding_model" {
  description = "Azure OpenAI Embedding Model"
  type        = string
}

variable "embedding_dimension" {
  description = "Embedding Dimension"
  type        = number
  default     = 3072 # Updating to correct default for text-embedding-3-large
}

# Qdrant
variable "qdrant_url" {
  description = "Qdrant URL"
  type        = string
}

variable "qdrant_api_key" {
  description = "Qdrant API Key"
  type        = string
  sensitive   = true
}

variable "qdrant_collection_name" {
  description = "Name of the Qdrant collection"
  type        = string
}

variable "vector_backend" {
  default = "qdrant"
}

# Azure Storage
variable "az_account_name" {
  description = "Azure Storage Account Name"
  type        = string
}

variable "az_account_key" {
  description = "Azure Storage Account Key"
  type        = string
  sensitive   = true
}

variable "az_container_name" {
  default = "dailynewsstore"
}

# Monitoring - AUTOMATED CREATION
# No need for manual instrumentation key variables anymore
