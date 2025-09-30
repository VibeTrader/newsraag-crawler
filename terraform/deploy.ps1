# ============================================
# NewsRaag Multi-Region Deployment Script (PowerShell)
# ============================================

param(
    [string]$Action = "deploy"
)

# Function to write colored output
function Write-Log {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Log "🔍 Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if (!(Get-Command "az" -ErrorAction SilentlyContinue)) {
        Write-Error "Azure CLI is not installed. Please install it first."
        exit 1
    }
    
    # Check if Terraform is installed
    if (!(Get-Command "terraform" -ErrorAction SilentlyContinue)) {
        Write-Error "Terraform is not installed. Please install it first."
        exit 1
    }
    
    # Check if logged into Azure
    try {
        az account show --output none
    }
    catch {
        Write-Error "Not logged into Azure. Please run 'az login' first."
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Function to validate configuration
function Test-Configuration {
    Write-Log "📋 Validating configuration..."
    
    if (!(Test-Path "environments\prod.tfvars")) {
        Write-Error "Configuration file environments\prod.tfvars not found!"
        exit 1
    }
    
    # Check if Application Insights name is updated
    $content = Get-Content "environments\prod.tfvars" -Raw
    if ($content -match "newscrawler-insights") {
        Write-Warning "Please update existing_application_insights_name in environments\prod.tfvars"
        Write-Host "   Run: az monitor app-insights component list --output table"
        Write-Host "   Then update the name in environments\prod.tfvars"
        $continue = Read-Host "   Continue anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    }
    
    Write-Success "Configuration validation passed"
}

# Function to get Application Insights info
function Get-AppInsightsInfo {
    Write-Log "🔍 Discovering Application Insights resources..."
    
    Write-Host ""
    Write-Host "Available Application Insights resources:"
    az monitor app-insights component list --output table
    Write-Host ""
    
    Write-Log "ℹ️  Update environments\prod.tfvars with the correct names from above"
}

# Function to show cost estimate
function Show-CostEstimate {
    Write-Log "💰 Cost Estimation (Basic B1 tier):"
    Write-Host ""
    Write-Host "  📊 App Services (3x Basic B1):  ~`$39/month"
    Write-Host "  🌐 Traffic Manager:             ~`$1/month"
    Write-Host "  📈 Application Insights:        Using existing"
    Write-Host "  🔔 Alerts:                      Free tier"
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "  💵 Total Estimated Cost:       ~`$40-45/month"
    Write-Host ""
    Write-Warning "This is Basic tier for testing. Scale up for production loads."
}

# Function to deploy infrastructure
function Start-Deployment {
    Write-Log "🚀 Starting Terraform deployment..."
    
    # Initialize Terraform
    Write-Log "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    Write-Log "Creating deployment plan..."
    terraform plan -var-file="environments\prod.tfvars" -out="tfplan"
    
    # Show plan summary
    Write-Host ""
    Write-Log "📋 Deployment Plan Summary created"
    Write-Host ""
    
    # Confirm deployment
    $continue = Read-Host "🤔 Continue with deployment? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Log "Deployment cancelled"
        exit 0
    }
    
    # Apply deployment
    Write-Log "Deploying infrastructure..."
    terraform apply "tfplan"
    
    # Clean up plan file
    Remove-Item "tfplan" -ErrorAction SilentlyContinue
    
    Write-Success "🎉 Deployment completed successfully!"
}

# Function to show outputs
function Show-Outputs {
    Write-Log "📊 Deployment Results:"
    Write-Host ""
    
    # Get deployment summary
    $summary = terraform output -json deployment_summary | ConvertFrom-Json
    Write-Host "Environment: $($summary.environment)"
    Write-Host "App Service Tier: $($summary.app_service_tier)"
    Write-Host ""
    
    Write-Log "🌐 Access URLs:"
    terraform output quick_urls
    Write-Host ""
    
    Write-Log "📈 Next Steps:"
    Write-Host "  1. Test health endpoints: curl https://your-traffic-manager-url/health"
    Write-Host "  2. Update your CI/CD pipeline to deploy to all 3 regions"
    Write-Host "  3. Monitor performance in Application Insights"
    Write-Host "  4. Scale up tier when ready for production traffic"
}

# Function to run health checks
function Test-HealthChecks {
    Write-Log "🏥 Running health checks..."
    
    try {
        $globalUrl = terraform output -raw traffic_manager_url
        Write-Log "Testing global endpoint: $globalUrl/health"
        
        $response = Invoke-WebRequest -Uri "$globalUrl/health" -Method GET -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "Global endpoint is healthy ✅"
        }
        else {
            Write-Warning "Global endpoint returned status: $($response.StatusCode) ⚠️"
        }
    }
    catch {
        Write-Warning "Global endpoint health check failed: $($_.Exception.Message) ⚠️"
    }
}

# Main execution
function Main {
    Write-Host ""
    Write-Log "🚀 NewsRaag Multi-Region Deployment"
    Write-Host "   This will deploy your API to US, Europe, and India regions"
    Write-Host ""
    
    # Change to terraform directory if needed
    if (!(Test-Path "main.tf")) {
        if (Test-Path "terraform\main.tf") {
            Set-Location "terraform"
        }
        else {
            Write-Error "Please run this script from the project root or terraform directory"
            exit 1
        }
    }
    
    switch ($Action.ToLower()) {
        "info" {
            Get-AppInsightsInfo
        }
        "cost" {
            Show-CostEstimate
        }
        "plan" {
            Test-Prerequisites
            Test-Configuration
            terraform init
            terraform plan -var-file="environments\prod.tfvars"
        }
        "deploy" {
            Test-Prerequisites
            Test-Configuration
            Show-CostEstimate
            Start-Deployment
            Show-Outputs
        }
        "output" {
            Show-Outputs
        }
        "health" {
            Test-HealthChecks
        }
        "destroy" {
            Write-Warning "This will destroy ALL infrastructure!"
            $confirm = Read-Host "Are you absolutely sure? Type 'yes' to continue"
            if ($confirm -eq "yes") {
                terraform destroy -var-file="environments\prod.tfvars"
            }
            else {
                Write-Log "Destruction cancelled"
            }
        }
        default {
            Write-Host "Usage: .\deploy.ps1 [-Action <action>]"
            Write-Host ""
            Write-Host "Actions:"
            Write-Host "  info    - Show available Application Insights resources"
            Write-Host "  cost    - Show cost estimation"
            Write-Host "  plan    - Show deployment plan without executing"
            Write-Host "  deploy  - Deploy infrastructure (default)"
            Write-Host "  output  - Show deployment outputs"
            Write-Host "  health  - Test deployed endpoints"
            Write-Host "  destroy - Destroy all infrastructure (careful!)"
        }
    }
}

# Run main function
Main
