import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging

# Add parent directory to path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app

class TestIEP2App(unittest.TestCase):
    """Unit tests for IEP2 Anthropic API bridge."""

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

    def test_index_endpoint(self):
        """Test the index/health check endpoint."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Check that it contains the expected fields
        self.assertIn('service', response_data)
        self.assertIn('status', response_data)
        self.assertIn('version', response_data)
        self.assertIn('default_model', response_data)
        
        # Verify the values
        self.assertEqual(response_data['service'], 'IEP2 - Anthropic API Bridge')
        self.assertEqual(response_data['status'], 'active')

    def test_generate_endpoint_without_prompt(self):
        """Test the generate endpoint without providing a prompt."""
        response = self.client.post('/api/generate', 
                                   json={},  # Empty JSON without prompt
                                   content_type='application/json')
        
        # Should return a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        
        # Parse response data
        response_data = json.loads(response.data)
        
        # Verify error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'No prompt provided')

    @patch('app.ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.requests.post')
    def test_generate_endpoint_successful_call(self, mock_post):
        """Test the generate endpoint with a successful API call."""
        # Mock the response from Anthropic API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_012345",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "This is a test response from Claude."
                }
            ],
            "model": "claude-3-7-sonnet-20250219",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 15
            }
        }
        mock_post.return_value = mock_response
        
        # Test data
        test_prompt = "Generate a schedule for me"
        
        # Call API
        response = self.client.post('/api/generate', 
                                   json={'prompt': test_prompt},
                                   content_type='application/json')
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        self.assertEqual(call_args[0][0], "https://api.anthropic.com/v1/messages")
        
        # Check headers
        headers = call_args[1]['headers']
        self.assertEqual(headers["x-api-key"], "mock_api_key")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        
        # Check payload
        payload = call_args[1]['json']
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["messages"][0]["content"], test_prompt)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data["content"][0]["text"], "This is a test response from Claude.")

    @patch('app.ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.requests.post')
    def test_generate_endpoint_with_custom_parameters(self, mock_post):
        """Test the generate endpoint with custom parameters."""
        # Mock the response from Anthropic API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "custom model response"}
        mock_post.return_value = mock_response
        
        # Test data with custom parameters
        test_data = {
            'prompt': 'Custom prompt',
            'model': 'claude-3-opus-20240229',
            'temperature': 0.8,
            'max_tokens': 1000
        }
        
        # Call API
        response = self.client.post('/api/generate', 
                                   json=test_data,
                                   content_type='application/json')
        
        # Verify the API was called with the custom parameters
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload["model"], "claude-3-opus-20240229")
        self.assertEqual(payload["temperature"], 0.8)
        self.assertEqual(payload["max_tokens"], 1000)
        
        # Check response
        self.assertEqual(response.status_code, 200)

    @patch('app.ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.requests.post')
    def test_generate_endpoint_anthropic_api_error(self, mock_post):
        """Test the generate endpoint when Anthropic API returns an error."""
        # Mock an error response from Anthropic API
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_post.return_value = mock_response
        
        # Call API
        response = self.client.post('/api/generate', 
                                   json={'prompt': 'Test prompt'},
                                   content_type='application/json')
        
        # Should return the error from Anthropic
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('error', response_data)
        self.assertIn('Anthropic API returned error', response_data['error'])

    @patch('app.ANTHROPIC_API_KEY', None)
    def test_generate_endpoint_no_api_key(self):
        """Test the generate endpoint without an API key configured."""
        # Call API
        response = self.client.post('/api/generate', 
                                   json={'prompt': 'Test prompt'},
                                   content_type='application/json')
        
        # Should return an error about missing API key
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertIn('error', response_data)
        self.assertIn('ANTHROPIC_API_KEY environment variable not set', response_data['error'])

    @patch('app.ANTHROPIC_API_KEY', 'mock_api_key')
    @patch('app.requests.post')
    def test_generate_endpoint_request_exception(self, mock_post):
        """Test the generate endpoint when requests raises an exception."""
        # Mock requests.post to raise an exception
        mock_post.side_effect = Exception("Connection error")
        
        # Call API
        response = self.client.post('/api/generate', 
                                   json={'prompt': 'Test prompt'},
                                   content_type='application/json')
        
        # Should return a 500 error
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.data)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Connection error')

if __name__ == '__main__':
    unittest.main() 