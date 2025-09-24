"""
Test the LLM-based content cleaner.
"""
import os
import pytest
import asyncio
from loguru import logger

from utils.llm.cleaner import create_llm_cleaner
from utils.config.env_validator import EnvironmentValidator
from utils.config.token_tracker import TokenUsageTracker

@pytest.mark.asyncio
async def test_llm_config_validation():
    """Test LLM configuration validation."""
    # Validate LLM configuration
    validation = EnvironmentValidator.validate_llm_config()
    
    # Log validation results
    logger.info(f"LLM configuration validation: {validation}")
    
    # Check if LLM cleaning is enabled
    is_enabled = EnvironmentValidator.is_llm_cleaning_enabled()
    logger.info(f"LLM cleaning enabled: {is_enabled}")
    
    # Get LLM configuration
    config = EnvironmentValidator.get_llm_config()
    logger.info(f"LLM configuration: {config}")
    
    # If LLM cleaning is enabled, it should have valid configuration
    if is_enabled:
        assert validation["azure_openai"], "Azure OpenAI configuration should be valid when LLM cleaning is enabled"
        assert validation["llm_cleaning"], "LLM cleaning configuration should be valid when LLM cleaning is enabled"

@pytest.mark.asyncio
async def test_token_tracker():
    """Test token usage tracker."""
    # Initialize token tracker
    tracker = TokenUsageTracker()
    
    # Get initial usage stats
    initial_stats = tracker.get_usage_stats()
    logger.info(f"Initial token usage stats: {initial_stats}")
    
    # Record some token usage
    tracker.record_usage("gpt-4", 100, "test")
    
    # Get updated stats
    updated_stats = tracker.get_usage_stats()
    logger.info(f"Updated token usage stats: {updated_stats}")
    
    # Check if usage was recorded
    if tracker.track_usage:
        assert updated_stats["daily_usage"]["tokens"] >= 100, "Daily token usage should include recorded usage"
        assert updated_stats["total_usage"]["tokens"] >= 100, "Total token usage should include recorded usage"

@pytest.mark.asyncio
async def test_llm_cleaner():
    """Test the LLM content cleaner."""
    # Create LLM cleaner
    cleaner = create_llm_cleaner()
    
    # Skip test if LLM cleaning is disabled
    if not cleaner.enabled:
        logger.warning("LLM cleaning is disabled, skipping test")
        pytest.skip("LLM cleaning is disabled")
    
    # Sample raw content
    raw_content = """
    # Bitcoin Breaks $50,000 as Bull Run Continues
    
    By John Smith | Category: Cryptocurrency | 2025-09-20
    
    NAVIGATION MENU | HOME | ABOUT | CONTACT
    
    Bitcoin has broken through the $50,000 level for the first time since December.
    Analysts suggest this could be the beginning of a new bull market.
    
    Key support levels:
    - $48,500
    - $46,200
    - $42,000
    
    FOOTER | PRIVACY POLICY | TERMS OF SERVICE
    """
    
    # Test cleaning
    result = await cleaner.clean_content(raw_content, "test_source", "http://example.com")
    
    # Assertions
    assert result is not None, "LLM cleaner should return a result"
    cleaned_content, metadata = result
    
    # Check metadata extraction
    assert "Bitcoin" in metadata.get("title", ""), "Title should be extracted correctly"
    assert "John Smith" in metadata.get("author", ""), "Author should be extracted correctly"
    assert "Cryptocurrency" in metadata.get("category", ""), "Category should be extracted correctly"
    
    # Check that navigation elements are removed
    assert "NAVIGATION MENU" not in cleaned_content, "Navigation menu should be removed"
    assert "FOOTER" not in cleaned_content, "Footer should be removed"
    
    # Check that financial data is preserved
    assert "$50,000" in cleaned_content, "Price value should be preserved"
    assert "$48,500" in cleaned_content, "Support level should be preserved"
    assert "bull market" in cleaned_content, "Market analysis should be preserved"
    
    # Get token usage
    token_usage = cleaner.get_token_usage()
    logger.info(f"Token usage after cleaning: {token_usage}")
    
    # Check health
    is_healthy = await cleaner.is_healthy()
    logger.info(f"LLM cleaner health check: {is_healthy}")

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_llm_config_validation())
    asyncio.run(test_token_tracker())
    asyncio.run(test_llm_cleaner())