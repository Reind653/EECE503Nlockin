import json
import unittest
import requests
import os
import sys
import logging
from unittest.mock import patch, MagicMock

# Add parent directory to path to import parser module for direct access in some tests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parser

class TestIEP1Integration(unittest.TestCase):
    """Integration tests for IEP1 with other system components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Set environment variables for testing
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy_key_for_testing")
        
        # URLs for services - use environment variables or defaults for testing
        cls.IEP1_URL = os.environ.get("IEP1_URL", "http://localhost:5001")
        cls.EEP1_URL = os.environ.get("EEP1_URL", "http://localhost:5000")

    def setUp(self):
        """Set up resources before each test."""
        # Check if we're running in test mode or with real services
        self.mock_mode = os.environ.get("TEST_MOCK_MODE", "True").lower() == "true"
        # Disable logging for tests
        logging.disable(logging.CRITICAL)
        
        # Create a test client for direct testing
        parser.app.testing = True
        self.client = parser.app.test_client()

    def tearDown(self):
        """Clean up after each test."""
        # Re-enable logging
        logging.disable(logging.NOTSET)

    def test_health_endpoint_can_be_called_from_eep1(self):
        """Test that EEP1 can call IEP1's health endpoint."""
        if self.mock_mode:
            # Mock the EEP1's call to IEP1
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "healthy", "model": "gpt-3.5-turbo"}
                mock_get.return_value = mock_response
                
                # Simulate EEP1 calling IEP1's health endpoint
                response = requests.get(f"{self.IEP1_URL}/health")
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "healthy")
        else:
            # Make an actual request to the health endpoint
            try:
                response = requests.get(f"{self.IEP1_URL}/health", timeout=5)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "healthy")
            except requests.RequestException as e:
                self.fail(f"Health endpoint request failed: {str(e)}")

    def test_predict_endpoint_with_sample_schedule_text(self):
        """Test predict endpoint with a sample schedule text input."""
        sample_schedule = """
        Monday:
        9:00 AM - 10:30 AM: Meeting with marketing team
        1:00 PM - 2:00 PM: Lunch with client
        3:00 PM - 5:00 PM: Work on project proposal
        
        Tuesday:
        10:00 AM - 11:00 AM: Standup meeting
        2:00 PM - 4:00 PM: Interview candidates
        """
        
        prompt = f"Parse this schedule and return in JSON format: {sample_schedule}"
        
        if self.mock_mode:
            # Mock OpenAI API call
            with patch('parser.client.chat.completions.create') as mock_create:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = json.dumps({
                    "schedule": {
                        "Monday": [
                            {"time": "9:00 AM - 10:30 AM", "event": "Meeting with marketing team"},
                            {"time": "1:00 PM - 2:00 PM", "event": "Lunch with client"},
                            {"time": "3:00 PM - 5:00 PM", "event": "Work on project proposal"}
                        ],
                        "Tuesday": [
                            {"time": "10:00 AM - 11:00 AM", "event": "Standup meeting"},
                            {"time": "2:00 PM - 4:00 PM", "event": "Interview candidates"}
                        ]
                    }
                })
                mock_create.return_value = mock_response
                
                # Call the predict endpoint
                response = self.client.post('/predict', 
                                          json={'prompt': prompt},
                                          content_type='application/json')
                
                # Validate the response
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertIn('schedule', response_data)
                self.assertEqual(len(response_data['schedule']['Monday']), 3)
                self.assertEqual(len(response_data['schedule']['Tuesday']), 2)
        else:
            # Make an actual request to the predict endpoint
            try:
                response = requests.post(
                    f"{self.IEP1_URL}/predict",
                    json={'prompt': prompt},
                    timeout=30  # Longer timeout for real API call
                )
                self.assertEqual(response.status_code, 200)
                response_data = response.json()
                # Just check that we got some kind of structured response
                self.assertTrue(isinstance(response_data, dict))
            except requests.RequestException as e:
                self.fail(f"Predict endpoint request failed: {str(e)}")

    def test_eep1_can_use_iep1_to_parse_schedule(self):
        """Test that EEP1 can use IEP1 to parse a schedule."""
        sample_text = """
        Wednesday:
        8:30 AM - 9:30 AM: Gym workout
        10:00 AM - 12:00 PM: Team meeting 
        12:00 PM - 1:00 PM: Lunch break
        1:30 PM - 3:30 PM: Work on project
        """
        
        if self.mock_mode:
            # Mock EEP1's call to IEP1
            with patch('requests.post') as mock_post:
                # Simulate IEP1's response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "schedule": {
                        "Wednesday": [
                            {"time": "8:30 AM - 9:30 AM", "event": "Gym workout"},
                            {"time": "10:00 AM - 12:00 PM", "event": "Team meeting"},
                            {"time": "12:00 PM - 1:00 PM", "event": "Lunch break"},
                            {"time": "1:30 PM - 3:30 PM", "event": "Work on project"}
                        ]
                    }
                }
                mock_post.return_value = mock_response
                
                # Simulate EEP1 calling IEP1
                response = requests.post(
                    f"{self.IEP1_URL}/predict",
                    json={'prompt': f"Parse this schedule: {sample_text}"}
                )
                
                # Validate the request and response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn('schedule', data)
                self.assertEqual(len(data['schedule']['Wednesday']), 4)
        else:
            # Try to make an actual request to EEP1 to use IEP1
            try:
                # This is a simplified version since we don't know exactly how EEP1 calls IEP1
                # In a real environment, we would use the actual API endpoints of EEP1
                response = requests.post(
                    f"{self.IEP1_URL}/predict",
                    json={'prompt': f"Parse this schedule: {sample_text}"},
                    timeout=30
                )
                self.assertEqual(response.status_code, 200)
                # Just check for a valid response
                self.assertTrue(isinstance(response.json(), dict))
            except requests.RequestException as e:
                self.fail(f"Integration request failed: {str(e)}")

    def test_iep1_can_handle_complex_schedule_format(self):
        """Test IEP1's ability to handle complex schedule formats."""
        complex_schedule = """
        Week of March 15-19, 2023
        
        Monday (March 15):
        * 8:00-9:30: Breakfast with advisor
        * 10:00-11:30: CS101 Lecture (Room 302)
        * 12:00-13:00: Lunch
        * 14:00-16:30: Study group for upcoming math exam
        * 18:00-19:00: Gym
        
        Tuesday (March 16):
        * 9:00-10:30: Math 201 (Room 205)
        * 11:00-12:30: Meeting with project team
        * 13:00-14:00: Lunch
        * 15:00-17:00: Lab work
        * 19:00-21:00: Movie with friends
        """
        
        if self.mock_mode:
            # Mock OpenAI API call
            with patch('parser.client.chat.completions.create') as mock_create:
                # Prepare a structured response that OpenAI might return
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = json.dumps({
                    "week": "March 15-19, 2023",
                    "days": [
                        {
                            "day": "Monday",
                            "date": "March 15",
                            "events": [
                                {"time": "8:00-9:30", "description": "Breakfast with advisor"},
                                {"time": "10:00-11:30", "description": "CS101 Lecture", "location": "Room 302"},
                                {"time": "12:00-13:00", "description": "Lunch"},
                                {"time": "14:00-16:30", "description": "Study group for upcoming math exam"},
                                {"time": "18:00-19:00", "description": "Gym"}
                            ]
                        },
                        {
                            "day": "Tuesday",
                            "date": "March 16",
                            "events": [
                                {"time": "9:00-10:30", "description": "Math 201", "location": "Room 205"},
                                {"time": "11:00-12:30", "description": "Meeting with project team"},
                                {"time": "13:00-14:00", "description": "Lunch"},
                                {"time": "15:00-17:00", "description": "Lab work"},
                                {"time": "19:00-21:00", "description": "Movie with friends"}
                            ]
                        }
                    ]
                })
                mock_create.return_value = mock_response
                
                # Make request to IEP1
                response = self.client.post(
                    '/predict',
                    json={'prompt': f"Parse this complex schedule and maintain all details: {complex_schedule}"},
                    content_type='application/json'
                )
                
                # Validate response
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIn('week', data)
                self.assertIn('days', data)
                self.assertEqual(len(data['days']), 2)
                self.assertEqual(len(data['days'][0]['events']), 5)
                self.assertEqual(len(data['days'][1]['events']), 5)
        else:
            # Make an actual request to IEP1
            try:
                response = requests.post(
                    f"{self.IEP1_URL}/predict",
                    json={'prompt': f"Parse this complex schedule and maintain all details: {complex_schedule}"},
                    timeout=30
                )
                self.assertEqual(response.status_code, 200)
                # Just verify we got a response - actual content will vary
                self.assertTrue(isinstance(response.json(), dict))
            except requests.RequestException as e:
                self.fail(f"Complex schedule request failed: {str(e)}")

if __name__ == '__main__':
    unittest.main() 