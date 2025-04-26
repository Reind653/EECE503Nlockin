import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging

# Add parent directory to path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app

class TestIEP4App(unittest.TestCase):
    """Unit tests for IEP4 Schedule Chat Interface."""

    def setUp(self):
        """Set up test client and resources."""
        app.app.testing = True
        self.client = app.app.test_client()
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
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
        """Clean up resources after tests."""
        # Re-enable logging
        logging.disable(logging.NOTSET)

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_health_endpoint_successful(self, mock_call_anthropic_api):
        """Test the health check endpoint with successful API response."""
        # Configure the mock
        mock_call_anthropic_api.return_value = ({"content": "Test response"}, 200)
        
        # Make request to the health endpoint
        response = self.client.get('/health')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'healthy')
        self.assertEqual(response_data['model'], app.LLM_MODEL)
        
        # Verify the mock was called correctly
        mock_call_anthropic_api.assert_called_once()
        args, kwargs = mock_call_anthropic_api.call_args
        self.assertEqual(kwargs['prompt'], 'Hello')
        self.assertEqual(kwargs['max_tokens'], 10)

    @patch.object(app, 'ANTHROPIC_API_KEY', None)
    def test_health_endpoint_no_api_key(self):
        """Test the health check endpoint with no API key configured."""
        # Make request to the health endpoint
        response = self.client.get('/health')
        
        # Check response
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'unhealthy')
        self.assertEqual(response_data['error'], 'ANTHROPIC_API_KEY not set')

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_health_endpoint_api_error(self, mock_call_anthropic_api):
        """Test the health check endpoint with API error."""
        # Configure the mock
        mock_call_anthropic_api.return_value = ({"error": "API error"}, 500)
        
        # Make request to the health endpoint
        response = self.client.get('/health')
        
        # Check response
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'unhealthy')
        self.assertEqual(response_data['error'], 'API error')

    def test_chat_endpoint_no_message(self):
        """Test the chat endpoint with no message provided."""
        # Make request to the chat endpoint with no message
        response = self.client.post('/chat', 
                                   json={"schedule": self.sample_schedule},
                                   content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['error'], 'No message provided')

    def test_chat_endpoint_no_schedule(self):
        """Test the chat endpoint with no schedule provided."""
        # Make request to the chat endpoint with no schedule
        response = self.client.post('/chat', 
                                   json={"message": "Add a study session on Wednesday"},
                                   content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['error'], 'No schedule provided')

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_chat_endpoint_successful(self, mock_call_anthropic_api):
        """Test the chat endpoint with successful API response."""
        # Configure the mock
        mock_response = {
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
        mock_call_anthropic_api.return_value = (mock_response, 200)
        
        # Make request to the chat endpoint
        request_data = {
            "message": "Add a study session on Wednesday morning",
            "schedule": self.sample_schedule,
            "chat_history": self.chat_history
        }
        
        response = self.client.post('/chat', 
                                   json=request_data,
                                   content_type='application/json')
        
        # Check response status code
        self.assertEqual(response.status_code, 200)
        
        # Check response data
        response_data = json.loads(response.data)
        self.assertIn('response', response_data)
        self.assertIn('schedule', response_data)
        self.assertIn('generated_calendar', response_data)
        
        # Verify generated calendar has the new study session on Wednesday
        self.assertEqual(len(response_data['generated_calendar']['Wednesday']), 1)
        wednesday_event = response_data['generated_calendar']['Wednesday'][0]
        self.assertEqual(wednesday_event['type'], 'generated')
        self.assertEqual(wednesday_event['description'], 'Study Session')
        
        # Verify that the mock was called with the correct prompt
        mock_call_anthropic_api.assert_called_once()
        args, kwargs = mock_call_anthropic_api.call_args
        self.assertIn("Add a study session on Wednesday morning", kwargs['prompt'])

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_chat_endpoint_api_error(self, mock_call_anthropic_api):
        """Test the chat endpoint with API error."""
        # Configure the mock
        mock_call_anthropic_api.return_value = ({"error": "API error"}, 500)
        
        # Make request to the chat endpoint
        request_data = {
            "message": "Add a study session on Wednesday morning",
            "schedule": self.sample_schedule,
            "chat_history": self.chat_history
        }
        
        response = self.client.post('/chat', 
                                   json=request_data,
                                   content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['error'], 'API error')
        self.assertEqual(response_data['schedule'], self.sample_schedule)

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_chat_endpoint_json_parse_error(self, mock_call_anthropic_api):
        """Test the chat endpoint with JSON parse error in the response."""
        # Configure the mock with invalid JSON response
        mock_response = {
            "content": [
                {
                    "text": "This is not valid JSON"
                }
            ]
        }
        mock_call_anthropic_api.return_value = (mock_response, 200)
        
        # Make request to the chat endpoint
        request_data = {
            "message": "Add a study session on Wednesday morning",
            "schedule": self.sample_schedule,
            "chat_history": self.chat_history
        }
        
        response = self.client.post('/chat', 
                                   json=request_data,
                                   content_type='application/json')
        
        # Check response - should still return 200 but with error message
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['schedule'], self.sample_schedule)
        self.assertIn('response', response_data)
        self.assertIn('I processed your request but encountered an issue', response_data['response'])

    def test_update_prompt_endpoint_no_original_prompt(self):
        """Test the update-prompt endpoint with no original prompt provided."""
        # Make request to the update-prompt endpoint with no original prompt
        response = self.client.post('/update-prompt', 
                                   json={"chat_history": self.chat_history},
                                   content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['error'], 'No original prompt provided')

    def test_update_prompt_endpoint_empty_chat_history(self):
        """Test the update-prompt endpoint with empty chat history."""
        original_prompt = "Please optimize my schedule with more free time."
        
        # Make request to the update-prompt endpoint with empty chat history
        response = self.client.post('/update-prompt', 
                                   json={
                                       "original_prompt": original_prompt,
                                       "chat_history": []
                                   },
                                   content_type='application/json')
        
        # Check response - should return original prompt unchanged
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['custom_prompt'], original_prompt)

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_update_prompt_endpoint_successful(self, mock_call_anthropic_api):
        """Test the update-prompt endpoint with successful API response."""
        original_prompt = "Please optimize my schedule with more free time."
        updated_prompt = "Please optimize my schedule with more free time and study sessions in the morning."
        
        # Configure the mock
        mock_response = {
            "content": [
                {
                    "text": updated_prompt
                }
            ]
        }
        mock_call_anthropic_api.return_value = (mock_response, 200)
        
        # Make request to the update-prompt endpoint
        response = self.client.post('/update-prompt', 
                                   json={
                                       "original_prompt": original_prompt,
                                       "chat_history": self.chat_history
                                   },
                                   content_type='application/json')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['custom_prompt'], updated_prompt)
        
        # Verify the mock was called
        mock_call_anthropic_api.assert_called_once()
        # Not checking exact prompt contents as it varies based on implementation

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_update_prompt_endpoint_with_code_block(self, mock_call_anthropic_api):
        """Test the update-prompt endpoint with response in code block."""
        original_prompt = "Please optimize my schedule with more free time."
        updated_prompt = "Please optimize my schedule with more free time and study sessions in the morning."
        
        # Configure the mock with response in code blocks
        mock_response = {
            "content": [
                {
                    "text": f"```\n{updated_prompt}\n```"
                }
            ]
        }
        mock_call_anthropic_api.return_value = (mock_response, 200)
        
        # Make request to the update-prompt endpoint
        response = self.client.post('/update-prompt', 
                                   json={
                                       "original_prompt": original_prompt,
                                       "chat_history": self.chat_history
                                   },
                                   content_type='application/json')
        
        # Check response - should extract from code block
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['custom_prompt'], updated_prompt)

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.call_anthropic_api')
    def test_update_prompt_endpoint_api_error(self, mock_call_anthropic_api):
        """Test the update-prompt endpoint with API error."""
        original_prompt = "Please optimize my schedule with more free time."
        
        # Configure the mock
        mock_call_anthropic_api.return_value = ({"error": "API error"}, 500)
        
        # Make request to the update-prompt endpoint
        response = self.client.post('/update-prompt', 
                                   json={
                                       "original_prompt": original_prompt,
                                       "chat_history": self.chat_history
                                   },
                                   content_type='application/json')
        
        # Check response - should return error but include original prompt
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['error'], 'API error')
        self.assertEqual(response_data['custom_prompt'], original_prompt)

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('requests.post')
    def test_call_anthropic_api_function(self, mock_post):
        """Test the call_anthropic_api function directly."""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_012345",
            "content": [{"type": "text", "text": "This is a test response"}]
        }
        mock_post.return_value = mock_response
        
        # Call the function
        result, status_code = app.call_anthropic_api(
            prompt="Test prompt",
            model="claude-3-7-sonnet-20250219",
            temperature=0.5,
            max_tokens=100
        )
        
        # Check result
        self.assertEqual(status_code, 200)
        self.assertEqual(result["content"][0]["text"], "This is a test response")
        
        # Verify the mock was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.anthropic.com/v1/messages")
        
        # Check headers
        headers = kwargs['headers']
        self.assertEqual(headers["x-api-key"], "mock_api_key")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        
        # Check payload
        payload = kwargs['json']
        self.assertEqual(payload["model"], "claude-3-7-sonnet-20250219")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["messages"][0]["content"], "Test prompt")
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["max_tokens"], 100)
        
        # Check timeout
        self.assertEqual(kwargs['timeout'], 300)

    @patch.object(app, 'ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('requests.post')
    def test_call_anthropic_api_error_handling(self, mock_post):
        """Test error handling in the call_anthropic_api function."""
        # Configure the mock to raise an exception
        mock_post.side_effect = Exception("Connection error")
        
        # Call the function
        result, status_code = app.call_anthropic_api(
            prompt="Test prompt"
        )
        
        # Check result
        self.assertEqual(status_code, 500)
        self.assertEqual(result["error"], "Connection error")

    @patch.object(app, 'ANTHROPIC_API_KEY', None)
    def test_call_anthropic_api_no_api_key(self):
        """Test call_anthropic_api function with no API key configured."""
        # Call the function
        result, status_code = app.call_anthropic_api(
            prompt="Test prompt"
        )
        
        # Check result
        self.assertEqual(status_code, 500)
        self.assertEqual(result["error"], "ANTHROPIC_API_KEY environment variable not set")

if __name__ == '__main__':
    unittest.main() 