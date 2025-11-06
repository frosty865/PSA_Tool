#!/usr/bin/env python3
"""
Check which Flask routes are actually available
"""
import requests
import json

BASE_URL = "http://localhost:8080"

# Routes to test
routes_to_test = [
    ("GET", "/"),
    ("GET", "/api/system/health"),
    ("GET", "/api/health"),
    ("GET", "/api/version"),
    ("GET", "/api/progress"),
    ("GET", "/api/files/list"),
    ("POST", "/api/process/start", {"filename": "test.pdf"}),
    ("POST", "/api/system/control", {"action": "process_existing"}),
]

print("=" * 60)
print("Testing Flask Routes")
print("=" * 60)
print()

available = []
not_found = []

for route_info in routes_to_test:
    method = route_info[0]
    path = route_info[1]
    body = route_info[2] if len(route_info) > 2 else None
    
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json=body, timeout=5)
        
        if response.status_code == 200:
            available.append((method, path, response.status_code))
            print(f"[OK] {method:6} {path:40} -> {response.status_code}")
        elif response.status_code == 404:
            not_found.append((method, path))
            print(f"[404] {method:6} {path:40} -> Not Found")
        else:
            print(f"[{response.status_code}] {method:6} {path:40} -> {response.status_code}")
            if response.status_code < 500:
                available.append((method, path, response.status_code))
    except Exception as e:
        print(f"[ERROR] {method:6} {path:40} -> {str(e)[:50]}")

print()
print("=" * 60)
print("Summary")
print("=" * 60)
print(f"Available routes: {len(available)}")
print(f"Not found (404): {len(not_found)}")
print()

if not_found:
    print("Routes returning 404 (Flask needs restart):")
    for method, path in not_found:
        print(f"  {method} {path}")
    print()
    print("SOLUTION: Restart Flask service:")
    print("  nssm restart \"VOFC-Flask\"")
    print("  (Run PowerShell as Administrator)")

