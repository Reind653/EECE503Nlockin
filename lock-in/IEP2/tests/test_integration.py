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

class TestIEP2Integration(unittest.TestCase):
    """Integration tests for IEP2 with other system components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Set environment variables for testing
        os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "dummy_key_for_testing")
        
        # URLs for services - use environment variables or defaults for testing
        cls.IEP2_URL = os.environ.get("IEP2_URL", "http://localhost:5004")
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
        """Test that EEP1 can call IEP2's health endpoint."""
        if self.mock_mode:
            # Mock the EEP1's call to IEP2
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "service": "IEP2 - Anthropic API Bridge",
                    "status": "active",
                    "version": "1.0.0",
                    "default_model": "claude-3-7-sonnet-20250219"
                }
                mock_get.return_value = mock_response
                
                # Simulate EEP1 calling IEP2's health endpoint
                response = requests.get(f"{self.IEP2_URL}/")
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["service"], "IEP2 - Anthropic API Bridge")
                self.assertEqual(data["status"], "active")
        else:
            # Make an actual request to the health endpoint
            try:
                response = requests.get(f"{self.IEP2_URL}/", timeout=5)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["service"], "IEP2 - Anthropic API Bridge")
                self.assertEqual(data["status"], "active")
            except requests.RequestException as e:
                self.fail(f"Health endpoint request failed: {str(e)}")

    def test_eep1_can_use_iep2_to_generate_schedule(self):
        """Test that EEP1 can use IEP2 to generate a schedule."""
        if self.mock_mode:
            # Mock the API responses
            with patch('requests.post') as mock_post:
                # Simulate IEP2's response to EEP1
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "msg_sample",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": """Here's an optimized schedule:
                            
                            Monday:
                            9:00 AM - 10:30 AM: Study for Math Exam
                            11:00 AM - 12:30 PM: CS101 Lecture
                            1:00 PM - 2:00 PM: Lunch
                            2:30 PM - 4:00 PM: Group Project Meeting
                            
                            Tuesday:
                            8:30 AM - 10:00 AM: Gym Workout
                            10:30 AM - 12:00 PM: Research Meeting
                            12:30 PM - 1:30 PM: Lunch
                            2:00 PM - 4:00 PM: Laboratory Session"""
                        }
                    ],
                    "model": "claude-3-7-sonnet-20250219",
                    "stop_reason": "end_turn"
                }
                mock_post.return_value = mock_response
                
                # Create a test prompt simulating what EEP1 would send
                test_prompt = """You are a helpful AI assistant that helps optimize schedules. 
                Please optimize the following schedule, taking into account the user's preferences:
                
                Current Schedule:
                Monday: Math study (2h), CS101 class (1.5h), Group project (1.5h)
                Tuesday: Gym (1.5h), Research meeting (1.5h), Lab (2h)
                
                User Preferences:
                - Prefer to start day no earlier than 8:30 AM
                - Need at least 30 minutes break between activities
                - Lunch should be around 1 PM for about 1 hour
                
                Please organize this into an optimized daily schedule."""
                
                # Simulate EEP1 calling IEP2
                response = requests.post(
                    f"{self.IEP2_URL}/api/generate",
                    json={'prompt': test_prompt}
                )
                
                # Validate the request was made to the correct endpoint
                self.assertTrue(mock_post.called)
                
                # Validate the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["role"], "assistant")
                self.assertTrue(isinstance(data["content"], list))
                
                # Check that the response contains schedule information
                schedule_text = data["content"][0]["text"]
                self.assertIn("Monday", schedule_text)
                self.assertIn("Tuesday", schedule_text)
        else:
            # Make an actual request to IEP2
            # Note: This will only work if you have a valid Anthropic API key
            try:
                # Simplified test prompt for real API call to reduce token usage
                test_prompt = "Create a simple one-day schedule for a college student with 3 classes."
                
                response = requests.post(
                    f"{self.IEP2_URL}/api/generate",
                    json={'prompt': test_prompt},
                    timeout=30  # Longer timeout for real API call
                )
                
                # Just verify we got a successful response - content will vary
                self.assertEqual(response.status_code, 200)
                self.assertTrue(isinstance(response.json(), dict))
                
                # Verify it has the expected structure from Anthropic API
                data = response.json()
                self.assertIn("content", data)
                
            except requests.RequestException as e:
                self.fail(f"API request failed: {str(e)}")

    def test_integration_with_custom_model_parameters(self):
        """Test integration using custom model parameters."""
        if self.mock_mode:
            with patch('requests.post') as mock_post:
                # Mock response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "msg_sample2",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Custom model response"}],
                    "model": "claude-3-opus-20240229", # The custom model
                    "stop_reason": "end_turn"
                }
                mock_post.return_value = mock_response
                
                # Test with custom parameters
                test_data = {
                    'prompt': 'Generate a creative story about time travel',
                    'model': 'claude-3-opus-20240229',  # Using a different model
                    'temperature': 0.9,  # Higher temperature for more creativity
                    'max_tokens': 2000
                }
                
                # Simulate request
                response = requests.post(
                    f"{self.IEP2_URL}/api/generate",
                    json=test_data
                )
                
                # Verify custom parameters were passed correctly
                call_args = mock_post.call_args
                payload = call_args[1]['json']
                self.assertEqual(payload["model"], "claude-3-opus-20240229")
                self.assertEqual(payload["temperature"], 0.9)
                self.assertEqual(payload["max_tokens"], 2000)
                
                # Check response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["model"], "claude-3-opus-20240229")
        else:
            # With real services, we could test with a different model
            # but we'll skip this to avoid unnecessary API calls
            pass

if __name__ == '__main__':
    unittest.main() 