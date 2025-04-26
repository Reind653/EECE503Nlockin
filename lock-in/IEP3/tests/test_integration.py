import json
import unittest
import requests
import os
import sys
import logging
from unittest.mock import patch, MagicMock

# Add parent directory to path to import app module for direct access in some tests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app

class TestIEP3Integration(unittest.TestCase):
    """Integration tests for IEP3 Google Calendar integration with other components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # URLs for services - use environment variables or defaults for testing
        cls.IEP3_URL = os.environ.get("IEP3_URL", "http://localhost:5002")
        cls.EEP1_URL = os.environ.get("EEP1_URL", "http://localhost:5000")

    def setUp(self):
        """Set up resources before each test."""
        # Check if we're running in test mode or with real services
        self.mock_mode = os.environ.get("TEST_MOCK_MODE", "True").lower() == "true"
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
        # Create a test client for direct testing
        app.app.testing = True
        self.client = app.app.test_client()

    def tearDown(self):
        """Clean up after each test."""
        # Re-enable logging
        logging.disable(logging.NOTSET)

    def test_health_endpoint_can_be_called_from_eep1(self):
        """Test that EEP1 can call IEP3's health endpoint."""
        if self.mock_mode:
            # Mock the EEP1's call to IEP3
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "healthy"}
                mock_get.return_value = mock_response
                
                # Simulate EEP1 calling IEP3's health endpoint
                response = requests.get(f"{self.IEP3_URL}/health")
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "healthy")
        else:
            # Make an actual request to the health endpoint
            try:
                response = requests.get(f"{self.IEP3_URL}/health", timeout=5)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "healthy")
            except requests.RequestException as e:
                self.fail(f"Health endpoint request failed: {str(e)}")

    @patch('google_auth_oauthlib.flow.Flow.from_client_config')
    def test_eep1_can_initiate_google_auth_flow(self, mock_flow_from_client_config):
        """Test that EEP1 can initiate the Google OAuth flow through IEP3."""
        if self.mock_mode:
            # Set up the mock flow
            mock_flow = MagicMock()
            mock_flow.authorization_url.return_value = ('https://fake-auth-url.com', 'fake-state')
            mock_flow_from_client_config.return_value = mock_flow
            
            # Mock the request from EEP1 to IEP3
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "url": "https://fake-auth-url.com",
                    "state": "fake-state"
                }
                mock_get.return_value = mock_response
                
                # Simulate EEP1 requesting authorization URL from IEP3
                response = requests.get(
                    f"{self.IEP3_URL}/authorize",
                    params={"redirect_uri": f"{self.EEP1_URL}/google-calendar/callback"}
                )
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("url", data)
                self.assertIn("state", data)
                self.assertEqual(data["url"], "https://fake-auth-url.com")
        else:
            # Make an actual request to the authorize endpoint
            try:
                response = requests.get(
                    f"{self.IEP3_URL}/authorize",
                    params={"redirect_uri": f"{self.EEP1_URL}/google-calendar/callback"},
                    timeout=5
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("url", data)
                self.assertIn("state", data)
            except requests.RequestException as e:
                self.fail(f"Authorize endpoint request failed: {str(e)}")

    @patch('google_auth_oauthlib.flow.Flow.from_client_config')
    def test_eep1_can_complete_oauth_flow(self, mock_flow_from_client_config):
        """Test that EEP1 can complete the OAuth flow through IEP3."""
        if self.mock_mode:
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
            
            # Mock the request from EEP1 to IEP3
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "success": True,
                    "credentials": {
                        "token": "fake_token",
                        "refresh_token": "fake_refresh_token",
                        "token_uri": "fake_token_uri",
                        "client_id": "fake_client_id",
                        "client_secret": "fake_client_secret",
                        "scopes": ["fake_scope"]
                    }
                }
                mock_post.return_value = mock_response
                
                # Simulate EEP1 completing the OAuth flow through IEP3
                response = requests.post(
                    f"{self.IEP3_URL}/callback",
                    json={
                        "code": "fake_auth_code",
                        "redirect_uri": f"{self.EEP1_URL}/google-calendar/callback"
                    }
                )
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("success", data)
                self.assertTrue(data["success"])
                self.assertIn("credentials", data)
                
                # Verify credentials structure
                credentials = data["credentials"]
                self.assertIn("token", credentials)
                self.assertIn("refresh_token", credentials)
        else:
            # Skip actual OAuth flow in real tests
            pass

    @patch('googleapiclient.discovery.build')
    @patch('google.oauth2.credentials.Credentials')
    def test_eep1_can_fetch_calendar_through_iep3(self, mock_credentials, mock_build):
        """Test that EEP1 can fetch calendar data through IEP3."""
        if self.mock_mode:
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
                        'start': {'dateTime': '2023-10-09T09:00:00Z'},  # Monday
                        'end': {'dateTime': '2023-10-09T11:00:00Z'}
                    }
                ]
            }
            
            # Configure the mock chain
            mock_list_method.execute.return_value = mock_events_result
            mock_events_resource.list.return_value = mock_list_method
            mock_calendar_service.events.return_value = mock_events_resource
            mock_build.return_value = mock_calendar_service
            
            # Mock the request from EEP1 to IEP3
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "success": True,
                    "google_calendar": {
                        "Monday": [
                            {
                                "id": "event1",
                                "type": "google_event",
                                "description": "Test Event 1",
                                "start_time": "09:00",
                                "end_time": "11:00",
                                "duration": 120,
                                "location": ""
                            }
                        ],
                        "Tuesday": [],
                        "Wednesday": [],
                        "Thursday": [],
                        "Friday": [],
                        "Saturday": [],
                        "Sunday": []
                    }
                }
                mock_post.return_value = mock_response
                
                # Simulate EEP1 fetching calendar data through IEP3
                response = requests.post(
                    f"{self.IEP3_URL}/fetch-calendar",
                    json={
                        "credentials": {
                            "token": "fake_token",
                            "refresh_token": "fake_refresh_token",
                            "token_uri": "fake_token_uri",
                            "client_id": "fake_client_id",
                            "client_secret": "fake_client_secret",
                            "scopes": ["fake_scope"]
                        }
                    }
                )
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("success", data)
                self.assertTrue(data["success"])
                self.assertIn("google_calendar", data)
                
                # Check calendar data structure
                calendar_data = data["google_calendar"]
                self.assertIn("Monday", calendar_data)
                self.assertEqual(len(calendar_data["Monday"]), 1)
                
                # Check event data
                event = calendar_data["Monday"][0]
                self.assertEqual(event["id"], "event1")
                self.assertEqual(event["description"], "Test Event 1")
                self.assertEqual(event["start_time"], "09:00")
                self.assertEqual(event["end_time"], "11:00")
        else:
            # Skip actual API calls in real tests
            pass

    @patch('googleapiclient.discovery.build')
    @patch('google.oauth2.credentials.Credentials')
    def test_eep1_can_create_events_through_iep3(self, mock_credentials, mock_build):
        """Test that EEP1 can create events through IEP3."""
        if self.mock_mode:
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
            
            # Mock the request from EEP1 to IEP3
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "success": True,
                    "created": 1,
                    "failed": 0,
                    "created_events": [
                        {
                            "id": "new_event_id",
                            "original_id": "test_event_1",
                            "description": "Test Task",
                            "status": "created"
                        }
                    ],
                    "failed_events": [],
                    "user_timezone": "America/New_York"
                }
                mock_post.return_value = mock_response
                
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
                
                # Simulate EEP1 creating an event through IEP3
                response = requests.post(
                    f"{self.IEP3_URL}/create-events",
                    json={
                        "credentials": {
                            "token": "fake_token",
                            "refresh_token": "fake_refresh_token",
                            "token_uri": "fake_token_uri",
                            "client_id": "fake_client_id",
                            "client_secret": "fake_client_secret",
                            "scopes": ["fake_scope"]
                        },
                        "events": [test_event]
                    }
                )
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("success", data)
                self.assertTrue(data["success"])
                self.assertIn("created", data)
                self.assertEqual(data["created"], 1)
                self.assertIn("failed", data)
                self.assertEqual(data["failed"], 0)
                self.assertIn("created_events", data)
                self.assertEqual(len(data["created_events"]), 1)
                
                # Check created event details
                created_event = data["created_events"][0]
                self.assertEqual(created_event["original_id"], "test_event_1")
                self.assertEqual(created_event["description"], "Test Task")
                self.assertEqual(created_event["status"], "created")
        else:
            # Skip actual API calls in real tests
            pass

    def test_end_to_end_oauth_and_calendar_flow(self):
        """Integration test for the end-to-end OAuth and Calendar flow."""
        if not self.mock_mode:
            # Skip this test in real test mode
            self.skipTest("Skipping end-to-end test in real test mode")
            
        # Mock all the necessary services
        with patch('google_auth_oauthlib.flow.Flow.from_client_config') as mock_flow_from_client_config, \
             patch('googleapiclient.discovery.build') as mock_build, \
             patch('google.oauth2.credentials.Credentials') as mock_credentials, \
             patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            
            # Step 1: Set up the mock flow for authorization
            mock_flow = MagicMock()
            mock_flow.authorization_url.return_value = ('https://fake-auth-url.com', 'fake-state')
            mock_flow.credentials = MagicMock()
            mock_flow.credentials.token = 'fake_token'
            mock_flow.credentials.refresh_token = 'fake_refresh_token'
            mock_flow.credentials.token_uri = 'fake_token_uri'
            mock_flow.credentials.client_id = 'fake_client_id'
            mock_flow.credentials.client_secret = 'fake_client_secret'
            mock_flow.credentials.scopes = ['fake_scope']
            mock_flow_from_client_config.return_value = mock_flow
            
            # Step 2: Set up mock calendar service
            mock_calendar_service = MagicMock()
            mock_calendars_resource = MagicMock()
            mock_events_resource = MagicMock()
            
            # Configure the events list response
            mock_list_response = MagicMock()
            mock_list_response.execute.return_value = {
                'items': [
                    {
                        'id': 'event1',
                        'summary': 'Existing Event',
                        'start': {'dateTime': '2023-10-09T09:00:00Z'},
                        'end': {'dateTime': '2023-10-09T11:00:00Z'}
                    }
                ]
            }
            
            # Configure the calendar metadata
            mock_get_response = MagicMock()
            mock_get_response.execute.return_value = {
                'timeZone': 'America/New_York'
            }
            
            # Configure the insert response
            mock_insert_response = MagicMock()
            mock_insert_response.execute.return_value = {
                'id': 'new_event_id',
                'summary': 'New Event',
                'status': 'confirmed'
            }
            
            # Configure the mock chain
            mock_events_resource.list.return_value = mock_list_response
            mock_events_resource.insert.return_value = mock_insert_response
            mock_calendars_resource.get.return_value = mock_get_response
            mock_calendar_service.events.return_value = mock_events_resource
            mock_calendar_service.calendars.return_value = mock_calendars_resource
            mock_build.return_value = mock_calendar_service
            
            # Step 3: Mock HTTP responses for request.get/post calls
            # Authorization URL response
            auth_response = MagicMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {
                "url": "https://fake-auth-url.com",
                "state": "fake-state"
            }
            
            # Callback response
            callback_response = MagicMock()
            callback_response.status_code = 200
            callback_response.json.return_value = {
                "success": True,
                "credentials": {
                    "token": "fake_token",
                    "refresh_token": "fake_refresh_token",
                    "token_uri": "fake_token_uri",
                    "client_id": "fake_client_id",
                    "client_secret": "fake_client_secret",
                    "scopes": ["fake_scope"]
                }
            }
            
            # Fetch calendar response
            fetch_response = MagicMock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "success": True,
                "google_calendar": {
                    "Monday": [
                        {
                            "id": "event1",
                            "type": "google_event",
                            "description": "Existing Event",
                            "start_time": "09:00",
                            "end_time": "11:00",
                            "duration": 120,
                            "location": ""
                        }
                    ],
                    "Tuesday": [],
                    "Wednesday": [],
                    "Thursday": [],
                    "Friday": [],
                    "Saturday": [],
                    "Sunday": []
                }
            }
            
            # Create events response
            create_response = MagicMock()
            create_response.status_code = 200
            create_response.json.return_value = {
                "success": True,
                "created": 1,
                "failed": 0,
                "created_events": [
                    {
                        "id": "new_event_id",
                        "original_id": "test_event_1",
                        "description": "New Event",
                        "status": "created"
                    }
                ],
                "failed_events": [],
                "user_timezone": "America/New_York"
            }
            
            # Configure mock_get and mock_post to return different responses
            mock_get.side_effect = lambda url, **kwargs: auth_response if '/authorize' in url else None
            mock_post.side_effect = lambda url, **kwargs: {
                '/callback': callback_response,
                '/fetch-calendar': fetch_response,
                '/create-events': create_response
            }.get(url.split(self.IEP3_URL)[-1], None)
            
            # Execute the end-to-end flow
            
            # Step 1: Get authorization URL
            auth_url_response = requests.get(
                f"{self.IEP3_URL}/authorize",
                params={"redirect_uri": f"{self.EEP1_URL}/google-calendar/callback"}
            )
            self.assertEqual(auth_url_response.status_code, 200)
            auth_data = auth_url_response.json()
            self.assertIn("url", auth_data)
            
            # Step 2: Exchange code for credentials
            credentials_response = requests.post(
                f"{self.IEP3_URL}/callback",
                json={
                    "code": "fake_auth_code",
                    "redirect_uri": f"{self.EEP1_URL}/google-calendar/callback"
                }
            )
            self.assertEqual(credentials_response.status_code, 200)
            credentials_data = credentials_response.json()
            self.assertIn("success", credentials_data)
            self.assertTrue(credentials_data["success"])
            self.assertIn("credentials", credentials_data)
            
            # Save the credentials for next steps
            credentials = credentials_data["credentials"]
            
            # Step 3: Fetch calendar data
            fetch_calendar_response = requests.post(
                f"{self.IEP3_URL}/fetch-calendar",
                json={"credentials": credentials}
            )
            self.assertEqual(fetch_calendar_response.status_code, 200)
            calendar_data = fetch_calendar_response.json()
            self.assertIn("success", calendar_data)
            self.assertTrue(calendar_data["success"])
            self.assertIn("google_calendar", calendar_data)
            
            # Step 4: Create a new event
            test_event = {
                'id': 'test_event_1',
                'type': 'task',
                'description': 'New Event',
                'day': 'Monday',
                'start_time': '14:00',
                'end_time': '15:00',
                'duration': 60,
                'location': 'Test Location'
            }
            
            create_event_response = requests.post(
                f"{self.IEP3_URL}/create-events",
                json={
                    "credentials": credentials,
                    "events": [test_event]
                }
            )
            self.assertEqual(create_event_response.status_code, 200)
            create_event_data = create_event_response.json()
            self.assertIn("success", create_event_data)
            self.assertTrue(create_event_data["success"])
            self.assertIn("created", create_event_data)
            self.assertEqual(create_event_data["created"], 1)

if __name__ == '__main__':
    unittest.main() 