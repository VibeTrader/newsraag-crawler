# Azure Application Insights Setup and Testing

This document explains how to set up Azure Application Insights for your NewsRagnarok Crawler and verify that it's working correctly.

## 1. Create an Application Insights Resource

1. Go to the [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" and search for "Application Insights"
3. Create a new Application Insights resource:
   - Select your subscription
   - Choose a resource group (or create a new one)
   - Enter a name (e.g., "newsraag-crawler-insights")
   - Select a region close to your application deployment
   - Click "Review + create", then "Create"

## 2. Get the Connection String or Instrumentation Key

1. Once your Application Insights resource is created, go to its overview page
2. Look for either:
   - **Connection String**: Under "Configure > Properties"
   - **Instrumentation Key**: On the overview page
3. Copy the connection string (preferred) or instrumentation key

## 3. Configure Your Environment

1. Create or update your `.env` file in the root of the project
2. Add one of the following lines:
   ```
   # Option 1 (Preferred): Using Connection String
   APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx;IngestionEndpoint=https://regionname.in.applicationinsights.azure.com/
   
   # Option 2: Using Instrumentation Key
   APPINSIGHTS_INSTRUMENTATIONKEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

## 4. Test the Integration

Run the test script to verify that Application Insights is properly configured:

```bash
python tests/test_app_insights.py
```

The script will:
- Check if Application Insights is properly configured
- Send test telemetry (events, metrics, traces, exceptions)
- Display a unique test ID you can use to find your test data in Azure Portal

## 5. View Data in Azure Portal

1. Go to your Application Insights resource in Azure Portal
2. Navigate to "Logs" in the left menu
3. Run a query to find your test data (replace the test_id with the one from your test run):
   ```
   customEvents 
   | where name == "test_event" 
   | where customDimensions.test_id == "test_20250909_123456"
   ```

4. You should see the test event if the connection is working correctly

## 6. Setting Up Alerts and Dashboards

Once your integration is working, you can:

1. **Create Alerts**:
   - Go to "Alerts" in your Application Insights resource
   - Create alert rules for critical metrics like:
     - High failure rate
     - Deletion process failures
     - Memory usage spikes

2. **Create Custom Dashboards**:
   - Go to "Dashboards" in Azure Portal
   - Create a new dashboard for your crawler
   - Add widgets for key metrics:
     - Articles processed/failed
     - Cycle duration
     - Deletion metrics
     - Memory usage

3. **Set Up Availability Tests**:
   - Use the health check endpoint of your crawler
   - Configure Azure to ping this endpoint regularly
   - Get notified if your crawler becomes unavailable

## Troubleshooting

If the test script fails to connect:

1. **Check Environment Variables**:
   - Verify the connection string or instrumentation key is correctly set
   - Ensure no extra spaces or quotes are included

2. **Check Network Connectivity**:
   - Ensure your machine can reach Azure Application Insights endpoints
   - Check any firewalls or proxies that might block the connection

3. **Verify SDK Installation**:
   - Confirm the required packages are installed:
     ```
     pip install opencensus-ext-azure opencensus-ext-logging opencensus-ext-requests applicationinsights
     ```

4. **Check for Errors**:
   - Look for detailed error messages in the test script output
   - Check if any exceptions are being thrown during telemetry transmission
