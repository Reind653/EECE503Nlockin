import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging

# Add parent directory to path to import parser module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parser

class TestIEP1Parser(unittest.TestCase):
    """Unit tests for IEP1 parser module."""

    def setUp(self):
        """Set up test client and resources."""
        parser.app.testing = True
        self.client = parser.app.test_client()
        # Disable logging for tests
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up resources after tests."""
        # Re-enable logging
        logging.disable(logging.NOTSET)

    def test_health_endpoint_with_api_key(self):
        """Test health endpoint with valid API key."""
        with patch('parser.api_key', 'test_api_key'):
            with patch('parser.client.chat.completions.create') as mock_create:
                # Mock the OpenAI API call
                mock_response = MagicMock()
                mock_create.return_value = mock_response
                
                # Call the health endpoint
                response = self.client.get('/health')
                
                # Check that the API was called correctly
                mock_create.assert_called_once()
                
                # Validate the response
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertEqual(response_data['status'], 'healthy')
                self.assertEqual(response_data['openai_status'], 'connected')

    def test_health_endpoint_without_api_key(self):
        """Test health endpoint without API key."""
        with patch('parser.api_key', None):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 500)
            response_data = json.loads(response.data)
            self.assertEqual(response_data['status'], 'unhealthy')
            self.assertIn('OPENAI_API_KEY', response_data['error'])

    def test_health_endpoint_api_error(self):
        """Test health endpoint with API error."""
        with patch('parser.api_key', 'test_api_key'):
            with patch('parser.client.chat.completions.create') as mock_create:
                # Simulate an error from the OpenAI API
                mock_create.side_effect = Exception("API connection error")
                
                # Call the health endpoint
                response = self.client.get('/health')
                
                # Check response
                self.assertEqual(response.status_code, 500)
                response_data = json.loads(response.data)
                self.assertEqual(response_data['status'], 'unhealthy')
                self.assertEqual(response_data['openai_status'], 'disconnected')
                self.assertIn('API connection error', response_data['error'])

    def test_predict_endpoint_with_valid_input(self):
        """Test predict endpoint with valid input."""
        with patch('parser.api_key', 'test_api_key'):
            with patch('parser.client.chat.completions.create') as mock_create:
                # Mock the OpenAI API response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = '{"result": "test result"}'
                mock_create.return_value = mock_response
                
                # Call the predict endpoint
                response = self.client.post('/predict', 
                                           json={'prompt': 'test prompt'},
                                           content_type='application/json')
                
                # Validate the request to OpenAI API
                mock_create.assert_called_once()
                # Check that the prompt was passed correctly
                self.assertEqual(mock_create.call_args[1]['messages'][1]['content'], 'test prompt')
                
                # Validate the response
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertEqual(response_data['result'], 'test result')

    def test_predict_endpoint_with_invalid_json_response(self):
        """Test predict endpoint with invalid JSON response from OpenAI."""
        with patch('parser.api_key', 'test_api_key'):
            with patch('parser.client.chat.completions.create') as mock_create:
                # Mock an invalid JSON response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = 'This is not valid JSON'
                mock_create.return_value = mock_response
                
                # Call the predict endpoint
                response = self.client.post('/predict', 
                                           json={'prompt': 'test prompt'},
                                           content_type='application/json')
                
                # Validate the response
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertEqual(response_data['response'], 'This is not valid JSON')
                self.assertIn('warning', response_data)

    def test_predict_endpoint_with_missing_prompt(self):
        """Test predict endpoint with missing prompt parameter."""
        response = self.client.post('/predict', 
                                   json={},  # Missing prompt parameter
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('error', response_data)
        self.assertIn('Missing prompt parameter', response_data['error'])

    def test_predict_endpoint_with_api_error(self):
        """Test predict endpoint with API error."""
        with patch('parser.api_key', 'test_api_key'):
            with patch('parser.client.chat.completions.create') as mock_create:
                # Simulate an API error
                mock_create.side_effect = Exception("API error occurred")
                
                # Call the predict endpoint
                response = self.client.post('/predict', 
                                           json={'prompt': 'test prompt'},
                                           content_type='application/json')
                
                # Validate the response
                self.assertEqual(response.status_code, 500)
                response_data = json.loads(response.data)
                self.assertIn('error', response_data)
                self.assertIn('API error', response_data['error'])

if __name__ == '__main__':
    unittest.main() 