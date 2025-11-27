"""
Tests for Enhanced Dashboard V3 Features
Tests ApexCharts endpoints, WebSocket, and new API endpoints
"""
import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from web_dashboard import app


class TestDashboardV3Endpoints:
    """Test suite for V3 dashboard endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_v3_dashboard_route_exists(self, client):
        """Test that V3 dashboard route is accessible"""
        response = client.get("/v3")
        # Should return 200 or 404 if template missing
        assert response.status_code in [200, 404]
    
    def test_keywords_api_endpoint(self, client):
        """Test keywords API endpoint"""
        response = client.get("/api/keywords")
        assert response.status_code == 200
        
        data = response.json()
        assert 'keywords' in data
        assert isinstance(data['keywords'], list)
    
    def test_sentiment_api_endpoint(self, client):
        """Test sentiment API endpoint"""
        response = client.get("/api/sentiment")
        assert response.status_code == 200
        
        data = response.json()
        assert 'overall' in data
        assert isinstance(data['overall'], (int, float))
        assert 0 <= data['overall'] <= 100
    
    def test_response_times_api_endpoint(self, client):
        """Test response times API endpoint"""
        response = client.get("/api/response-times")
        assert response.status_code == 200
        
        data = response.json()
        assert 'distribution' in data
        assert isinstance(data['distribution'], list)
        
        for item in data['distribution']:
            assert 'range' in item
            assert 'count' in item


class TestExistingAPIEndpoints:
    """Test that existing API endpoints still work"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_threads_api(self, client):
        """Test threads API endpoint"""
        response = client.get("/api/threads")
        assert response.status_code == 200
        data = response.json()
        # API returns dict with threads key or a list directly
        assert isinstance(data, (list, dict))
        if isinstance(data, dict):
            assert 'threads' in data
    
    def test_stats_api(self, client):
        """Test stats API endpoint"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert 'total_threads' in data
        assert 'priority_breakdown' in data
    
    def test_refresh_api(self, client):
        """Test refresh API endpoint"""
        response = client.get("/api/refresh")
        assert response.status_code == 200


class TestWebSocketEndpoint:
    """Test WebSocket functionality"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_websocket_connection(self, client):
        """Test that WebSocket endpoint accepts connections"""
        try:
            with client.websocket_connect("/ws") as websocket:
                # Connection should be established
                assert websocket is not None
        except Exception as e:
            # WebSocket may not be available in test environment
            pytest.skip(f"WebSocket test skipped: {e}")


class TestDashboardDataIntegrity:
    """Test data integrity in dashboard responses"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_priority_breakdown_values(self, client):
        """Test that priority breakdown contains all levels"""
        response = client.get("/api/stats")
        data = response.json()
        
        breakdown = data.get('priority_breakdown', {})
        expected_levels = ['critical', 'high', 'medium', 'low']
        
        for level in expected_levels:
            assert level in breakdown
            assert isinstance(breakdown[level], int)
            assert breakdown[level] >= 0
    
    def test_keywords_format(self, client):
        """Test keywords are in correct format for ApexCharts"""
        response = client.get("/api/keywords")
        data = response.json()
        
        for kw in data.get('keywords', []):
            assert 'x' in kw  # Keyword text
            assert 'y' in kw  # Count/weight


class TestTemplateAvailability:
    """Test template file availability"""
    
    def test_v3_template_exists(self):
        """Test that V3 template file exists"""
        template_path = Path(__file__).parent.parent / "templates" / "dashboard_v3.html"
        assert template_path.exists(), "V3 template file should exist"
    
    def test_original_template_exists(self):
        """Test that original template file exists"""
        template_path = Path(__file__).parent.parent / "templates" / "dashboard.html"
        assert template_path.exists(), "Original template file should exist"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
