# NewsRaag Multi-Region Terraform Infrastructure

This Terraform configuration deploys the NewsRaag API to 3 regions (US, Europe, India) with Traffic Manager for global load balancing.

## Architecture Overview

```
Internet → Traffic Manager → App Service (US/Europe/India)
                         → Shared Application Insights
                         → Centralized Monitoring & Alerts
```

## Prerequisites

1. **Azure CLI installed and logged in**
   ```bash
   az login
   ```

2. **Terraform installed** (version >= 1.0)

3. **Existing Application Insights resource**
   - This setup reuses your existing Application Insights
   - Update the names in `environments/prod.tfvars`

## Quick Start

### 1. Update Configuration
Edit `terraform/environments/prod.tfvars`:
```hcl
# Update with your actual resource names
existing_application_insights_name = "your-actual-insights-name"
existing_application_insights_rg   = "your-actual-resource-group"

# Update with your email
alert_email = "your-email@domain.com"

# Add your Slack webhook (optional)
slack_webhook_url = "https://hooks.slack.com/services/..."
```

### 2. Find Your Application Insights Details
```bash
# List Application Insights resources
az monitor app-insights component list --output table

# Get specific details
az monitor app-insights component show --app "your-insights-name" --resource-group "your-rg-name"
```

### 3. Deploy Infrastructure
```bash
# Initialize Terraform
cd terraform
terraform init

# Plan deployment
terraform plan -var-file="environments/prod.tfvars"

# Deploy infrastructure
terraform apply -var-file="environments/prod.tfvars"
```

## What Gets Created

### Regional Resources (3x):
- **Resource Groups**: `rg-newsraag-{us/eu/in}-prod`
- **App Service Plans**: Basic B1 tier ($13.14/month each)
- **App Services**: `newsraag-{us/eu/in}-prod`
- **Auto-scaling rules**: CPU and memory-based
- **Availability tests**: Regional health monitoring

### Global Resources:
- **Traffic Manager**: Global load balancing with geographic routing
- **Action Group**: Email + Slack notifications
- **Metric Alerts**: Response time, errors, CPU, memory, availability

## Regional Routing

- **US Region**: United States, Canada, Mexico, Central America
- **Europe Region**: Europe, Middle East (Jordan, UAE, etc.), Africa
- **India Region**: India, South Asia, Southeast Asia

## Cost Estimation

- **App Services**: 3 × Basic B1 = ~$39/month
- **Traffic Manager**: ~$0.54 per million queries
- **Application Insights**: Uses existing resource
- **Alerts**: Free tier includes basic alerts

**Total**: ~$45-50/month for basic tier

## Scaling Path

### To Standard Tier:
```hcl
# In prod.tfvars
app_service_plan_sku = "S1"
app_service_plan_tier = "Standard"
min_instances = 2
max_instances = 10
```

### To Premium Tier:
```hcl
app_service_plan_sku = "P1v2"
app_service_plan_tier = "Premium"
min_instances = 2
max_instances = 20
```

## Outputs After Deployment

```bash
terraform output
```

Key outputs:
- `traffic_manager_fqdn`: Global endpoint URL
- `deployment_summary`: Complete deployment overview
- All regional App Service URLs

## Health Check Endpoint

Make sure your application has a `/health` endpoint that returns HTTP 200. Example:

```python
# In your Flask/FastAPI app
@app.route('/health')
def health_check():
    return {"status": "healthy", "region": os.environ.get('DEPLOYMENT_REGION', 'unknown')}
```

## Monitoring & Alerts

The setup creates comprehensive monitoring:
- **Response Time**: Alerts if > 5 seconds
- **Error Rate**: Alerts if > 10 5xx errors in 5 minutes
- **CPU Usage**: Alerts if > 80%
- **Memory Usage**: Alerts if > 85%
- **Availability**: Alerts if < 90%

## Next Steps

1. **Deploy this infrastructure**
2. **Update your CI/CD pipeline** to deploy to all 3 regions
3. **Test Traffic Manager routing** from different locations
4. **Monitor performance** and scale up tiers as needed
5. **Add custom domain** and SSL certificates

## Troubleshooting

### Common Issues:
1. **Application Insights not found**: Check the name and resource group in Azure Portal
2. **Health check fails**: Ensure your app has a `/health` endpoint
3. **Deployment stuck**: Check Azure resource quotas and permissions

### Useful Commands:
```bash
# Check Terraform state
terraform state list

# Get specific resource details
terraform state show 'module.app_service_us.azurerm_linux_web_app.main'

# Destroy infrastructure (be careful!)
terraform destroy -var-file="environments/prod.tfvars"
```
