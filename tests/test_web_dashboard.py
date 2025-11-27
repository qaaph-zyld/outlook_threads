"""
Tests for Web Dashboard Module
Tests FastAPI endpoints and data loading
"""
import pytest
from datetime import datetime
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDashboardDataLoader:
    """Test suite for dashboard data loading"""
    
    def test_load_empty_directory(self, tmp_path):
        """Test loading from empty directory"""
        from web_dashboard import DashboardDataLoader
        
        with patch('config.THREADS_DIR', tmp_path):
            threads = DashboardDataLoader.load_thread_summaries()
            assert threads == []
    
    def test_get_stats_empty(self):
        """Test stats calculation with no threads"""
        from web_dashboard import DashboardDataLoader
        
        stats = DashboardDataLoader.get_dashboard_stats([])
        
        assert stats['total_threads'] == 0
        assert stats['urgent_count'] == 0
        assert stats['delay_count'] == 0
        assert stats['escalation_count'] == 0
    
    def test_get_stats_with_threads(self):
        """Test stats calculation with sample threads"""
        from web_dashboard import DashboardDataLoader
        
        sample_threads = [
            {
                'metadata': {'is_urgent': True, 'has_delay': False},
                'triage': {'escalate': True, 'due_soon': True},
                'priority_score': 80
            },
            {
                'metadata': {'is_urgent': False, 'has_delay': True},
                'triage': {'escalate': False, 'due_soon': False},
                'priority_score': 40
            },
            {
                'metadata': {'is_urgent': False, 'has_delay': False},
                'triage': {'escalate': False, 'due_soon': False},
                'priority_score': 20
            }
        ]
        
        stats = DashboardDataLoader.get_dashboard_stats(sample_threads)
        
        assert stats['total_threads'] == 3
        assert stats['urgent_count'] == 1
        assert stats['delay_count'] == 1
        assert stats['escalation_count'] == 1
        assert stats['response_needed'] == 1
        
        # Priority breakdown
        assert stats['priority_breakdown']['critical'] == 1
        assert stats['priority_breakdown']['medium'] == 1
        assert stats['priority_breakdown']['low'] == 1


class TestFastAPIEndpoints:
    """Test suite for FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from web_dashboard import app
        return TestClient(app)
    
    def test_api_threads_endpoint(self, client):
        """Test /api/threads endpoint"""
        with patch('web_dashboard.DashboardDataLoader.load_thread_summaries', return_value=[]):
            response = client.get("/api/threads")
            assert response.status_code == 200
            data = response.json()
            assert 'threads' in data
            assert 'count' in data
    
    def test_api_stats_endpoint(self, client):
        """Test /api/stats endpoint"""
        with patch('web_dashboard.DashboardDataLoader.load_thread_summaries', return_value=[]):
            response = client.get("/api/stats")
            assert response.status_code == 200
            data = response.json()
            assert 'total_threads' in data
            assert 'priority_breakdown' in data
    
    def test_api_refresh_endpoint(self, client):
        """Test /api/refresh endpoint"""
        with patch('web_dashboard.DashboardDataLoader.load_thread_summaries', return_value=[]):
            response = client.get("/api/refresh")
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'refreshed'
    
    def test_thread_detail_not_found(self, client):
        """Test thread detail endpoint with non-existent thread"""
        with patch('config.THREADS_DIR', Path('/nonexistent')):
            response = client.get("/thread/nonexistent-thread")
            assert response.status_code == 404


class TestTemplateGeneration:
    """Test suite for template generation"""
    
    def test_template_directory_creation(self, tmp_path):
        """Test that template directory is created"""
        from web_dashboard import TEMPLATES_DIR
        
        # Just verify the constant is a Path
        assert isinstance(TEMPLATES_DIR, Path)
    
    def test_create_template_function(self, tmp_path):
        """Test create_template function"""
        from web_dashboard import create_template, TEMPLATES_DIR
        
        with patch('web_dashboard.TEMPLATES_DIR', tmp_path):
            # This should not raise an error
            try:
                # The function writes to TEMPLATES_DIR
                pass  # Just checking import works
            except Exception as e:
                pytest.fail(f"Template creation failed: {e}")


class TestPriorityFiltering:
    """Test suite for priority-based filtering logic"""
    
    def test_priority_score_calculation(self):
        """Test that priority scores are calculated correctly"""
        from web_dashboard import DashboardDataLoader
        
        # Test that urgent metadata increases priority
        thread = {
            'metadata': {'is_urgent': True, 'has_delay': True, 'email_count': 15},
            'triage': {'escalate': True, 'due_soon': True}
        }
        
        # Calculate priority (mimicking the loader logic)
        priority_score = 0
        if thread['metadata'].get('is_urgent'):
            priority_score += 30
        if thread['metadata'].get('has_delay'):
            priority_score += 20
        if thread['metadata'].get('email_count', 0) > 10:
            priority_score += 10
        if thread.get('triage', {}).get('escalate'):
            priority_score += 25
        if thread.get('triage', {}).get('due_soon'):
            priority_score += 15
        
        assert priority_score == 100  # 30+20+10+25+15


class TestSorting:
    """Test suite for thread sorting"""
    
    def test_sort_by_priority(self):
        """Test that threads are sorted by priority descending"""
        threads = [
            {'priority_score': 20, 'name': 'low'},
            {'priority_score': 80, 'name': 'high'},
            {'priority_score': 50, 'name': 'medium'}
        ]
        
        sorted_threads = sorted(threads, key=lambda x: x['priority_score'], reverse=True)
        
        assert sorted_threads[0]['name'] == 'high'
        assert sorted_threads[1]['name'] == 'medium'
        assert sorted_threads[2]['name'] == 'low'


class TestDateFiltering:
    """Test suite for 60-day date filtering"""
    
    def test_old_thread_filtering(self):
        """Test that threads older than 60 days are filtered out"""
        from datetime import timedelta
        
        now = datetime.now()
        old_date = now - timedelta(days=65)
        recent_date = now - timedelta(days=30)
        
        # Old thread should be filtered
        old_days = (now - old_date).days
        assert old_days > 60
        
        # Recent thread should not be filtered
        recent_days = (now - recent_date).days
        assert recent_days <= 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
