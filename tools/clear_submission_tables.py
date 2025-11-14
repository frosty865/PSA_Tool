"""
Clear all submission tables for testing
Deletes all data from submission-related tables in the correct order.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("ERROR: supabase library not available")
    print("Install with: pip install supabase")
    sys.exit(1)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from config import Config
SUPABASE_URL = Config.SUPABASE_URL or ""
SUPABASE_KEY = Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_ANON_KEY

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Supabase credentials not found in environment variables")
    print("Required: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)")
    sys.exit(1)

def clear_submission_tables():
    """Clear all submission tables in the correct order."""
    print("=" * 60)
    print("Clearing Submission Tables")
    print("=" * 60)
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Tables to clear in order (respecting foreign key constraints)
    tables = [
        ("submission_vulnerability_ofc_links", "vulnerability-OFC links"),
        ("submission_ofc_sources", "OFC-source links"),
        ("submission_options_for_consideration", "Options for Consideration"),
        ("submission_vulnerabilities", "Vulnerabilities"),
        ("submission_sources", "Sources"),
        ("submissions", "Submissions"),
    ]
    
    total_deleted = 0
    
    for table_name, display_name in tables:
        try:
            # Get count before deletion
            count_result = supabase.table(table_name).select("*", count="exact").limit(1).execute()
            count = count_result.count if hasattr(count_result, 'count') else 0
            
            if count == 0:
                print(f"✓ {display_name:30} - Already empty")
                continue
            
            # Delete all records
            # Using a condition that matches all records
            delete_result = supabase.table(table_name).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            
            # Verify deletion
            verify_result = supabase.table(table_name).select("*", count="exact").limit(1).execute()
            remaining = verify_result.count if hasattr(verify_result, 'count') else 0
            
            if remaining == 0:
                print(f"✓ {display_name:30} - Deleted {count} record(s)")
                total_deleted += count
            else:
                print(f"⚠ {display_name:30} - Deleted {count - remaining} of {count} record(s)")
                
        except Exception as e:
            print(f"✗ {display_name:30} - Error: {e}")
    
    print("=" * 60)
    print(f"Total records deleted: {total_deleted}")
    print("=" * 60)
    print("✅ Submission tables cleared successfully!")
    print()
    print("You can now test the new system with fresh data.")

if __name__ == "__main__":
    # Check for --force flag to skip confirmation
    force = "--force" in sys.argv or "-f" in sys.argv
    
    if not force:
        # Confirm before proceeding
        print()
        print("⚠️  WARNING: This will delete ALL data from submission tables!")
        print("   - submissions")
        print("   - submission_vulnerabilities")
        print("   - submission_options_for_consideration")
        print("   - submission_sources")
        print("   - submission_vulnerability_ofc_links")
        print("   - submission_ofc_sources")
        print()
        try:
            response = input("Are you sure you want to continue? (yes/no): ")
        except EOFError:
            print("No input available. Use --force flag to run non-interactively.")
            sys.exit(1)
        
        if response.lower() not in ['yes', 'y']:
            print("Cancelled. No data was deleted.")
            sys.exit(0)
    
    clear_submission_tables()

