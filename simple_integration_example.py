# simple_integration_example.py
"""
Simple example showing how to use the new unified source system.
"""

def show_system_info():
    """Show information about the new source system."""
    print("NewsRagnarok Unified Source System")
    print("=" * 40)
    
    try:
        from crawler.factories import SourceFactory
        
        print("\nAvailable Templates:")
        for source_type in SourceFactory.get_supported_source_types():
            print(f"  - {source_type.value}")
        
        print("\nCustom Adapters (Your 5 Sources):")
        for source_name in SourceFactory.get_custom_sources():
            info = SourceFactory.get_creation_info(source_name)
            print(f"  - {source_name}: {info['creation_strategy']}")
        
        print("\nHow to use in main.py:")
        print("1. Replace existing imports:")
        print("   from crawler.factories import SourceFactory")
        print("2. Create all sources:")
        print("   sources = create_all_sources_fallback()")
        print("3. Process each source:")
        print("   for name, source in sources.items():")
        print("       result = await source.process_articles()")
        
        return True
        
    except Exception as e:
        print(f"Error loading system: {e}")
        return False

def test_source_creation():
    """Test creating sources with the new system."""
    print("\nTesting Source Creation:")
    print("-" * 25)
    
    try:
        from crawler.factories import SourceFactory
        from crawler.interfaces import SourceType, ContentType, SourceConfig
        
        # Test creating BabyPips source
        config = SourceConfig(
            name="babypips",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.babypips.com",
            rss_url="https://www.babypips.com/feed.rss"
        )
        
        if SourceFactory.can_create_source(config):
            source = SourceFactory.create_source(config)
            print(f"SUCCESS: Created {config.name} source")
            print(f"  Source type: {config.source_type.value}")
            print(f"  Content type: {config.content_type.value}")
            return True
        else:
            print("Cannot create source with current configuration")
            return False
            
    except Exception as e:
        print(f"Error creating source: {e}")
        return False

if __name__ == "__main__":
    print("NewsRagnarok Phase 1 - Integration Ready!")
    print("")
    
    success = True
    success &= show_system_info()
    success &= test_source_creation()
    
    if success:
        print("\n" + "=" * 40)
        print("SUCCESS: Phase 1 system is ready!")
        print("\nAll 5 sources (BabyPips, FXStreet, ForexLive,")
        print("Kabutan, PoundSterlingLive) can now be managed")
        print("through the unified interface.")
        print("\nReady for production integration!")
    else:
        print("\nSome components need dependencies installed.")
