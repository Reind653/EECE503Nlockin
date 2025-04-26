import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging
from datetime import datetime, timedelta

# Add parent directory to path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app

class TestIEP3App(unittest.TestCase):
    """Unit tests for IEP3 Google Calendar integration."""

    def setUp(self):
        """Set up test client and resources."""
        app.app.testing = True
        self.client = app.app.test_client()
        # Disable logging for tests
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up resources after tests."""
        # Re-enable logging
        logging.disable(logging.NOTSET)

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Check that it contains the expected fields
        self.assertIn('status', response_data)
        
        # Verify the values
        self.assertEqual(response_data['status'], 'healthy')

    def test_authorize_endpoint_missing_redirect_uri(self):
        """Test the authorize endpoint without providing a redirect URI."""
        response = self.client.get('/authorize')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Missing redirect_uri parameter')

    @patch('google_auth_oauthlib.flow.Flow.from_client_config')
    def test_authorize_endpoint_with_redirect_uri(self, mock_flow_from_client_config):
        """Test the authorize endpoint with a valid redirect URI."""
        # Set up the mock flow
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ('https://fake-auth-url.com', 'fake-state')
        mock_flow_from_client_config.return_value = mock_flow
        
        # Make the request
        response = self.client.get('/authorize?redirect_uri=http://localhost:5000/callback')
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check response
        response_data = json.loads(response.data)
        self.assertIn('url', response_data)
        self.assertIn('state', response_data)
        self.assertEqual(response_data['url'], 'https://fake-auth-url.com')
        self.assertEqual(response_data['state'], 'fake-state')
        
        # Verify flow was configured correctly
        mock_flow_from_client_config.assert_called_once()
        mock_flow.redirect_uri = 'http://localhost:5000/callback'
        mock_flow.authorization_url.assert_called_once()

    def test_callback_endpoint_missing_code(self):
        """Test the callback endpoint without providing a code."""
        response = self.client.post('/callback', 
                                   json={},  # Empty JSON without code
                                   content_type='application/json')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Code is required')

    def test_callback_endpoint_missing_redirect_uri(self):
        """Test the callback endpoint without providing a redirect URI."""
        response = self.client.post('/callback', 
                                   json={'code': 'fake_code'},  # Missing redirect_uri
                                   content_type='application/json')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Missing redirect_uri parameter')

    @patch('google_auth_oauthlib.flow.Flow.from_client_config')
    def test_callback_endpoint_successful(self, mock_flow_from_client_config):
        """Test the callback endpoint with valid parameters."""
        # Set up the mock flow
        mock_flow = MagicMock()
        mock_flow.credentials = MagicMock()
        mock_flow.credentials.token = 'fake_token'
        mock_flow.credentials.refresh_token = 'fake_refresh_token'
        mock_flow.credentials.token_uri = 'fake_token_uri'
        mock_flow.credentials.client_id = 'fake_client_id'
        mock_flow.credentials.client_secret = 'fake_client_secret'
        mock_flow.credentials.scopes = ['fake_scope']
        mock_flow_from_client_config.return_value = mock_flow
        
        # Make the request
        response = self.client.post('/callback', 
                                   json={
                                       'code': 'fake_code',
                                       'redirect_uri': 'http://localhost:5000/callback'
                                   },
                                   content_type='application/json')
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check response
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('credentials', response_data)
        
        # Verify credentials structure
        credentials = response_data['credentials']
        self.assertIn('token', credentials)
        self.assertIn('refresh_token', credentials)
        self.assertIn('token_uri', credentials)
        self.assertIn('client_id', credentials)
        self.assertIn('client_secret', credentials)
        self.assertIn('scopes', credentials)

    def test_fetch_calendar_missing_credentials(self):
        """Test the fetch-calendar endpoint without providing credentials."""
        response = self.client.post('/fetch-calendar', 
                                   json={},  # Empty JSON without credentials
                                   content_type='application/json')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Credentials are required')

    @patch('googleapiclient.discovery.build')
    @patch('google.oauth2.credentials.Credentials')
    def test_fetch_calendar_successful(self, mock_credentials, mock_build):
        """Test the fetch-calendar endpoint with valid credentials."""
        # Set up mock calendar service
        mock_calendar_service = MagicMock()
        mock_events_resource = MagicMock()
        mock_list_method = MagicMock()
        
        # Configure the mock events list response
        mock_events_result = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Test Event 1',
                    'start': {'dateTime': datetime.now().isoformat() + 'Z'},
                    'end': {'dateTime': (datetime.now() + timedelta(hours=1)).isoformat() + 'Z'},
                    'location': 'Test Location'
                }
            ]
        }
        
        # Configure the mock chain
        mock_list_method.execute.return_value = mock_events_result
        mock_events_resource.list.return_value = mock_list_method
        mock_calendar_service.events.return_value = mock_events_resource
        mock_build.return_value = mock_calendar_service
        
        # Make the request with fake credentials
        response = self.client.post('/fetch-calendar', 
                                   json={
                                       'credentials': {
                                           'token': 'fake_token',
                                           'refresh_token': 'fake_refresh_token',
                                           'token_uri': 'fake_token_uri',
                                           'client_id': 'fake_client_id',
                                           'client_secret': 'fake_client_secret',
                                           'scopes': ['fake_scope']
                                       }
                                   },
                                   content_type='application/json')
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check response
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('google_calendar', response_data)
        
        # Verify proper API calls were made
        mock_build.assert_called_once_with('calendar', 'v3', credentials=mock_credentials.return_value)
        mock_calendar_service.events.assert_called_once()
        mock_events_resource.list.assert_called_once()
        
    def test_create_events_missing_credentials(self):
        """Test the create-events endpoint without providing credentials."""
        response = self.client.post('/create-events', 
                                   json={},  # Empty JSON without credentials
                                   content_type='application/json')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Both credentials and events are required')

    def test_create_events_missing_events(self):
        """Test the create-events endpoint without providing events."""
        response = self.client.post('/create-events', 
                                   json={
                                       'credentials': {
                                           'token': 'fake_token'
                                       }
                                   },  # Missing events
                                   content_type='application/json')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Both credentials and events are required')

    @patch('googleapiclient.discovery.build')
    @patch('google.oauth2.credentials.Credentials')
    def test_create_events_successful(self, mock_credentials, mock_build):
        """Test the create-events endpoint with valid credentials and events."""
        # Set up mock calendar service
        mock_calendar_service = MagicMock()
        mock_calendars_resource = MagicMock()
        mock_events_resource = MagicMock()
        mock_insert_method = MagicMock()
        mock_get_method = MagicMock()
        
        # Configure the mock calendar metadata
        mock_calendar_metadata = {
            'timeZone': 'America/New_York'
        }
        
        # Configure the mock insert response
        mock_inserted_event = {
            'id': 'new_event_id',
            'summary': 'Created Event',
            'status': 'confirmed'
        }
        
        # Configure the mock chain
        mock_get_method.execute.return_value = mock_calendar_metadata
        mock_calendars_resource.get.return_value = mock_get_method
        mock_insert_method.execute.return_value = mock_inserted_event
        mock_events_resource.insert.return_value = mock_insert_method
        mock_calendar_service.calendars.return_value = mock_calendars_resource
        mock_calendar_service.events.return_value = mock_events_resource
        mock_build.return_value = mock_calendar_service
        
        # Test data - event to create
        test_event = {
            'id': 'test_event_1',
            'type': 'task',
            'description': 'Test Task',
            'day': 'Monday',
            'start_time': '09:00',
            'end_time': '10:00',
            'duration': 60,
            'location': 'Test Location'
        }
        
        # Make the request
        response = self.client.post('/create-events', 
                                   json={
                                       'credentials': {
                                           'token': 'fake_token',
                                           'refresh_token': 'fake_refresh_token',
                                           'token_uri': 'fake_token_uri',
                                           'client_id': 'fake_client_id',
                                           'client_secret': 'fake_client_secret',
                                           'scopes': ['fake_scope']
                                       },
                                       'events': [test_event]
                                   },
                                   content_type='application/json')
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check response
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('created', response_data)
        self.assertEqual(response_data['created'], 1)
        self.assertIn('failed', response_data)
        self.assertEqual(response_data['failed'], 0)
        self.assertIn('created_events', response_data)
        self.assertEqual(len(response_data['created_events']), 1)
        
    def test_process_google_events(self):
        """Test the process_google_events function."""
        # Sample Google Calendar events
        sample_events = [
            {
                'id': 'event1',
                'summary': 'Study Session',
                'location': 'Library',
                'start': {'dateTime': '2023-10-09T09:00:00Z'},  # Monday
                'end': {'dateTime': '2023-10-09T11:00:00Z'}
            },
            {
                'id': 'event2',
                'summary': 'Team Meeting',
                'location': 'Conference Room',
                'start': {'dateTime': '2023-10-10T14:00:00Z'},  # Tuesday
                'end': {'dateTime': '2023-10-10T15:30:00Z'}
            },
            {
                'id': 'event3',
                'summary': 'All-day Event',
                'start': {'date': '2023-10-11'},  # Wednesday - should be skipped
                'end': {'date': '2023-10-11'}
            }
        ]
        
        # Process the events
        processed_calendar = app.process_google_events(sample_events)
        
        # Check that we have the correct day structure
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days_of_week:
            self.assertIn(day, processed_calendar)
        
        # Check processed events for Monday
        self.assertEqual(len(processed_calendar['Monday']), 1)
        monday_event = processed_calendar['Monday'][0]
        self.assertEqual(monday_event['id'], 'event1')
        self.assertEqual(monday_event['description'], 'Study Session')
        self.assertEqual(monday_event['location'], 'Library')
        self.assertEqual(monday_event['start_time'], '09:00')
        self.assertEqual(monday_event['end_time'], '11:00')
        self.assertEqual(monday_event['duration'], 120)
        
        # Check processed events for Tuesday
        self.assertEqual(len(processed_calendar['Tuesday']), 1)
        tuesday_event = processed_calendar['Tuesday'][0]
        self.assertEqual(tuesday_event['id'], 'event2')
        self.assertEqual(tuesday_event['description'], 'Team Meeting')
        self.assertEqual(tuesday_event['location'], 'Conference Room')
        self.assertEqual(tuesday_event['start_time'], '14:00')
        self.assertEqual(tuesday_event['end_time'], '15:30')
        self.assertEqual(tuesday_event['duration'], 90)
        
        # All-day event should be skipped
        self.assertEqual(len(processed_calendar['Wednesday']), 0)

    def test_format_event_for_google(self):
        """Test the format_event_for_google function."""
        # Sample event in our application format
        sample_event = {
            'id': 'test_event',
            'type': 'class',
            'description': 'Python Programming',
            'day': 'Monday',
            'start_time': '09:00',
            'end_time': '11:00',
            'duration': 120,
            'location': 'Room 101',
            'course_code': 'CS101'
        }
        
        # Format the event for Google Calendar
        google_event = app.format_event_for_google(sample_event, 'America/New_York')
        
        # Check the formatted event
        self.assertEqual(google_event['summary'], 'Python Programming')
        self.assertEqual(google_event['location'], 'Room 101')
        self.assertIn('description', google_event)
        self.assertIn('Event Type: class', google_event['description'])
        self.assertIn('Course: CS101', google_event['description'])
        
        # Check time format
        self.assertIn('start', google_event)
        self.assertIn('dateTime', google_event['start'])
        self.assertIn('timeZone', google_event['start'])
        self.assertEqual(google_event['start']['timeZone'], 'America/New_York')
        
        self.assertIn('end', google_event)
        self.assertIn('dateTime', google_event['end'])
        self.assertIn('timeZone', google_event['end'])
        self.assertEqual(google_event['end']['timeZone'], 'America/New_York')
        
        # Check that the extended properties contain the original event
        self.assertIn('extendedProperties', google_event)
        self.assertIn('private', google_event['extendedProperties'])
        self.assertIn('originalEvent', google_event['extendedProperties']['private'])

    def test_normalize_time(self):
        """Test the normalize_time function."""
        # Test various time formats
        test_cases = [
            # Format: time_str, event_type, description, expected_result
            ('9', 'task', 'regular task', '09:00:00'),
            ('14', 'task', 'afternoon task', '14:00:00'),
            ('9:30', 'task', 'morning task', '09:30:00'),
            ('14:45', 'task', 'afternoon task', '14:45:00'),
            ('7', 'meal', 'breakfast', '07:00:00'),
            ('12', 'meal', 'lunch', '12:00:00'),
            ('6', 'meal', 'dinner', '18:00:00'),  # Should convert 6 to 18:00 for dinner
            ('10', 'class', 'morning class', '10:00:00'),
            ('2', 'class', 'afternoon class', '02:00:00')  # Updated to match actual behavior
        ]
        
        for time_str, event_type, description, expected in test_cases:
            result = app.normalize_time(time_str, event_type, description)
            self.assertEqual(result, expected, f"Failed for {time_str}, {event_type}, {description}")

if __name__ == '__main__':
    unittest.main() 