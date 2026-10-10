"""
AWS Lambda handler for Stubble Smoke Alert API.

Serves two endpoints via API Gateway HTTP API:
  GET /forecast  - Returns the latest forecast JSON from S3
  GET /fires     - Returns recent fire detection data from S3

Designed to be lightweight: reads pre-computed JSON from S3,
no ML dependencies in Lambda.
"""

import json
import os
import boto3
from botocore.exceptions import ClientError


# S3 configuration from environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'stubble-smoke-alert-bucket')
FORECAST_KEY = 'data/forecast.json'
FIRES_KEY = 'data/fires.json'

# Initialize S3 client (reused across Lambda invocations)
s3_client = boto3.client('s3')

# CORS headers for all responses
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}


def handler(event, context):
    """
    Main Lambda handler for API Gateway HTTP API events.

    Routes:
        GET /forecast  - Latest AQI forecast
        GET /fires     - Recent fire detections
        OPTIONS /*     - CORS preflight
    """
    # Handle CORS preflight
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '')
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': '',
        }

    # Get the path
    path = event.get('rawPath', event.get('path', '/'))

    if path == '/forecast':
        return _get_s3_json(FORECAST_KEY)
    elif path == '/fires':
        return _get_s3_json(FIRES_KEY)
    else:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': 'Not found',
                'available_endpoints': ['/forecast', '/fires'],
            }),
        }


def _get_s3_json(key):
    """
    Read a JSON file from S3 and return it as an API response.

    Args:
        key: S3 object key.

    Returns:
        API Gateway response dict.
    """
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        body = response['Body'].read().decode('utf-8')

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': body,
        }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'error': f'Data not found: {key}',
                    'message': 'Forecast has not been generated yet. Run the pipeline first.',
                }),
            }
        else:
            return {
                'statusCode': 500,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': str(e),
                }),
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
            }),
        }
