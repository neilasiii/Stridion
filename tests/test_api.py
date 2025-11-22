"""
API integration tests for settings endpoints.

Tests the REST API endpoints with validation.
"""

import pytest
import json
from unittest.mock import Mock, patch


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client for Flask app."""
    from src.web.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# =============================================================================
# VDOT Calculator API Tests
# =============================================================================

class TestVDOTCalculatorAPI:
    """Test VDOT calculation API endpoints."""

    @patch('src.settings_manager.vdot')
    def test_calculate_vdot_success(self, mock_vdot, client):
        """Test successful VDOT calculation from race time."""
        mock_vdot.vdot_from_time_and_distance.return_value = 42.5

        response = client.post(
            '/api/v1/settings/calculate-vdot',
            data=json.dumps({'distance': '5k', 'time': '25:30'}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'vdot' in data
        assert data['vdot'] == 42.5

    def test_calculate_vdot_invalid_distance(self, client):
        """Test VDOT calculation with invalid distance."""
        response = client.post(
            '/api/v1/settings/calculate-vdot',
            data=json.dumps({'distance': 'invalid', 'time': '25:30'}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Validation failed'
        assert 'details' in data
        assert 'distance' in data['details']

    def test_calculate_vdot_invalid_time_format(self, client):
        """Test VDOT calculation with invalid time format."""
        response = client.post(
            '/api/v1/settings/calculate-vdot',
            data=json.dumps({'distance': '5k', 'time': 'invalid'}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation failed' in data['error']

    def test_calculate_vdot_missing_data(self, client):
        """Test VDOT calculation with missing data."""
        response = client.post(
            '/api/v1/settings/calculate-vdot',
            data=json.dumps({'distance': '5k'}),  # Missing 'time'
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_calculate_paces_success(self, client):
        """Test successful pace calculation from VDOT."""
        response = client.post(
            '/api/v1/settings/calculate-paces',
            data=json.dumps({'vdot': 45.0}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check all pace zones are present
        assert 'easy_pace' in data
        assert 'marathon_pace' in data
        assert 'threshold_pace' in data
        assert 'interval_pace' in data

    def test_calculate_paces_vdot_too_low(self, client):
        """Test pace calculation with VDOT below minimum."""
        response = client.post(
            '/api/v1/settings/calculate-paces',
            data=json.dumps({'vdot': 25.0}),  # Below minimum of 30
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation failed' in data['error']

    def test_calculate_paces_vdot_too_high(self, client):
        """Test pace calculation with VDOT above maximum."""
        response = client.post(
            '/api/v1/settings/calculate-paces',
            data=json.dumps({'vdot': 90.0}),  # Above maximum of 85
            content_type='application/json'
        )

        assert response.status_code == 400


# =============================================================================
# Settings Update API Tests
# =============================================================================

class TestSettingsUpdateAPI:
    """Test settings update API endpoints."""

    @patch('src.settings_manager.SettingsManager.update_settings')
    def test_update_training_settings_success(self, mock_update, client):
        """Test successful training settings update."""
        mock_update.return_value = {
            'vdot_prescribed': 45.0,
            'current_phase': 'base',
            'weekly_volume_hours': 5.0,
            'weekly_run_count': 4,
        }

        response = client.put(
            '/api/v1/settings/training',
            data=json.dumps({
                'vdot_prescribed': 45.0,
                'current_phase': 'base',
                'weekly_volume_hours': 5.0,
                'weekly_run_count': 4,
                'easy_pace': {'min': '10:00', 'max': '11:00'},
                'marathon_pace': {'min': '9:05', 'max': '9:15'},
                'threshold_pace': {'min': '8:30', 'max': '8:40'},
                'interval_pace': {'min': '7:55', 'max': '8:05'},
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['vdot_prescribed'] == 45.0

    def test_update_training_settings_invalid_phase(self, client):
        """Test training settings update with invalid phase."""
        response = client.put(
            '/api/v1/settings/training',
            data=json.dumps({
                'vdot_prescribed': 45.0,
                'current_phase': 'invalid_phase',  # Invalid
                'weekly_volume_hours': 5.0,
                'weekly_run_count': 4,
                'easy_pace': {'min': '10:00', 'max': '11:00'},
                'marathon_pace': {'min': '9:05', 'max': '9:15'},
                'threshold_pace': {'min': '8:30', 'max': '8:40'},
                'interval_pace': {'min': '7:55', 'max': '8:05'},
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation failed' in data['error']
        assert 'current_phase' in data['details']

    def test_update_training_settings_invalid_vdot(self, client):
        """Test training settings update with invalid VDOT."""
        response = client.put(
            '/api/v1/settings/training',
            data=json.dumps({
                'vdot_prescribed': 90.0,  # Too high
                'current_phase': 'base',
                'weekly_volume_hours': 5.0,
                'weekly_run_count': 4,
                'easy_pace': {'min': '10:00', 'max': '11:00'},
                'marathon_pace': {'min': '9:05', 'max': '9:15'},
                'threshold_pace': {'min': '8:30', 'max': '8:40'},
                'interval_pace': {'min': '7:55', 'max': '8:05'},
            }),
            content_type='application/json'
        )

        assert response.status_code == 400

    @patch('src.settings_manager.SettingsManager.update_settings')
    def test_update_communication_settings_success(self, mock_update, client):
        """Test successful communication settings update."""
        mock_update.return_value = {
            'detail_level': 'DETAILED',
            'include_paces': True,
        }

        response = client.put(
            '/api/v1/settings/communication',
            data=json.dumps({
                'detail_level': 'DETAILED',
                'include_paces': True,
            }),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_update_communication_settings_invalid_detail_level(self, client):
        """Test communication settings with invalid detail level."""
        response = client.put(
            '/api/v1/settings/communication',
            data=json.dumps({
                'detail_level': 'INVALID',  # Not BRIEF/STANDARD/DETAILED
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'detail_level' in data['details']

    def test_update_settings_unknown_category(self, client):
        """Test settings update with unknown category."""
        response = client.put(
            '/api/v1/settings/unknown_category',
            data=json.dumps({'some': 'data'}),
            content_type='application/json'
        )

        assert response.status_code == 400


# =============================================================================
# Settings Retrieval API Tests
# =============================================================================

class TestSettingsRetrievalAPI:
    """Test settings retrieval API endpoints."""

    @patch('src.settings_manager.SettingsManager.get_settings')
    def test_get_settings_category_success(self, mock_get, client):
        """Test successful settings retrieval for a category."""
        mock_get.return_value = {
            'detail_level': 'BRIEF',
            'include_paces': True,
        }

        response = client.get('/api/v1/settings/communication')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'detail_level' in data

    @patch('src.settings_manager.SettingsManager.get_settings')
    def test_get_settings_unknown_category(self, mock_get, client):
        """Test settings retrieval for unknown category."""
        mock_get.return_value = None

        response = client.get('/api/v1/settings/unknown')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
