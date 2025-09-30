#!/bin/bash

# ============================================
# NewsRaag Multi-Region Deployment Script
# ============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if logged into Azure
    if ! az account show &> /dev/null; then
        error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Function to validate configuration
validate_config() {
    log "📋 Validating configuration..."
    
    if [ ! -f "environments/prod.tfvars" ]; then
        error "Configuration file environments/prod.tfvars not found!"
        exit 1
    fi
    
    # Check if Application Insights name is updated
    if grep -q "newscrawler-insights" environments/prod.tfvars; then
        warning "Please update existing_application_insights_name in environments/prod.tfvars"
        echo "   Run: az monitor app-insights component list --output table"
        echo "   Then update the name in environments/prod.tfvars"
        read -p "   Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    success "Configuration validation passed"
}

# Function to get Application Insights info
get_app_insights_info() {
    log "🔍 Discovering Application Insights resources..."
    
    echo ""
    echo "Available Application Insights resources:"
    az monitor app-insights component list --output table
    echo ""
    
    log "ℹ️  Update environments/prod.tfvars with the correct names from above"
}

# Function to estimate costs
show_cost_estimate() {
    log "💰 Cost Estimation (Basic B1 tier):"
    echo ""
    echo "  📊 App Services (3x Basic B1):  ~$39/month"
    echo "  🌐 Traffic Manager:             ~$1/month"  
    echo "  📈 Application Insights:        Using existing"
    echo "  🔔 Alerts:                      Free tier"
    echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  💵 Total Estimated Cost:       ~$40-45/month"
    echo ""
    warning "This is Basic tier for testing. Scale up for production loads."
}

# Function to deploy infrastructure
deploy() {
    log "🚀 Starting Terraform deployment..."
    
    # Initialize Terraform
    log "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log "Creating deployment plan..."
    terraform plan -var-file="environments/prod.tfvars" -out="tfplan"
    
    # Show plan summary
    echo ""
    log "📋 Deployment Plan Summary:"
    terraform show -json tfplan | jq -r '.resource_changes[] | "\(.change.actions[0]) \(.address)"' | head -20
    echo ""
    
    # Confirm deployment
    read -p "🤔 Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Deployment cancelled"
        exit 0
    fi
    
    # Apply deployment
    log "Deploying infrastructure..."
    terraform apply "tfplan"
    
    # Clean up plan file
    rm tfplan
    
    success "🎉 Deployment completed successfully!"
}

# Function to show outputs
show_outputs() {
    log "📊 Deployment Results:"
    echo ""
    terraform output -json | jq -r '.deployment_summary.value | "Environment: \(.environment)"'
    terraform output -json | jq -r '.deployment_summary.value | "App Service Tier: \(.app_service_tier)"'
    echo ""
    
    log "🌐 Access URLs:"
    terraform output quick_urls
    echo ""
    
    log "📈 Next Steps:"
    echo "  1. Test health endpoints: curl https://your-traffic-manager-url/health"
    echo "  2. Update your CI/CD pipeline to deploy to all 3 regions"
    echo "  3. Monitor performance in Application Insights"
    echo "  4. Scale up tier when ready for production traffic"
}

# Function to run health checks
health_check() {
    log "🏥 Running health checks..."
    
    # Get URLs from Terraform output
    GLOBAL_URL=$(terraform output -raw traffic_manager_url 2>/dev/null || echo "")
    
    if [ -n "$GLOBAL_URL" ]; then
        log "Testing global endpoint: $GLOBAL_URL/health"
        if curl -f -s "$GLOBAL_URL/health" > /dev/null; then
            success "Global endpoint is healthy ✅"
        else
            warning "Global endpoint health check failed ⚠️"
        fi
    else
        warning "Could not retrieve global URL from Terraform output"
    fi
}

# Main execution
main() {
    echo ""
    log "🚀 NewsRaag Multi-Region Deployment"
    echo "   This will deploy your API to US, Europe, and India regions"
    echo ""
    
    # Change to terraform directory
    if [ ! -f "main.tf" ]; then
        cd terraform 2>/dev/null || {
            error "Please run this script from the project root or terraform directory"
            exit 1
        }
    fi
    
    case "${1:-deploy}" in
        "info")
            get_app_insights_info
            ;;
        "cost")
            show_cost_estimate
            ;;
        "plan")
            check_prerequisites
            validate_config
            terraform init
            terraform plan -var-file="environments/prod.tfvars"
            ;;
        "deploy")
            check_prerequisites
            validate_config
            show_cost_estimate
            deploy
            show_outputs
            ;;
        "output")
            show_outputs
            ;;
        "health")
            health_check
            ;;
        "destroy")
            warning "This will destroy ALL infrastructure!"
            read -p "Are you absolutely sure? Type 'yes' to continue: " confirm
            if [ "$confirm" = "yes" ]; then
                terraform destroy -var-file="environments/prod.tfvars"
            else
                log "Destruction cancelled"
            fi
            ;;
        *)
            echo "Usage: $0 {info|cost|plan|deploy|output|health|destroy}"
            echo ""
            echo "Commands:"
            echo "  info    - Show available Application Insights resources"
            echo "  cost    - Show cost estimation"
            echo "  plan    - Show deployment plan without executing"
            echo "  deploy  - Deploy infrastructure (default)"
            echo "  output  - Show deployment outputs"
            echo "  health  - Test deployed endpoints"
            echo "  destroy - Destroy all infrastructure (careful!)"
            ;;
    esac
}

# Run main function
main "$@"
