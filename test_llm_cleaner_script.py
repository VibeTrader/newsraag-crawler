"""
Simple test script for LLM content cleaner.

This script demonstrates how to use the LLM content cleaner directly.
"""
import os
import asyncio
import json
import sys
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Environment variables loaded from .env file")
except ImportError:
    # If python-dotenv is not installed, environment variables should be set manually
    print("python-dotenv not installed. Using existing environment variables.")

async def test_llm_cleaner():
    """Test the LLM content cleaner with a sample article."""
    try:
        # Import after environment is loaded
        from utils.llm.cleaner import create_llm_cleaner
        from utils.config.env_validator import EnvironmentValidator
        
        # Validate LLM configuration
        validation = EnvironmentValidator.validate_llm_config()
        print(f"\nLLM configuration validation: {validation}")
        
        # Check if LLM cleaning is enabled
        is_enabled = EnvironmentValidator.is_llm_cleaning_enabled()
        print(f"LLM cleaning enabled: {is_enabled}")
        
        if not is_enabled:
            print("LLM cleaning is disabled. Please check your configuration.")
            return
        
        # Create LLM cleaner
        cleaner = create_llm_cleaner()
        
        # Sample article content
        sample_article = """
        # Market Recap: Stocks Fall as Tech Earnings Disappoint
        
        By Sarah Johnson | Markets | September 23, 2025
        
        HOME | MARKETS | ECONOMY | TECH | PERSONAL FINANCE | SIGN IN
        
        U.S. stocks declined on Tuesday as disappointing earnings from major tech companies weighed on market sentiment. The S&P 500 fell 0.8%, while the tech-heavy Nasdaq Composite dropped 1.5%.
        
        ## Earnings Disappoint
        
        Technology giants reported mixed results, with several missing analyst expectations:
        
        - MegaTech reported EPS of $2.45 vs $2.65 expected
        - GlobalSoft saw revenue drop 3% year-over-year to $28.7 billion
        - CloudSystems cut its forward guidance, citing "macroeconomic uncertainties"
        
        The results triggered a sell-off in the sector, with the Technology Select SPDR ETF (XLK) falling 2.3%.
        
        ## Economic Data
        
        Meanwhile, new economic data showed consumer confidence declining to 95.2 in September from 98.7 in August. Economists had expected a reading of 97.0.
        
        "Consumer sentiment is weakening as inflation concerns persist," said Robert Chen, chief economist at Capital Research. "This could impact holiday spending if the trend continues."
        
        ## Market Outlook
        
        Analysts remain cautious about the market's near-term prospects:
        
        > "We're seeing a rotation out of growth stocks and into value plays as interest rates remain elevated," noted Maria Rodriguez, market strategist at Global Investments. "Defensive sectors like utilities and consumer staples could outperform in this environment."
        
        The 10-year Treasury yield rose to 3.85%, putting additional pressure on growth stocks.
        
        ## Trading Levels
        
        Key levels to watch:
        - S&P 500: Support at 4,850, resistance at 5,050
        - Nasdaq: Support at 16,800, resistance at 17,500
        - Dow Jones: Support at 41,200, resistance at 42,400
        
        MOST READ ARTICLES | SUBSCRIBE | ADVERTISE WITH US
        
        © 2025 Financial News Corp. All Rights Reserved | Terms of Use | Privacy Policy
        """
        
        # Test cleaning
        print(f"\nCleaning sample article...")
        result = await cleaner.clean_content(sample_article, "test", "http://example.com/market-recap")
        
        if result:
            cleaned_content, metadata = result
            
            # Print metadata
            print(f"\nExtracted Metadata:")
            print(json.dumps(metadata, indent=2))
            
            # Print cleaned content preview
            print(f"\nCleaned Content Preview (first 500 chars):")
            print(cleaned_content[:500])
            
            # Print token usage
            print(f"\nToken Usage:")
            print(json.dumps(cleaner.get_token_usage(), indent=2))
            
            # Check health
            is_healthy = await cleaner.is_healthy()
            print(f"\nLLM cleaner health check: {is_healthy}")
        else:
            print("LLM cleaning failed. Check logs for details.")
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Please make sure all dependencies are installed.")
    except Exception as e:
        print(f"Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        print("Starting LLM cleaner test...")
        asyncio.run(test_llm_cleaner())
        print("\nTest completed.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError running test: {e}")
        import traceback
        traceback.print_exc()