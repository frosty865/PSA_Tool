#!/usr/bin/env python3
"""
Test Supabase Connection
Diagnostic script to check Supabase configuration and connection
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.supabase_client import get_supabase_client, test_supabase
from services.processor.normalization.supabase_upload import init_supabase

print("=" * 60)
print("Supabase Connection Diagnostic")
print("=" * 60)
print()

# Check configuration
print("📋 Configuration Check:")
print(f"  SUPABASE_URL: {'✅ SET' if Config.SUPABASE_URL else '❌ NOT SET'}")
if Config.SUPABASE_URL:
    print(f"    Value: {Config.SUPABASE_URL[:50]}...")
print(f"  SUPABASE_SERVICE_ROLE_KEY: {'✅ SET' if Config.SUPABASE_SERVICE_ROLE_KEY else '❌ NOT SET'}")
print(f"  SUPABASE_ANON_KEY: {'✅ SET' if Config.SUPABASE_ANON_KEY else '❌ NOT SET'}")
print(f"  SUPABASE_OFFLINE_MODE: {'⚠️  ENABLED' if Config.SUPABASE_OFFLINE_MODE else '✅ DISABLED'}")
print()

# Check which key will be used
supabase_key = Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_ANON_KEY
if Config.SUPABASE_SERVICE_ROLE_KEY:
    print("  🔑 Using: SUPABASE_SERVICE_ROLE_KEY")
elif Config.SUPABASE_ANON_KEY:
    print("  🔑 Using: SUPABASE_ANON_KEY")
else:
    print("  ❌ No key available!")
print()

# Test connection
print("🔌 Connection Test:")
try:
    result = test_supabase()
    if result == "ok":
        print("  ✅ Connection test: SUCCESS")
    else:
        print(f"  ❌ Connection test: FAILED ({result})")
except Exception as e:
    print(f"  ❌ Connection test: ERROR - {e}")
print()

# Try to get client
print("🔧 Client Initialization:")
try:
    client = get_supabase_client()
    print("  ✅ Client created successfully")
    
    # Try a simple query
    print("  📊 Testing query...")
    try:
        result = client.table('sectors').select('id, name').limit(3).execute()
        if result.data:
            print(f"  ✅ Query successful: Found {len(result.data)} sectors")
            for sector in result.data:
                print(f"     - {sector.get('name', 'Unknown')}")
        else:
            print("  ⚠️  Query returned no data")
    except Exception as e:
        print(f"  ❌ Query failed: {e}")
        
except ConfigurationError as e:
    print(f"  ❌ Configuration error: {e}")
except Exception as e:
    print(f"  ❌ Client creation failed: {e}")
    import traceback
    traceback.print_exc()
print()

# Test upload module
print("📤 Upload Module Test:")
try:
    upload_client = init_supabase()
    if upload_client:
        print("  ✅ Upload module client initialized successfully")
    else:
        print("  ❌ Upload module client initialization failed (returned None)")
except Exception as e:
    print(f"  ❌ Upload module error: {e}")
    import traceback
    traceback.print_exc()
print()

# Summary
print("=" * 60)
print("Summary:")
if Config.SUPABASE_URL and supabase_key and not Config.SUPABASE_OFFLINE_MODE:
    print("  ✅ Configuration looks good")
    try:
        test_result = test_supabase()
        if test_result == "ok":
            print("  ✅ Connection is working")
            print()
            print("  If uploads are still failing, check:")
            print("    1. Service logs for specific error messages")
            print("    2. Supabase dashboard for API errors")
            print("    3. Network connectivity to Supabase")
        else:
            print(f"  ❌ Connection test failed: {test_result}")
    except Exception as e:
        print(f"  ❌ Connection test error: {e}")
else:
    print("  ❌ Configuration incomplete:")
    if not Config.SUPABASE_URL:
        print("     - SUPABASE_URL is not set")
    if not supabase_key:
        print("     - Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_ANON_KEY is set")
    if Config.SUPABASE_OFFLINE_MODE:
        print("     - SUPABASE_OFFLINE_MODE is enabled")
print("=" * 60)

