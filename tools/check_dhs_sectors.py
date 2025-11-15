#!/usr/bin/env python3
"""
Check Supabase sectors and subsectors against DHS Critical Infrastructure standards.
Verifies that all sectors match DHS 16 critical infrastructure sectors (plus General exception).
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.supabase_client import get_supabase_client
from config import Config

# DHS 16 Critical Infrastructure Sectors (official names)
DHS_SECTORS = {
    "Chemical",
    "Commercial Facilities",
    "Communications",
    "Critical Manufacturing",
    "Dams",
    "Defense Industrial Base",
    "Emergency Services",
    "Energy",
    "Financial Services",
    "Food and Agriculture",
    "Government Facilities",
    "Healthcare and Public Health",
    "Information Technology",
    "Nuclear Reactors, Materials, and Waste",
    "Transportation Systems",
    "Water and Wastewater Systems"
}

# Allowed exception
ALLOWED_EXCEPTIONS = {"General"}

def normalize_name(name):
    """Normalize sector/subsector name for comparison"""
    if not name:
        return ""
    return name.strip()

def check_sectors():
    """Check sectors table against DHS standards"""
    print("=" * 80)
    print("CHECKING SECTORS AGAINST DHS STANDARDS")
    print("=" * 80)
    
    try:
        client = get_supabase_client()
        
        # Query sectors table - try different column name variations
        result = None
        try:
            # Try selecting all columns first to see what's available
            result = client.table("sectors").select("*").execute()
            if result.data and len(result.data) > 0:
                print(f"DEBUG: Sample sector row: {result.data[0]}")
                print(f"DEBUG: Available columns: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"ERROR: Could not query sectors table: {e}")
            return False
        
        if not result or not result.data:
            print("WARNING: No sectors found in database (table may be empty)")
            print("Attempting to query with is_active filter...")
            try:
                # Try with is_active filter
                result = client.table("sectors").select("*").eq("is_active", True).execute()
            except:
                pass
        
        if not result or not result.data:
            print("ERROR: No sectors found in database")
            return False
        
        sectors_in_db = {}
        for row in result.data:
            # Try all possible column name variations
            sector_name = (row.get("name") or 
                          row.get("sector_name") or 
                          row.get("sector") or 
                          "").strip()
            sector_id = row.get("id")
            is_active = row.get("is_active", True)
            
            if sector_name:
                sectors_in_db[sector_name] = {
                    "id": sector_id,
                    "is_active": is_active,
                    "raw_row": row  # Keep for debugging
                }
            else:
                print(f"WARNING: Sector row with no name: {row}")
        
        print(f"\nFound {len(sectors_in_db)} sectors in database:")
        print("-" * 80)
        
        # Check each sector
        all_valid = True
        missing_dhs = []
        extra_sectors = []
        inactive_sectors = []
        
        for sector_name, info in sorted(sectors_in_db.items()):
            normalized = normalize_name(sector_name)
            
            if not info.get("is_active", True):
                inactive_sectors.append(sector_name)
                print(f"  ⚠ INACTIVE: {sector_name} (ID: {info['id']})")
                continue
            
            if normalized in DHS_SECTORS:
                print(f"  ✓ VALID: {sector_name} (ID: {info['id']})")
            elif normalized in ALLOWED_EXCEPTIONS:
                print(f"  ✓ ALLOWED EXCEPTION: {sector_name} (ID: {info['id']})")
            else:
                print(f"  ✗ NOT DHS STANDARD: {sector_name} (ID: {info['id']})")
                extra_sectors.append(sector_name)
                all_valid = False
        
        # Check for missing DHS sectors
        db_sector_names = {normalize_name(s) for s in sectors_in_db.keys()}
        for dhs_sector in DHS_SECTORS:
            if dhs_sector not in db_sector_names:
                missing_dhs.append(dhs_sector)
                print(f"  ✗ MISSING DHS SECTOR: {dhs_sector}")
                all_valid = False
        
        # Summary
        print("\n" + "=" * 80)
        print("SECTOR CHECK SUMMARY")
        print("=" * 80)
        print(f"Total sectors in DB: {len(sectors_in_db)}")
        print(f"Active sectors: {len(sectors_in_db) - len(inactive_sectors)}")
        print(f"Valid DHS sectors: {len([s for s in sectors_in_db.keys() if normalize_name(s) in DHS_SECTORS])}")
        print(f"Allowed exceptions: {len([s for s in sectors_in_db.keys() if normalize_name(s) in ALLOWED_EXCEPTIONS])}")
        
        if missing_dhs:
            print(f"\n⚠ MISSING DHS SECTORS ({len(missing_dhs)}):")
            for sector in missing_dhs:
                print(f"  - {sector}")
        
        if extra_sectors:
            print(f"\n⚠ NON-DHS SECTORS ({len(extra_sectors)}):")
            for sector in extra_sectors:
                print(f"  - {sector}")
        
        if inactive_sectors:
            print(f"\n⚠ INACTIVE SECTORS ({len(inactive_sectors)}):")
            for sector in inactive_sectors:
                print(f"  - {sector}")
        
        if all_valid and not missing_dhs:
            print("\n✓ ALL SECTORS MATCH DHS STANDARDS (plus allowed exceptions)")
        else:
            print("\n✗ SECTORS DO NOT FULLY MATCH DHS STANDARDS")
        
        return all_valid and not missing_dhs
    
    except Exception as e:
        print(f"ERROR: Failed to check sectors: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_subsectors():
    """Check subsectors table structure and relationships"""
    print("\n" + "=" * 80)
    print("CHECKING SUBSECTORS")
    print("=" * 80)
    
    try:
        client = get_supabase_client()
        
        # Query subsectors with their parent sectors
        result = None
        try:
            # Try to get subsectors with sector relationship using foreign key
            result = client.table("subsectors").select("id, name, sector_id, is_active, sectors!inner(sector_name)").execute()
        except Exception as e:
            try:
                # Try without join - we'll query sectors separately
                result = client.table("subsectors").select("id, name, sector_id, is_active").execute()
            except Exception as e2:
                print(f"ERROR: Could not query subsectors table: {e}, {e2}")
                return False
        
        if not result or not result.data:
            print("ERROR: No subsectors found in database")
            return False
        
        subsectors_in_db = {}
        subsectors_by_sector = {}
        
        for row in result.data:
            subsector_name = row.get("name") or row.get("subsector_name") or ""
            subsector_id = row.get("id")
            sector_id = row.get("sector_id")
            is_active = row.get("is_active", True)
            
            # Get sector name from join or query separately
            sector_name = None
            if "sectors" in row and isinstance(row["sectors"], dict):
                sector_name = row["sectors"].get("sector_name") or row["sectors"].get("name")
            elif sector_id:
                # Query sector separately
                try:
                    sector_result = client.table("sectors").select("sector_name, name").eq("id", sector_id).maybe_single().execute()
                    if sector_result.data:
                        sector_name = sector_result.data.get("sector_name") or sector_result.data.get("name")
                except Exception as e:
                    print(f"DEBUG: Could not query sector {sector_id}: {e}")
                    pass
            
            if subsector_name:
                subsectors_in_db[subsector_name] = {
                    "id": subsector_id,
                    "sector_id": sector_id,
                    "sector_name": sector_name,
                    "is_active": is_active
                }
                
                if sector_name:
                    if sector_name not in subsectors_by_sector:
                        subsectors_by_sector[sector_name] = []
                    subsectors_by_sector[sector_name].append(subsector_name)
        
        print(f"\nFound {len(subsectors_in_db)} subsectors in database")
        print(f"Subsectors grouped by {len(subsectors_by_sector)} sectors")
        print("-" * 80)
        
        # Show subsectors by sector
        for sector_name in sorted(subsectors_by_sector.keys()):
            subsectors = subsectors_by_sector[sector_name]
            print(f"\n  {sector_name} ({len(subsectors)} subsectors):")
            for subsector in sorted(subsectors):
                info = subsectors_in_db[subsector]
                status = "ACTIVE" if info.get("is_active", True) else "INACTIVE"
                print(f"    - {subsector} [{status}]")
        
        # Check for orphaned subsectors (no parent sector)
        orphaned = [name for name, info in subsectors_in_db.items() if not info.get("sector_id")]
        if orphaned:
            print(f"\n⚠ ORPHANED SUBSECTORS (no parent sector): {len(orphaned)}")
            for subsector in orphaned:
                print(f"  - {subsector}")
        
        # Check for inactive subsectors
        inactive = [name for name, info in subsectors_in_db.items() if not info.get("is_active", True)]
        if inactive:
            print(f"\n⚠ INACTIVE SUBSECTORS: {len(inactive)}")
            for subsector in inactive:
                print(f"  - {subsector}")
        
        print(f"\n✓ SUBSECTOR CHECK COMPLETE")
        return True
    
    except Exception as e:
        print(f"ERROR: Failed to check subsectors: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("\n" + "=" * 80)
    print("DHS SECTOR/SUBSECTOR VALIDATION")
    print("=" * 80)
    print(f"Checking against DHS 16 Critical Infrastructure Sectors")
    print(f"Allowed exceptions: {', '.join(ALLOWED_EXCEPTIONS)}")
    print()
    
    # Check if Supabase is configured
    if Config.SUPABASE_OFFLINE_MODE:
        print("ERROR: Supabase is in offline mode. Cannot check database.")
        return 1
    
    if not Config.SUPABASE_URL:
        print("ERROR: Supabase URL not configured.")
        return 1
    
    # Check sectors
    sectors_ok = check_sectors()
    
    # Check subsectors
    subsectors_ok = check_subsectors()
    
    # Final result
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if sectors_ok and subsectors_ok:
        print("✓ ALL CHECKS PASSED")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Review output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())

