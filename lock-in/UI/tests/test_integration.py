import unittest
import json
import sys
import os
import logging
from unittest.mock import patch, MagicMock
import requests

# Mock flask_sqlalchemy before importing app
sys.modules['flask_sqlalchemy'] = MagicMock()
sys.modules['sqlitecloud'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()

# Add parent directory to path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up mock return values for functions that will be used
flask_sqlalchemy_mock = sys.modules['flask_sqlalchemy']
SQLAlchemy_mock = MagicMock()
flask_sqlalchemy_mock.SQLAlchemy = SQLAlchemy_mock

werkzeug_security_mock = sys.modules['werkzeug.security']
werkzeug_security_mock.generate_password_hash = MagicMock(return_value='hashed_password')
werkzeug_security_mock.check_password_hash = MagicMock(return_value=True)

# Now import app
import app
from preference_questions import PREFERENCE_QUESTIONS, get_default_preferences

class TestUIIntegration(unittest.TestCase):
    """Integration tests for UI component with other services."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # URLs for services - use environment variables or defaults for testing
        cls.EEP1_URL = os.environ.get("EEP1_URL", "http://localhost:5000")
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
        
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
        # Mock SQLite Cloud connection and cursor
        self.patcher_conn = patch('app.get_cloud_connection')
        self.mock_conn = self.patcher_conn.start()
        self.mock_cursor = MagicMock()
        self.mock_conn.return_value.cursor.return_value = self.mock_cursor
        
        # Mock session for authenticated routes
        self.patcher_session = patch('app.session', {'user': 'test@example.com'})
        self.mock_session = self.patcher_session.start()
        
        # Sample schedule data
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
        
        # Sample schedule with missing information
        self.schedule_with_missing_info = {
            "meetings": [
                {
                    "id": "meeting-1",
                    "description": "CS101 Exam",
                    "day": "Monday",
                    "time": None,
                    "duration_minutes": None,
                    "type": "exam",
                    "location": "Room 101",
                    "course_code": "CS101",
                    "missing_info": ["time", "duration_minutes"]
                }
            ],
            "tasks": [],
            "course_codes": ["CS101"]
        }

    def tearDown(self):
        """Clean up after each test."""
        # Re-enable logging
        logging.disable(logging.NOTSET)
        
        # Stop the patchers
        self.patcher_conn.stop()
        self.patcher_session.stop()

    @patch('app.requests.post')
    def test_parse_schedule_integration_with_eep1(self, mock_post):
        """Test UI integration with EEP1 for parsing schedules."""
        # Configure the mock for EEP1 parsing response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'complete',
            'schedule': self.sample_schedule
        }
        mock_post.return_value = mock_response
        
        # Call the UI parse-schedule endpoint
        response = self.client.post(
            '/parse-schedule',
            json={'text': 'I have a CS101 lecture on Monday at 9am'},
            content_type='application/json'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify EEP1 was called correctly
        mock_post.assert_called_once()
        url_called = mock_post.call_args[0][0]
        self.assertTrue(url_called.endswith('/parse-schedule'))
        
        # Verify SQLite Cloud was updated with the parsed schedule
        self.mock_cursor.execute.assert_called()
        
        # Verify the schedule was updated in the database
        # Find the call that updates the parsed_json in user table
        update_called = False
        for call in self.mock_cursor.execute.call_args_list:
            args, _ = call
            if isinstance(args[0], str) and "UPDATE user SET parsed_json" in args[0]:
                update_called = True
                break
        self.assertTrue(update_called)

    @patch('app.requests.post')
    def test_parse_schedule_with_missing_info(self, mock_post):
        """Test integration when schedule has missing information."""
        # Configure the mock for EEP1 parsing with missing info
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'questions_needed',
            'schedule': self.schedule_with_missing_info,
            'questions': [
                {
                    'item_id': 'meeting-1',
                    'field': 'time',
                    'message': 'What time is the CS101 Exam?'
                },
                {
                    'item_id': 'meeting-1',
                    'field': 'duration_minutes',
                    'message': 'How long is the CS101 Exam?'
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Call the UI parse-schedule endpoint
        response = self.client.post(
            '/parse-schedule',
            json={'text': 'I have a CS101 exam on Monday'},
            content_type='application/json'
        )
        
        # Verify the response indicates questions are needed
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('redirect', data)
        self.assertIn('questions', data)
        
        # Verify the questions were stored in the session

    @patch('app.requests.get')
    def test_get_schedule_integration_with_eep1(self, mock_get):
        """Test UI integration with EEP1 for getting schedules."""
        # Configure mock cursor to return a user with a schedule
        recent_time = "2023-01-01T00:00:00"
        self.mock_cursor.fetchone.return_value = [json.dumps(self.sample_schedule), recent_time]  # latest_schedule, schedule_timestamp
        
        # Call the get-schedule endpoint
        response = self.client.get('/get-schedule')
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('schedule', data)

    @patch('app.requests.post')
    def test_answer_question_integration(self, mock_post):
        """Test integration of answering questions about missing schedule information."""
        # Configure mock cursor to return a user with a schedule with missing info
        self.mock_cursor.fetchone.return_value = [json.dumps(self.schedule_with_missing_info), "2023-01-01T00:00:00"]
        
        # Configure the mock for EEP1 answer-question response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # The response after answering should have fewer missing fields
        updated_schedule = self.schedule_with_missing_info.copy()
        updated_schedule['meetings'][0]['time'] = "14:00"
        updated_schedule['meetings'][0]['missing_info'].remove('time')
        
        mock_response.json.return_value = {
            'status': 'success',
            'schedule': updated_schedule,
            'questions': []  # No more questions after this answer
        }
        mock_post.return_value = mock_response
        
        # Call the answer-question endpoint
        response = self.client.post(
            '/answer-question',
            json={
                'item_id': 'meeting-1',
                'type': 'time',
                'answer': '14:00'
            },
            content_type='application/json'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify EEP1 was called correctly
        mock_post.assert_called_once()
        url_called = mock_post.call_args[0][0]
        self.assertTrue(url_called.endswith('/answer-question'))
        
        # Verify the database was updated with the new schedule information
        update_called = False
        for call in self.mock_cursor.execute.call_args_list:
            args, _ = call
            if isinstance(args[0], str) and "UPDATE user SET parsed_json" in args[0]:
                update_called = True
                break
        self.assertTrue(update_called)

    @patch('app.requests.post')
    def test_integration_end_to_end_flow(self, mock_post):
        """Test an end-to-end flow of the application with mocked services."""
        if self.mock_mode:
            # Setup mock responses for different endpoints
            def mock_post_side_effect(*args, **kwargs):
                url = args[0]
                mock_response = MagicMock()
                
                # Mock response for parse-schedule
                if '/parse-schedule' in url:
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        'status': 'complete',
                        'schedule': self.sample_schedule
                    }
                
                # Mock response for reset-stored-schedule
                elif '/reset-stored-schedule' in url:
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        'status': 'stored schedule reset'
                    }
                
                # Mock response for generate-optimized-schedule
                elif '/generate-optimized-schedule' in url:
                    mock_response.status_code = 200
                    optimized_schedule = self.sample_schedule.copy()
                    # Add some optimization details
                    optimized_schedule['optimization_applied'] = True
                    mock_response.json.return_value = {
                        'status': 'success',
                        'schedule': optimized_schedule
                    }
                
                return mock_response
                
            mock_post.side_effect = mock_post_side_effect
            
            # Configure mock cursor for user data
            self.mock_cursor.fetchone.side_effect = [
                # First call - check if user has preferences
                [1, json.dumps(get_default_preferences())],  # preferences_completed, preferences
                # Second call - check if user has a schedule
                [None, None],  # latest_schedule, schedule_timestamp
                # Third call - after schedule is parsed
                [json.dumps(self.sample_schedule), "2023-01-01T00:00:00"]  # latest_schedule, schedule_timestamp
            ]
            
            # Step 1: Parse a schedule
            parse_response = self.client.post(
                '/parse-schedule',
                json={'text': 'I have a CS101 lecture on Monday at 9am'},
                content_type='application/json'
            )
            
            # Verify parse response
            self.assertEqual(parse_response.status_code, 200)
            parse_data = json.loads(parse_response.data)
            self.assertEqual(parse_data['status'], 'success')
            
            # Step 2: Get the schedule
            get_response = self.client.get('/get-schedule')
            
            # Verify get response
            self.assertEqual(get_response.status_code, 200)
            get_data = json.loads(get_response.data)
            self.assertEqual(get_data['status'], 'success')
            self.assertIn('schedule', get_data)
            
            # Step 3: Generate an optimized schedule
            optimize_response = self.client.post(
                '/generate-optimized-schedule',
                json={'preferences': get_default_preferences()},
                content_type='application/json'
            )
            
            # Verify optimize response
            self.assertEqual(optimize_response.status_code, 200)
            optimize_data = json.loads(optimize_response.data)
            self.assertEqual(optimize_data['status'], 'success')
            
            # Step 4: Reset the schedule
            reset_response = self.client.post('/reset-schedule')
            
            # Verify reset response
            self.assertEqual(reset_response.status_code, 200)
            reset_data = json.loads(reset_response.data)
            self.assertEqual(reset_data['status'], 'success')
        else:
            # Skip the test in real mode
            self.skipTest("Skipping integration test in real mode")

if __name__ == '__main__':
    unittest.main() 