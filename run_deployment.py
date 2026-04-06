#!/usr/bin/env python3
"""
HuggingFace Deployment Automation Script
Executes all 7 remaining tasks for OptiMaintainer project
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import time
import requests

def main():
    print("="*80)
    print("OptiMaintainer - HuggingFace Deployment Automation")
    print("="*80)
    print()
    
    # Check for HF_TOKEN
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ ERROR: HF_TOKEN environment variable not set!")
        print()
        print("Please set your HuggingFace token:")
        print('  PowerShell: $env:HF_TOKEN = "hf_xxxxxxxxxxxxx"')
        print('  CMD: set HF_TOKEN=hf_xxxxxxxxxxxxx')
        return False
    
    print(f"✅ HF_TOKEN found (length: {len(hf_token)})")
    print()
    
    # Task 1: Run deploy script
    print("="*80)
    print("TASK 1: Creating HF Space and deploying...")
    print("="*80)
    
    try:
        result = subprocess.run([sys.executable, "deploy_hf.py"], 
                              cwd=".",
                              capture_output=True, 
                              text=True,
                              timeout=300)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings/Info:", result.stderr)
        
        if result.returncode != 0:
            print("❌ Deployment failed!")
            return False
        
        print("✅ TASK 1 COMPLETE: HF Space created and deployed")
        
    except Exception as e:
        print(f"❌ Error running deploy_hf.py: {e}")
        return False
    
    print()
    print("="*80)
    print("TASK 2-7: Manual Steps Required")
    print("="*80)
    print()
    print("Your Space is now being built. Complete these steps:")
    print()
    print("1. Wait for Space to finish building (2-5 minutes)")
    print("   Monitor at: https://huggingface.co/spaces/YOUR-USERNAME/optimaintainer")
    print()
    print("2. Add secrets in Space Settings:")
    print("   - HF_TOKEN")
    print("   - OPENAI_API_KEY")
    print()
    print("3. Add tag 'openenv' in Space Settings")
    print()
    print("4. Test endpoints once Space is Running:")
    print("   - GET https://YOUR-USERNAME-optimaintainer.hf.space/health")
    print("   - POST https://YOUR-USERNAME-optimaintainer.hf.space/reset")
    print()
    print("5. Update Excel checklists when confirmed working")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
