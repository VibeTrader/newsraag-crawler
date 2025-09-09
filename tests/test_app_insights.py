"""
Test script to verify Azure Application Insights integration.

Usage:
    python test_app_insights.py

This script will:
1. Check if Application Insights is configured
2. Send test telemetry (events, metrics, traces, exceptions)
3. Verify the connection
"""
import os
import sys
import time
from datetime import datetime
import traceback

# Add parent directory to path to import from monitoring
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Azure Application Insights client
from monitoring.app_insights import get_app_insights
from dotenv import load_dotenv

def main():
    """Run the Application Insights test."""
    # Load environment variables
    load_dotenv()
    
    print("🔍 Testing Azure Application Insights integration...")
    
    # Get Application Insights client
    app_insights = get_app_insights()
    
    # Check if App Insights is configured
    if not app_insights.enabled:
        print("❌ Azure Application Insights is not properly configured.")
        print("   Please check your environment variables:")
        print("   - APPLICATIONINSIGHTS_CONNECTION_STRING")
        print("   - APPINSIGHTS_INSTRUMENTATIONKEY")
        return False
    
    # Print configuration
    print(f"✅ Azure Application Insights is configured.")
    if app_insights.connection_string:
        print(f"   Using connection string: {app_insights.connection_string[:20]}...")
    else:
        print(f"   Using instrumentation key: {app_insights.instrumentation_key[:10]}...")
    
    # Test sending various telemetry
    test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n🔍 Sending test telemetry with ID: {test_id}")
    
    try:
        # 1. Track event
        print("   Sending test event...")
        app_insights.track_event("test_event", {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # 2. Track metric
        print("   Sending test metric...")
        app_insights.track_metric("test_metric", 42.0, {
            "test_id": test_id,
            "unit": "count"
        })
        
        # 3. Track trace
        print("   Sending test trace...")
        app_insights.track_trace(f"Test trace message with ID: {test_id}")
        
        # 4. Track dependency
        print("   Sending test dependency...")
        app_insights.track_dependency_status("test_dependency", True, 123.45, {
            "test_id": test_id
        })
        
        # 5. Track operation
        print("   Sending test operation...")
        with app_insights.start_operation("test_operation"):
            # Simulate some work
            time.sleep(1)
            app_insights.track_trace(f"Inside test operation: {test_id}")
        
        # 6. Track exception
        print("   Sending test exception...")
        try:
            # Generate a test exception
            raise ValueError(f"Test exception with ID: {test_id}")
        except Exception as e:
            app_insights.track_exception(e, {"test_id": test_id})
        
        # 7. Track crawler-specific metrics
        print("   Sending crawler-specific metrics...")
        app_insights.track_articles_discovered(10, "test_source")
        app_insights.track_articles_processed(8, "test_source", True)
        app_insights.track_articles_processed(2, "test_source", False)
        app_insights.track_duplicates_detected(3, "test_source", "url")
        app_insights.track_documents_deleted(5, "qdrant")
        app_insights.track_cycle_duration(45.67)
        app_insights.track_deletion_duration(12.34)
        app_insights.track_memory_usage(256.78)
        
        print("\n✅ Successfully sent test telemetry to Azure Application Insights!")
        print("   Note: It may take a few minutes for data to appear in the Azure portal.")
        print("   Check your Application Insights resource for the test data with ID:")
        print(f"   {test_id}")
        print("\n📊 Search tips in Azure Application Insights:")
        print("   - In Logs, search: customEvents | where name == 'test_event'")
        print("   - For metrics: requests | where customDimensions.test_id == '" + test_id + "'")
        print("   - For exceptions: exceptions | where customDimensions.test_id == '" + test_id + "'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing Azure Application Insights: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    # Exit with appropriate code
    sys.exit(0 if success else 1)
