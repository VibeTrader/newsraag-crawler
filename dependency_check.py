#!/usr/bin/env python3
"""
Simple dependency checker for NewsRagnarok Crawler.
Tests if all required modules can be imported successfully.
"""
import sys
import os

def test_imports():
    """Test all required imports."""
    print("🔍 Testing Python imports...")
    
    required_modules = [
        'time', 'asyncio', 'os', 'sys', 'argparse', 'threading', 
        'datetime', 'gc', 'json', 'http.server'
    ]
    
    optional_modules = [
        'psutil', 'loguru', 'qdrant_client', 'openai', 'redis'
    ]
    
    # Test required modules
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False
    
    # Test optional modules
    print("\n🔍 Testing optional modules...")
    for module in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"⚠️ {module}: {e} (optional)")
    
    return True

def test_environment():
    """Test environment variables."""
    print("\n🔍 Testing environment variables...")
    
    required_env = [
        'QDRANT_URL', 'QDRANT_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_API_KEY'
    ]
    
    optional_env = [
        'REDIS_HOST', 'REDIS_PASSWORD', 'PORT', 'ENVIRONMENT'
    ]
    
    # Test required environment variables
    all_present = True
    for env_var in required_env:
        value = os.environ.get(env_var)
        if value:
            print(f"✅ {env_var}: {'*' * len(value[:10])}...")
        else:
            print(f"❌ {env_var}: Missing")
            all_present = False
    
    # Test optional environment variables
    print("\n🔍 Optional environment variables...")
    for env_var in optional_env:
        value = os.environ.get(env_var)
        if value:
            print(f"✅ {env_var}: {value}")
        else:
            print(f"⚠️ {env_var}: Not set")
    
    return all_present

def test_file_structure():
    """Test required files and directories."""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        'main.py', 'requirements.txt', 'azure_startup.py'
    ]
    
    required_dirs = [
        'crawler', 'monitoring', 'config'
    ]
    
    all_present = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}: Missing")
            all_present = False
    
    for dir in required_dirs:
        if os.path.isdir(dir):
            print(f"✅ {dir}/")
        else:
            print(f"❌ {dir}/: Missing")
            all_present = False
    
    return all_present

def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 NewsRagnarok Crawler - Dependency Check")
    print("=" * 60)
    
    # Load .env file if present
    if os.path.exists('.env'):
        print("📄 Loading .env file...")
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ Environment variables loaded from .env")
    
    # Run tests
    imports_ok = test_imports()
    env_ok = test_environment()
    files_ok = test_file_structure()
    
    print("\n" + "=" * 60)
    print("📊 DEPENDENCY CHECK SUMMARY")
    print("=" * 60)
    
    print(f"📦 Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"🔧 Environment: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"📁 File Structure: {'✅ PASS' if files_ok else '❌ FAIL'}")
    
    overall_status = imports_ok and env_ok and files_ok
    print(f"\n🎯 Overall Status: {'✅ READY TO DEPLOY' if overall_status else '❌ NEEDS ATTENTION'}")
    
    if not overall_status:
        print("\n💡 Please fix the issues above before deploying to Azure.")
        return 1
    else:
        print("\n🚀 All checks passed! Ready for Azure deployment.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
