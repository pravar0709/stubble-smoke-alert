"""
Tests for the Lambda API handler.

Mocks S3 to test response shape, error handling, and CORS headers.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.lambda_handler import handler, CORS_HEADERS


@pytest.fixture
def mock_s3():
    """Mock boto3 S3 client."""
    with patch('src.lambda_handler.s3_client') as mock:
        yield mock


def _make_event(path, method='GET'):
    """Create a minimal API Gateway HTTP API event."""
    return {
        'rawPath': path,
        'requestContext': {
            'http': {
                'method': method,
                'path': path,
            },
        },
    }


class TestForecastEndpoint:
    """Test GET /forecast endpoint."""

    def test_returns_200_with_forecast(self, mock_s3):
        """Should return forecast JSON from S3."""
        forecast_data = {
            'forecast_date': '2024-10-15',
            'predicted_aqi_band': 'Very Poor',
            'action': 'Move PE indoors.',
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(forecast_data).encode('utf-8'))
        }

        response = handler(_make_event('/forecast'), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['predicted_aqi_band'] == 'Very Poor'
        assert body['forecast_date'] == '2024-10-15'

    def test_returns_cors_headers(self, mock_s3):
        """Response must include CORS headers."""
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'{}')
        }

        response = handler(_make_event('/forecast'), None)

        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'GET' in response['headers']['Access-Control-Allow-Methods']

    def test_returns_404_when_no_data(self, mock_s3):
        """Should return 404 if forecast.json not in S3."""
        from botocore.exceptions import ClientError
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
            'GetObject'
        )

        response = handler(_make_event('/forecast'), None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestFiresEndpoint:
    """Test GET /fires endpoint."""

    def test_returns_200_with_fires(self, mock_s3):
        """Should return fire data from S3."""
        fires_data = [
            {'lat': 30.5, 'lon': 76.2, 'frp': 25.3},
        ]
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(fires_data).encode('utf-8'))
        }

        response = handler(_make_event('/fires'), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert isinstance(body, list)
        assert body[0]['lat'] == 30.5


class TestRouting:
    """Test API routing."""

    def test_unknown_path_returns_404(self, mock_s3):
        """Unknown paths should return 404 with available endpoints."""
        response = handler(_make_event('/unknown'), None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert '/forecast' in body['available_endpoints']

    def test_options_returns_200(self, mock_s3):
        """OPTIONS request for CORS preflight should return 200."""
        response = handler(_make_event('/forecast', method='OPTIONS'), None)

        assert response['statusCode'] == 200
        assert response['headers']['Access-Control-Allow-Origin'] == '*'


class TestResponseShape:
    """Test that API responses have the expected shape."""

    def test_forecast_response_has_required_fields(self, mock_s3):
        """Forecast response must include all fields the frontend needs."""
        forecast = {
            'forecast_date': '2024-10-15',
            'generated_at': '2024-10-14T18:00:00Z',
            'predicted_aqi_band': 'Poor',
            'predicted_aqi_range': '101-200',
            'action': 'Shorten outdoor activity.',
            'severity': 3,
            'color': '#ff9800',
            'reason': 'NW winds with fire detections.',
            'fires': [],
            'delhi': {'lat': 28.6139, 'lon': 77.209},
            'disclaimer': 'Experimental forecast.',
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(forecast).encode('utf-8'))
        }

        response = handler(_make_event('/forecast'), None)
        body = json.loads(response['body'])

        required_keys = [
            'forecast_date', 'predicted_aqi_band', 'predicted_aqi_range',
            'action', 'severity', 'color', 'reason', 'fires', 'delhi',
            'disclaimer',
        ]
        for key in required_keys:
            assert key in body, f"Missing required key: {key}"

    def test_content_type_is_json(self, mock_s3):
        """Content-Type must be application/json."""
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'{}')
        }

        response = handler(_make_event('/forecast'), None)
        assert response['headers']['Content-Type'] == 'application/json'
