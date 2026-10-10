"""
Deploy script for Stubble Smoke Alert.

Uploads forecast data and frontend to S3 after SAM deployment.
Run this AFTER `sam deploy` completes.

Usage:
    python deploy.py --bucket BUCKET_NAME --api-url API_URL
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def upload_data(bucket: str):
    """Upload forecast data to S3."""
    data_dir = Path("data/processed")
    files = {
        "data/forecast.json": data_dir / "forecast.json",
    }

    # Also upload fires as separate JSON if available
    forecast_path = data_dir / "forecast.json"
    if forecast_path.exists():
        with open(forecast_path) as f:
            forecast = json.load(f)
        fires = forecast.get("fires", [])
        fires_path = data_dir / "fires.json"
        with open(fires_path, "w") as f:
            json.dump(fires, f)
        files["data/fires.json"] = fires_path

    for s3_key, local_path in files.items():
        if local_path.exists():
            cmd = f'aws s3 cp "{local_path}" "s3://{bucket}/{s3_key}" --content-type application/json'
            print(f"  Uploading {s3_key}...")
            os.system(cmd)
        else:
            print(f"  [SKIP] {local_path} not found")


def upload_frontend(bucket: str, api_url: str):
    """Upload frontend files to S3, updating API URL."""
    frontend_dir = Path("frontend")

    # Update app.js with the actual API URL
    app_js_path = frontend_dir / "app.js"
    app_js = app_js_path.read_text()

    # Replace the empty API_BASE_URL with the actual URL
    updated_js = app_js.replace(
        "const API_BASE_URL = '';",
        f"const API_BASE_URL = '{api_url}';",
    )

    # Write updated version temporarily
    temp_js = frontend_dir / "app_deployed.js"
    temp_js.write_text(updated_js)

    # Upload frontend files
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
    }

    for file_path in frontend_dir.iterdir():
        if file_path.is_file() and file_path.suffix in content_types:
            s3_key = f"frontend/{file_path.name}"
            ct = content_types[file_path.suffix]

            # Use the deployed version of app.js
            if file_path.name == "app.js":
                upload_path = temp_js
            elif file_path.name == "app_deployed.js":
                continue  # Don't upload the temp file
            else:
                upload_path = file_path

            cmd = f'aws s3 cp "{upload_path}" "s3://{bucket}/{s3_key}" --content-type "{ct}"'
            print(f"  Uploading {s3_key}...")
            os.system(cmd)

    # Also upload forecast.json to frontend directory for fallback
    forecast_src = Path("data/processed/forecast.json")
    if forecast_src.exists():
        cmd = f'aws s3 cp "{forecast_src}" "s3://{bucket}/frontend/forecast.json" --content-type application/json'
        print("  Uploading frontend/forecast.json (fallback)...")
        os.system(cmd)

    # Cleanup
    if temp_js.exists():
        temp_js.unlink()

    print(f"\n  Frontend URL: http://{bucket}.s3-website-ap-south-1.amazonaws.com/frontend/index.html")


def main():
    parser = argparse.ArgumentParser(description="Deploy Stubble Smoke Alert to AWS")
    parser.add_argument("--bucket", required=True, help="S3 bucket name (from SAM output)")
    parser.add_argument("--api-url", required=True, help="API Gateway URL (from SAM output)")
    args = parser.parse_args()

    print("=" * 50)
    print("Deploying Stubble Smoke Alert")
    print("=" * 50)

    print("\n1. Uploading forecast data to S3...")
    upload_data(args.bucket)

    print("\n2. Uploading frontend to S3...")
    upload_frontend(args.bucket, args.api_url)

    print("\n" + "=" * 50)
    print("Deployment complete!")
    print("=" * 50)
    print(f"\nAPI URL: {args.api_url}")
    print(f"Frontend: http://{args.bucket}.s3-website-ap-south-1.amazonaws.com/frontend/index.html")


if __name__ == "__main__":
    main()
