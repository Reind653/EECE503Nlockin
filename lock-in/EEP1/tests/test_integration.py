import unittest
import json
import sys
import os
import logging
from unittest.mock import patch, MagicMock
import requests

# Add parent directory to path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app
from helpers import reset_schedules, save_schedule, load_schedule

class TestEEP1Integration(unittest.TestCase):
    """Integration tests for EEP1 Schedule Management Service with other components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # URLs for services - use environment variables or defaults for testing
        cls.IEP1_URL = os.environ.get("IEP1_URL", "http://localhost:5001")
        cls.IEP2_URL = os.environ.get("IEP2_URL", "http://localhost:5004")
        cls.IEP3_URL = os.environ.get("IEP3_URL", "http://localhost:5003")
        cls.IEP4_URL = os.environ.get("IEP4_URL", "http://localhost:5005")

    def setUp(self):
        """Set up test environment before each test."""
        # Check if we're running in test mode or with real services
        self.mock_mode = os.environ.get("TEST_MOCK_MODE", "True").lower() == "true"
        
        # Set up Flask test client
        app.app.testing = True
        self.client = app.app.test_client()
        
        # Reset schedules before each test to ensure clean state
        reset_schedules()
        
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
        # Sample schedule data for testing
        self.sample_schedule = {
            "meetings": [
                {
                    "id": "meeting-1",
                    "description": "CS101 Lecture",
                    "day": "Monday",
                    "time": "09:00",
                    "duration_minutes": 60,
                    "type": "regular",
                    "location": "Room 101",
                    "course_code": "CS101",
                    "missing_info": []
                }
            ],
            "tasks": [
                {
                    "id": "task-1",
                    "description": "Complete CS101 Assignment",
                    "day": "Tuesday",
                    "time": "16:00",
                    "duration_minutes": 120,
                    "priority": "high",
                    "category": "homework",
                    "is_fixed_time": False,
                    "course_code": "CS101",
                    "related_event": "CS101 Lecture",
                    "missing_info": []
                }
            ],
            "course_codes": ["CS101"]
        }
        
        # Sample schedule text for parsing
        self.sample_schedule_text = """I have a CS101 lecture on Monday at 9am that lasts 1 hour in Room 101. 
        On Tuesday I need to complete my CS101 assignment, which will take about 2 hours, I'll start around 4pm."""

    def tearDown(self):
        """Clean up after each test."""
        # Reset all schedules to clean state
        reset_schedules()
        
        # Re-enable logging
        logging.disable(logging.NOTSET)

    @patch('app.requests.post')
    def test_parse_schedule_iep1_integration(self, mock_post):
        """Test integration with IEP1 for schedule parsing."""
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_schedule
        mock_post.return_value = mock_response
        
        # Call the EEP1 parse-schedule endpoint
        response = self.client.post(
            '/parse-schedule',
            json={'text': self.sample_schedule_text},
            content_type='application/json'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'complete')
        
        # Verify IEP1 was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], f"{self.IEP1_URL}/predict")
        self.assertIn('prompt', kwargs['json'])
        self.assertIn(self.sample_schedule_text, kwargs['json']['prompt'])

    def test_basic_integration_flow(self):
        """Test a basic integration flow with mocked responses."""
        if self.mock_mode:
            # Mock all the necessary API calls
            with patch('app.requests.post') as mock_post:
                # Configure the mock for IEP1 parsing
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = self.sample_schedule
                mock_post.return_value = mock_response
                
                # Step 1: Parse the schedule
                parse_response = self.client.post(
                    '/parse-schedule',
                    json={'text': self.sample_schedule_text},
                    content_type='application/json'
                )
                
                # Verify the parsing response
                self.assertEqual(parse_response.status_code, 200)
                parse_data = json.loads(parse_response.data)
                self.assertEqual(parse_data['status'], 'complete')
                
                # Verify schedules are stored properly
                saved_schedule = load_schedule()
                self.assertIsNotNone(saved_schedule)
                self.assertEqual(len(saved_schedule['meetings']), 1)
                self.assertEqual(len(saved_schedule['tasks']), 1)
        else:
            # Skip the test in real mode
            self.skipTest("Skipping integration test in real mode")

if __name__ == '__main__':
    unittest.main() 