#!/usr/bin/env python3
"""
Test script to verify model route is available
"""
import sys
import os

# Add C:\Tools\VOFC-Flask to path
flask_dir = r'C:\Tools\VOFC-Flask'
if os.path.exists(flask_dir):
    sys.path.insert(0, flask_dir)
    os.chdir(flask_dir)

try:
    print("Testing blueprint import...")
    from routes.model import model_bp
    print(f"✓ Blueprint imported: {model_bp.name}")
    
    print("\nTesting app import...")
    from app import app
    print("✓ App imported successfully")
    
    print(f"\nRegistered blueprints: {list(app.blueprints.keys())}")
    
    print("\nChecking for /api/run_model route...")
    routes = [str(r) for r in app.url_map.iter_rules() if 'run_model' in r.rule]
    if routes:
        print(f"✓ Route found: {routes}")
    else:
        print("✗ Route NOT found in Flask app")
        print("\nAll routes:")
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith('model'):
                print(f"  {rule.rule} -> {rule.endpoint} ({rule.methods})")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

