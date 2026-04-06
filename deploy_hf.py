#!/usr/bin/env python3
"""
HuggingFace Space Deployment Script for OptiMaintainer

Usage:
    export HF_TOKEN=your_huggingface_token
    python deploy_hf.py

This script creates a Docker-based HuggingFace Space and deploys the OptiMaintainer environment.
"""

import os
import sys

try:
    from huggingface_hub import HfApi, create_repo, upload_folder
except ImportError:
    print("Install huggingface_hub: pip install huggingface_hub")
    sys.exit(1)


def deploy():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: Set HF_TOKEN environment variable")
        print("  export HF_TOKEN=your_huggingface_token")
        sys.exit(1)

    api = HfApi(token=token)
    
    # Configuration
    repo_name = "optimaintainer"
    username = api.whoami()["name"]
    repo_id = f"{username}/{repo_name}"
    
    print(f"Deploying to: https://huggingface.co/spaces/{repo_id}")
    
    # Create Space (Docker SDK)
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
            token=token,
        )
        print(f"✅ Created Space: {repo_id}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"Space already exists: {repo_id}")
        else:
            raise

    # Upload files
    upload_folder(
        folder_path=".",
        repo_id=repo_id,
        repo_type="space",
        token=token,
        ignore_patterns=[
            ".git/*",
            "__pycache__/*",
            "*.pyc",
            ".env",
            "results.jsonl",
            "deploy_hf.py",
        ],
    )
    
    print(f"✅ Uploaded files to Space")
    print(f"\n🚀 Deployment complete!")
    print(f"   URL: https://huggingface.co/spaces/{repo_id}")
    print(f"   Health: https://{username}-{repo_name}.hf.space/health")


if __name__ == "__main__":
    deploy()
