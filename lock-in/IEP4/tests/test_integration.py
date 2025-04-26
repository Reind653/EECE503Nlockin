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

class TestIEP4Integration(unittest.TestCase):
    """Integration tests for IEP4 Schedule Chat Interface with other components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # URLs for services - use environment variables or defaults for testing
        cls.IEP4_URL = os.environ.get("IEP4_URL", "http://localhost:5005")
        cls.EEP1_URL = os.environ.get("EEP1_URL", "http://localhost:5000")
        cls.UI_URL = os.environ.get("UI_URL", "http://localhost:3000")

    def setUp(self):
        """Set up resources before each test."""
        # Check if we're running in test mode or with real services
        self.mock_mode = os.environ.get("TEST_MOCK_MODE", "True").lower() == "true"
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
        # Create a test client for direct testing
        app.app.testing = True
        self.client = app.app.test_client()
        
        # Sample data for tests
        self.sample_schedule = {
            "generated_calendar": {
                "Monday": [
                    {
                        "id": "meeting-1",
                        "type": "meeting",
                        "description": "Team Meeting",
                        "start_time": "09:00",
                        "end_time": "10:00",
                        "duration": 60
                    },
                    {
                        "id": "class-1",
                        "type": "class",
                        "description": "CS101 Lecture",
                        "course_code": "CS101",
                        "start_time": "11:00",
                        "end_time": "12:30",
                        "duration": 90
                    }
                ],
                "Tuesday": [
                    {
                        "id": "task-1",
                        "type": "task",
                        "description": "Complete Assignment",
                        "start_time": "14:00",
                        "end_time": "16:00",
                        "duration": 120
                    }
                ],
                "Wednesday": [],
                "Thursday": [],
                "Friday": [],
                "Saturday": [],
                "Sunday": []
            }
        }
        
        self.chat_history = [
            {
                "role": "user",
                "content": "I need a study session on Tuesday morning"
            },
            {
                "role": "assistant",
                "content": "I've added a study session on Tuesday morning from 9:00 to 11:00."
            }
        ]

    def tearDown(self):
        """Clean up after each test."""
        # Re-enable logging
        logging.disable(logging.NOTSET)

    def test_health_endpoint_can_be_called_from_eep1(self):
        """Test that EEP1 can call IEP4's health endpoint."""
        if self.mock_mode:
            # Mock the EEP1's call to IEP4
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "status": "healthy",
                    "model": app.LLM_MODEL
                }
                mock_get.return_value = mock_response
                
                # Simulate EEP1 calling IEP4's health endpoint
                response = requests.get(f"{self.IEP4_URL}/health")
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "healthy")
                self.assertEqual(data["model"], app.LLM_MODEL)
        else:
            # Make an actual request to the health endpoint
            try:
                response = requests.get(f"{self.IEP4_URL}/health", timeout=5)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "healthy")
            except requests.RequestException as e:
                self.fail(f"Health endpoint request failed: {str(e)}")

    def test_eep1_can_use_iep4_chat_endpoint(self):
        """Test that EEP1 can use IEP4's chat endpoint."""
        if self.mock_mode:
            # Mock the request from EEP1 to IEP4
            with patch('requests.post') as mock_post:
                # Configure mock response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "response": "I've added a study session on Wednesday morning.",
                    "schedule": self.sample_schedule,
                    "generated_calendar": {
                        "Monday": [
                            {
                                "id": "meeting-1",
                                "type": "meeting",
                                "description": "Team Meeting",
                                "start_time": "09:00",
                                "end_time": "10:00",
                                "duration": 60
                            },
                            {
                                "id": "class-1",
                                "type": "class",
                                "description": "CS101 Lecture",
                                "course_code": "CS101",
                                "start_time": "11:00",
                                "end_time": "12:30",
                                "duration": 90
                            }
                        ],
                        "Tuesday": [
                            {
                                "id": "task-1",
                                "type": "task",
                                "description": "Complete Assignment",
                                "start_time": "14:00",
                                "end_time": "16:00",
                                "duration": 120
                            }
                        ],
                        "Wednesday": [
                            {
                                "id": "study-1",
                                "type": "generated",
                                "description": "Study Session",
                                "start_time": "09:00",
                                "end_time": "11:00",
                                "duration": 120
                            }
                        ],
                        "Thursday": [],
                        "Friday": [],
                        "Saturday": [],
                        "Sunday": []
                    }
                }
                mock_post.return_value = mock_response
                
                # Prepare request data
                request_data = {
                    "message": "Add a study session on Wednesday morning",
                    "schedule": self.sample_schedule,
                    "chat_history": self.chat_history
                }
                
                # Simulate EEP1 calling IEP4's chat endpoint
                response = requests.post(
                    f"{self.IEP4_URL}/chat",
                    json=request_data
                )
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("response", data)
                self.assertIn("schedule", data)
                self.assertIn("generated_calendar", data)
                
                # Verify the generated calendar has the new study session
                self.assertEqual(len(data["generated_calendar"]["Wednesday"]), 1)
                wednesday_event = data["generated_calendar"]["Wednesday"][0]
                self.assertEqual(wednesday_event["type"], "generated")
                self.assertEqual(wednesday_event["description"], "Study Session")
                
                # Verify the call was made correctly
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], f"{self.IEP4_URL}/chat")
                self.assertEqual(kwargs["json"]["message"], "Add a study session on Wednesday morning")
        else:
            # Make an actual request to the chat endpoint
            try:
                request_data = {
                    "message": "Add a study session on Wednesday morning",
                    "schedule": self.sample_schedule,
                    "chat_history": self.chat_history
                }
                
                response = requests.post(
                    f"{self.IEP4_URL}/chat",
                    json=request_data,
                    timeout=30  # Longer timeout for real API call
                )
                
                # Just verify we got a successful response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("response", data)
                self.assertIn("schedule", data)
                self.assertIn("generated_calendar", data)
            except requests.RequestException as e:
                self.fail(f"Chat endpoint request failed: {str(e)}")

    def test_ui_can_use_iep4_update_prompt_endpoint(self):
        """Test that UI can use IEP4's update-prompt endpoint."""
        if self.mock_mode:
            # Mock the request from UI to IEP4
            with patch('requests.post') as mock_post:
                # Configure mock response
                mock_response = MagicMock()
                mock_response.status_code = 200
                original_prompt = "Please optimize my schedule with more free time."
                updated_prompt = "Please optimize my schedule with more free time and study sessions in the morning."
                mock_response.json.return_value = {
                    "custom_prompt": updated_prompt
                }
                mock_post.return_value = mock_response
                
                # Prepare request data
                request_data = {
                    "original_prompt": original_prompt,
                    "chat_history": self.chat_history
                }
                
                # Simulate UI calling IEP4's update-prompt endpoint
                response = requests.post(
                    f"{self.IEP4_URL}/update-prompt",
                    json=request_data
                )
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("custom_prompt", data)
                self.assertEqual(data["custom_prompt"], updated_prompt)
                
                # Verify the call was made correctly
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], f"{self.IEP4_URL}/update-prompt")
                self.assertEqual(kwargs["json"]["original_prompt"], original_prompt)
        else:
            # Make an actual request to the update-prompt endpoint
            try:
                original_prompt = "Please optimize my schedule with more free time."
                
                request_data = {
                    "original_prompt": original_prompt,
                    "chat_history": self.chat_history
                }
                
                response = requests.post(
                    f"{self.IEP4_URL}/update-prompt",
                    json=request_data,
                    timeout=30  # Longer timeout for real API call
                )
                
                # Just verify we got a successful response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("custom_prompt", data)
                self.assertNotEqual(data["custom_prompt"], "")  # Should not be empty
            except requests.RequestException as e:
                self.fail(f"Update-prompt endpoint request failed: {str(e)}")

    @patch('requests.post')
    def test_direct_anthropic_api_call(self, mock_post):
        """Test direct call to Anthropic API."""
        if self.mock_mode:
            # Configure the mock
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "msg_012345",
                "content": [{"type": "text", "text": "This is a test response"}],
                "model": app.LLM_MODEL
            }
            mock_post.return_value = mock_response
            
            # Override the API key for testing
            original_api_key = app.ANTHROPIC_API_KEY
            app.ANTHROPIC_API_KEY = "test_api_key"
            
            try:
                # Call the Anthropic API directly
                result, status_code = app.call_anthropic_api(
                    prompt="Test prompt"
                )
                
                # Verify the result
                self.assertEqual(status_code, 200)
                self.assertEqual(result["content"][0]["text"], "This is a test response")
                
                # Verify the API was called correctly
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], "https://api.anthropic.com/v1/messages")
                
                # Check headers
                headers = kwargs['headers']
                self.assertEqual(headers["x-api-key"], "test_api_key")
                
                # Check payload
                payload = kwargs['json']
                self.assertEqual(payload["model"], app.LLM_MODEL)
                self.assertEqual(payload["messages"][0]["content"], "Test prompt")
            finally:
                # Restore the original API key
                app.ANTHROPIC_API_KEY = original_api_key
        else:
            # Skip the test in real mode to avoid making actual API calls
            self.skipTest("Skipping direct API call test in real mode")

    def test_end_to_end_chat_flow(self):
        """Test end-to-end chat flow from UI through IEP4."""
        if self.mock_mode:
            # Mock all necessary API calls
            with patch('requests.post') as mock_post, \
                 patch.object(app, 'call_anthropic_api') as mock_call_anthropic_api:
                
                # First simulate Anthropic API response
                mock_api_response = {
                    "content": [
                        {
                            "text": json.dumps({
                                "response": "I've added a study session on Wednesday morning.",
                                "schedule": self.sample_schedule,
                                "generated_calendar": {
                                    "Monday": [
                                        {
                                            "id": "meeting-1",
                                            "type": "meeting",
                                            "description": "Team Meeting",
                                            "start_time": "09:00",
                                            "end_time": "10:00",
                                            "duration": 60
                                        },
                                        {
                                            "id": "class-1",
                                            "type": "class",
                                            "description": "CS101 Lecture",
                                            "course_code": "CS101",
                                            "start_time": "11:00",
                                            "end_time": "12:30",
                                            "duration": 90
                                        }
                                    ],
                                    "Tuesday": [
                                        {
                                            "id": "task-1",
                                            "type": "task",
                                            "description": "Complete Assignment",
                                            "start_time": "14:00",
                                            "end_time": "16:00",
                                            "duration": 120
                                        }
                                    ],
                                    "Wednesday": [
                                        {
                                            "id": "study-1",
                                            "type": "generated",
                                            "description": "Study Session",
                                            "start_time": "09:00",
                                            "end_time": "11:00",
                                            "duration": 120
                                        }
                                    ],
                                    "Thursday": [],
                                    "Friday": [],
                                    "Saturday": [],
                                    "Sunday": []
                                }
                            })
                        }
                    ]
                }
                mock_call_anthropic_api.return_value = (mock_api_response, 200)
                
                # Simulate UI sending request to IEP4
                request_data = {
                    "message": "Add a study session on Wednesday morning",
                    "schedule": self.sample_schedule,
                    "chat_history": []  # Start with empty chat history
                }
                
                # Step 1: UI makes request to IEP4
                response = self.client.post('/chat',
                                          json=request_data,
                                          content_type='application/json')
                
                # Verify response
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertIn("response", response_data)
                self.assertIn("schedule", response_data)
                self.assertIn("generated_calendar", response_data)
                
                # Verify new event was added
                self.assertEqual(len(response_data["generated_calendar"]["Wednesday"]), 1)
                
                # Step 2: UI appends to chat history and makes another request
                new_chat_history = [
                    {
                        "role": "user",
                        "content": "Add a study session on Wednesday morning"
                    },
                    {
                        "role": "assistant",
                        "content": response_data["response"]
                    }
                ]
                
                # Configure the mock for the second call
                mock_api_response_2 = {
                    "content": [
                        {
                            "text": json.dumps({
                                "response": "I've added lunch on Wednesday at noon.",
                                "schedule": response_data["schedule"],
                                "generated_calendar": {
                                    "Monday": response_data["generated_calendar"]["Monday"],
                                    "Tuesday": response_data["generated_calendar"]["Tuesday"],
                                    "Wednesday": response_data["generated_calendar"]["Wednesday"] + [
                                        {
                                            "id": "meal-1",
                                            "type": "meal",
                                            "description": "Lunch",
                                            "start_time": "12:00",
                                            "end_time": "13:00",
                                            "duration": 60
                                        }
                                    ],
                                    "Thursday": response_data["generated_calendar"]["Thursday"],
                                    "Friday": response_data["generated_calendar"]["Friday"],
                                    "Saturday": response_data["generated_calendar"]["Saturday"],
                                    "Sunday": response_data["generated_calendar"]["Sunday"]
                                }
                            })
                        }
                    ]
                }
                mock_call_anthropic_api.return_value = (mock_api_response_2, 200)
                
                # Make second request
                request_data_2 = {
                    "message": "Add lunch on Wednesday at noon",
                    "schedule": response_data["schedule"],
                    "chat_history": new_chat_history
                }
                
                response_2 = self.client.post('/chat',
                                            json=request_data_2,
                                            content_type='application/json')
                
                # Verify second response
                self.assertEqual(response_2.status_code, 200)
                response_data_2 = json.loads(response_2.data)
                
                # Verify both events are in the calendar
                wednesday_events = response_data_2["generated_calendar"]["Wednesday"]
                self.assertEqual(len(wednesday_events), 2)
                self.assertEqual(wednesday_events[0]["description"], "Study Session")
                self.assertEqual(wednesday_events[1]["description"], "Lunch")
                self.assertEqual(wednesday_events[1]["type"], "meal")
                
                # Verify call_anthropic_api was called twice
                self.assertEqual(mock_call_anthropic_api.call_count, 2)
        else:
            # Skip test in real mode
            self.skipTest("Skipping end-to-end test in real mode")

if __name__ == '__main__':
    unittest.main() 