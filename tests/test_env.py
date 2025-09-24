#!/usr/bin/env python3
"""
Diagnostic script to test environment loading and LLM configuration.
"""
import os
from dotenv import load_dotenv

# Load environment variables
print("Loading .env file...")
load_dotenv()

# Test specific environment variables
print("\n=== Environment Variable Check ===")
env_vars_to_check = [
    "AZURE_OPENAI_DEPLOYMENT",
    "OPENAI_API_KEY", 
    "OPENAI_BASE_URL",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_OPENAI_EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "LLM_CLEANING_ENABLED"
]

for var in env_vars_to_check:
    value = os.getenv(var)
    if var == "OPENAI_API_KEY":
        display_value = f"***{value[-4:]}" if value else "NOT SET"
    else:
        display_value = value if value else "NOT SET"
    print(f"{var}: {display_value}")

# Test the validator
print("\n=== Testing EnvironmentValidator ===")
try:
    from utils.config.env_validator import EnvironmentValidator
    
    # Test validate_llm_config
    validation_result = EnvironmentValidator.validate_llm_config()
    print(f"validate_llm_config() result: {validation_result}")
    
    # Test is_llm_cleaning_enabled
    is_enabled = EnvironmentValidator.is_llm_cleaning_enabled()
    print(f"is_llm_cleaning_enabled(): {is_enabled}")
    
    # Get full config
    llm_config = EnvironmentValidator.get_llm_config()
    print(f"LLM config keys: {list(llm_config.keys())}")
    
    # Show which variables the validator thinks are missing
    base_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "AZURE_OPENAI_API_VERSION"]
    cleaning_vars = ["AZURE_OPENAI_DEPLOYMENT"]
    embedding_vars = ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "AZURE_OPENAI_EMBEDDING_MODEL", "EMBEDDING_DIMENSION"]
    
    print("\n=== Variable Existence Check ===")
    for var_group, vars_list in [("Base", base_vars), ("Cleaning", cleaning_vars), ("Embedding", embedding_vars)]:
        print(f"{var_group} vars:")
        for var in vars_list:
            exists = bool(os.getenv(var))
            print(f"  {var}: {'EXISTS' if exists else 'MISSING'}")
        
except Exception as e:
    print(f"Error testing validator: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Summary ===")
print("If Azure OpenAI deployment is set but validator says it's missing,")
print("this could be an issue with environment loading or path resolution.")
