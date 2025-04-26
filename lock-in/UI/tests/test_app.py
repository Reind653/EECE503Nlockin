import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock
import logging

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


class TestUIApp(unittest.TestCase):
    """Unit tests for UI Flask Application."""

    def setUp(self):
        """Set up test environment before each test."""
        # Set up Flask test client
        app.app.testing = True
        self.client = app.app.test_client()
        
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
        # Sample user data for testing
        self.test_user = {
            'email': 'test@example.com',
            'password': 'password123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
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
        
        # Mock SQLite Cloud connection and cursor
        self.patcher_conn = patch('app.get_cloud_connection')
        self.mock_conn = self.patcher_conn.start()
        self.mock_cursor = MagicMock()
        self.mock_conn.return_value.cursor.return_value = self.mock_cursor
        
        # Mock session for authenticated routes
        self.patcher_session = patch('app.session', {'user': 'test@example.com'})
        self.mock_session = self.patcher_session.start()

    def tearDown(self):
        """Clean up after each test."""
        # Re-enable logging
        logging.disable(logging.NOTSET)
        
        # Stop the patchers
        self.patcher_conn.stop()
        self.patcher_session.stop()

    def test_index_route_with_no_recent_schedule(self):
        """Test index route when user has no recent schedule."""
        # Configure mock cursor to return a user with no recent schedule
        self.mock_cursor.fetchone.return_value = [1, None, None]  # preferences_completed, latest_schedule, schedule_timestamp
        
        # Call the index route
        response = self.client.get('/')
        
        # Verify response is redirection to index.html template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)  # Verify HTML response

    def test_index_route_with_recent_schedule(self):
        """Test index route when user has a recent schedule."""
        # Configure mock cursor to return a user with a recent schedule
        import datetime
        recent_time = datetime.datetime.utcnow().isoformat()
        self.mock_cursor.fetchone.return_value = [1, json.dumps(self.sample_schedule), recent_time]  # preferences_completed, latest_schedule, schedule_timestamp
        
        # Call the index route
        response = self.client.get('/')
        
        # Verify response is redirection to schedule-only.html template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)  # Verify HTML response

    def test_login_route_get(self):
        """Test login route GET method."""
        # Stop the session patcher to simulate no logged-in user
        self.patcher_session.stop()
        
        # Call the login route with GET method
        response = self.client.get('/login')
        
        # Verify response is login.html template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)
        self.assertIn(b'Login', response.data)
        
        # Restart the session patcher for other tests
        self.patcher_session = patch('app.session', {'user': 'test@example.com'})
        self.mock_session = self.patcher_session.start()

    @patch('app.check_password_hash')
    @patch('app.redirect')
    @patch('app.session')
    def test_login_route_post_success(self, mock_session, mock_redirect, mock_check_password_hash):
        """Test login route POST method with correct credentials."""
        # Stop the session patcher to simulate no logged-in user
        self.patcher_session.stop()
        
        # Configure mock cursor to return a user
        self.mock_cursor.fetchone.return_value = [1, 'hashed_password', 'Test', 'User', 1]  # id, password, first_name, last_name, preferences_completed
        
        # Configure password hash check to return True
        mock_check_password_hash.return_value = True
        
        # Call the login route with POST method
        response = self.client.post(
            '/login',
            data={'email': 'test@example.com', 'password': 'password123'},
            follow_redirects=True
        )
        
        # Verify user was logged in
        self.mock_cursor.execute.assert_called_with("SELECT id, password, first_name, last_name, preferences_completed FROM user WHERE email = ?", ('test@example.com',))
        
        # Restart the session patcher for other tests
        self.patcher_session = patch('app.session', {'user': 'test@example.com'})
        self.mock_session = self.patcher_session.start()

    @patch('app.requests.post')
    def test_parse_schedule_route(self, mock_post):
        """Test parse-schedule route with successful parsing response."""
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'complete',
            'schedule': self.sample_schedule
        }
        mock_post.return_value = mock_response
        
        # Call the parse-schedule endpoint
        response = self.client.post(
            '/parse-schedule',
            json={'text': 'I have a CS101 lecture on Monday at 9am'},
            content_type='application/json'
        )
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('redirect', data)
        
        # Verify EEP1 was called correctly
        mock_post.assert_called_once()
        self.assertIn('/parse-schedule', mock_post.call_args[0][0])

    def test_preferences_route_get(self):
        """Test preferences route GET method."""
        # Configure mock cursor to return a user with incomplete preferences
        self.mock_cursor.fetchone.return_value = [0, None]  # preferences_completed, preferences
        
        # Call the preferences route with GET method
        response = self.client.get('/preferences')
        
        # Verify response is preferences.html template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)
        self.assertIn(b'Preferences', response.data)

    def test_logout_route(self):
        """Test logout route."""
        # Call the logout route
        response = self.client.get('/logout', follow_redirects=True)
        
        # Verify response is redirection to login page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', response.data)
        self.assertIn(b'Login', response.data)

    @patch('app.requests.post')
    def test_get_schedule_route(self, mock_post):
        """Test get-schedule route."""
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'schedule': self.sample_schedule
        }
        mock_post.return_value = mock_response
        
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
    def test_reset_schedule_route(self, mock_post):
        """Test reset-schedule route."""
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'stored schedule reset'
        }
        mock_post.return_value = mock_response
        
        # Call the reset-schedule endpoint
        response = self.client.post('/reset-schedule')
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify EEP1 was called correctly
        mock_post.assert_called_once()
        self.assertIn('/reset-stored-schedule', mock_post.call_args[0][0])


if __name__ == '__main__':
    unittest.main() 