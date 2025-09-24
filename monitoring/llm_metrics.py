"""
Enhanced metrics for LLM content cleaning.
"""

def record_llm_cleaning_success(self, source_name: str) -> None:
    """Record successful LLM content cleaning.
    
    Args:
        source_name: The name of the source (crawler)
    """
    try:
        # Increment success counter
        self.increment_counter(f"llm_cleaning_success_{source_name}")
        self.increment_counter("llm_cleaning_success_total")
        
        # Calculate and update success rate
        success_count = self.get_counter(f"llm_cleaning_success_{source_name}", 0)
        failure_count = self.get_counter(f"llm_cleaning_failure_{source_name}", 0)
        total_count = success_count + failure_count
        
        if total_count > 0:
            success_rate = (success_count / total_count) * 100
            self.update_gauge(f"llm_cleaning_success_rate_{source_name}", success_rate)
            
        # Update last successful timestamp
        import time
        self.update_gauge(f"llm_cleaning_last_success_{source_name}", time.time())
        
    except Exception as e:
        import traceback
        self.logger.error(f"Error recording LLM cleaning success: {e}\n{traceback.format_exc()}")
        
def record_llm_cleaning_failure(self, source_name: str, error_message: str) -> None:
    """Record failed LLM content cleaning.
    
    Args:
        source_name: The name of the source (crawler)
        error_message: The error message
    """
    try:
        # Increment failure counter
        self.increment_counter(f"llm_cleaning_failure_{source_name}")
        self.increment_counter("llm_cleaning_failure_total")
        
        # Record error in alerts
        self.record_error(
            error_type="llm_cleaning_failed",
            message=f"LLM cleaning failed for {source_name}: {error_message}",
            severity="warning",
            source=source_name
        )
        
        # Update last failure timestamp
        import time
        self.update_gauge(f"llm_cleaning_last_failure_{source_name}", time.time())
        
    except Exception as e:
        import traceback
        self.logger.error(f"Error recording LLM cleaning failure: {e}\n{traceback.format_exc()}")
