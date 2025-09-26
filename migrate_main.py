# migrate_main.py
"""
Migration script to safely update main.py to use the enhanced unified source system.
This script backs up the original main.py and replaces it with the enhanced version.
"""
import os
import shutil
from datetime import datetime

def migrate_main():
    """Migrate main.py to use enhanced unified source system."""
    
    print("🔄 NewsRagnarok Main.py Migration Script")
    print("=" * 45)
    
    # Check if files exist
    original_main = "main.py"
    enhanced_main = "main_enhanced.py"
    backup_main = f"main_original_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    
    if not os.path.exists(original_main):
        print(f"❌ Original main.py not found!")
        return False
    
    if not os.path.exists(enhanced_main):
        print(f"❌ Enhanced main.py not found!")
        return False
    
    try:
        # Step 1: Backup original main.py
        print(f"📦 Backing up original main.py to {backup_main}...")
        shutil.copy2(original_main, backup_main)
        print(f"✅ Backup created: {backup_main}")
        
        # Step 2: Replace main.py with enhanced version
        print(f"🔄 Replacing main.py with enhanced version...")
        shutil.copy2(enhanced_main, original_main)
        print(f"✅ main.py updated with unified source system")
        
        # Step 3: Show what changed
        print(f"\n📋 Migration Summary:")
        print(f"  📦 Original main.py backed up to: {backup_main}")
        print(f"  🚀 main.py now uses unified source system")
        print(f"  🔧 All 5 sources (BabyPips, FXStreet, ForexLive, Kabutan, PoundSterlingLive)")
        print(f"     are now managed through factory pattern")
        
        # Step 4: Show new capabilities
        print(f"\n🌟 New Capabilities:")
        print(f"  📊 Enhanced logging and statistics")
        print(f"  🔧 Unified source management")
        print(f"  📋 Better error handling and recovery") 
        print(f"  🧪 Test modes: --test-sources, --list-sources")
        print(f"  ⚡ Improved memory management")
        print(f"  📈 Enhanced monitoring and metrics")
        
        # Step 5: Show usage
        print(f"\n🚀 Usage (same as before):")
        print(f"  python main.py                    # Run enhanced crawler")
        print(f"  python main.py --clear-collection # Clear Qdrant collection")
        print(f"  python main.py --test-sources     # Test source creation")
        print(f"  python main.py --list-sources     # List available sources")
        
        # Step 6: Show rollback info
        print(f"\n🔄 Rollback Instructions (if needed):")
        print(f"  To restore original version:")
        print(f"  cp {backup_main} main.py")
        
        print(f"\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        
        # Try to restore backup if replacement failed
        if os.path.exists(backup_main):
            try:
                shutil.copy2(backup_main, original_main)
                print(f"🔄 Restored original main.py from backup")
            except:
                print(f"❌ Could not restore backup! Manual restoration needed.")
        
        return False

def show_differences():
    """Show key differences between original and enhanced versions."""
    print("\n🔍 Key Differences - Original vs Enhanced:")
    print("=" * 50)
    
    print("📊 ORIGINAL MAIN.PY:")
    print("  ❌ Individual crawler imports (babypips.py, fxstreet.py, etc.)")
    print("  ❌ Manual source configuration loading") 
    print("  ❌ Direct crawler.core.source_crawler calls")
    print("  ❌ Inconsistent error handling per source")
    print("  ❌ Basic statistics and logging")
    
    print("\n🚀 ENHANCED MAIN.PY:")
    print("  ✅ Unified source system with factory pattern")
    print("  ✅ Automatic source loading (YAML + fallback)")
    print("  ✅ Consistent interface for all sources")
    print("  ✅ Enhanced error handling and recovery")
    print("  ✅ Comprehensive statistics and monitoring")
    print("  ✅ Health checks for individual sources")
    print("  ✅ Better memory management and garbage collection")
    print("  ✅ Enhanced logging with emojis and formatting")
    print("  ✅ Test modes for development and debugging")
    
    print("\n💡 BENEFITS:")
    print("  🎯 All existing functionality preserved")
    print("  ⚡ Better performance and resource management")
    print("  🔧 Easier to add new sources in the future")
    print("  📊 Better monitoring and observability")
    print("  🛡️ More robust error handling")
    print("  🧪 Better development and testing tools")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show-diff":
        show_differences()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Migration Script for NewsRagnarok Main.py")
        print("Usage:")
        print("  python migrate_main.py           # Perform migration")
        print("  python migrate_main.py --show-diff  # Show differences")
        print("  python migrate_main.py --help       # Show this help")
    else:
        success = migrate_main()
        if success:
            print(f"\n🎉 Ready to run enhanced crawler!")
            print(f"   python main.py")
        else:
            print(f"\n❌ Migration failed. Check errors above.")
            sys.exit(1)
