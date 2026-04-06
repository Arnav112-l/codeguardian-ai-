#!/usr/bin/env python3
"""
Post-Deployment Verification Script
Tests all endpoints after HuggingFace Space deployment
"""

import sys
import time
import requests
from typing import Tuple

def test_endpoint(url: str, method: str = "GET", data: dict = None) -> Tuple[bool, str]:
    """Test an endpoint and return success status and response"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:  # POST
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return True, response.json() if response.text else "OK"
        else:
            return False, f"Status {response.status_code}: {response.text}"
    except requests.exceptions.Timeout:
        return False, "Timeout (Space still building?)"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, str(e)

def main():
    print("="*80)
    print("OptiMaintainer - Post-Deployment Verification")
    print("="*80)
    print()
    
    # Get Space URL from user
    space_url = input("Enter your Space URL (e.g., https://username-optimaintainer.hf.space/): ").strip()
    
    if not space_url.endswith("/"):
        space_url += "/"
    
    # Remove trailing slash for endpoint construction
    base_url = space_url.rstrip("/")
    
    print()
    print(f"Testing Space: {base_url}")
    print()
    
    # Test endpoints
    tests = [
        ("GET /health", f"{base_url}/health", "GET", None),
        ("GET /scenarios", f"{base_url}/scenarios", "GET", None),
        ("POST /reset", f"{base_url}/reset", "POST", {}),
        ("GET /state", f"{base_url}/state", "GET", None),
    ]
    
    results = []
    
    for name, url, method, data in tests:
        print(f"Testing {name}...", end=" ")
        success, response = test_endpoint(url, method, data)
        results.append((name, success, response))
        
        if success:
            print("✅ PASS")
            if isinstance(response, dict):
                # Show summary of response
                if "status" in response:
                    print(f"  └─ Status: {response['status']}")
                if "total_scenarios" in response:
                    print(f"  └─ Scenarios: {response['total_scenarios']}")
        else:
            print(f"❌ FAIL")
            print(f"  └─ Error: {response}")
    
    print()
    print("="*80)
    print("Summary")
    print("="*80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print()
        print("✅ ALL TESTS PASSED!")
        print()
        print("Next steps:")
        print("1. Update Excel checklists marking all HF tasks as Done")
        print("2. Tag your Space with 'openenv' in Settings")
        print("3. Add secret GROQ_API_KEY in Settings")
        print()
        return True
    else:
        print()
        print("⚠️ Some tests failed. Possible reasons:")
        print("- Space is still building (wait 2-5 minutes)")
        print("- Space needs to be restarted")
        print("- Check Space logs in HF settings")
        print()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
