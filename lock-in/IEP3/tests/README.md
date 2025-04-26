# IEP3 Tests

This directory contains unit and integration tests for the IEP3 (Intelligent Event Processor 3) service, which provides integration with Google Calendar.

## Test Structure

- `test_app.py`: Unit tests for the Flask application and Google Calendar API functions
- `test_integration.py`: Integration tests for IEP3's interactions with other components (like EEP1)
- `run_tests.py`: Script to run the tests

## Running Tests

### Prerequisites

Make sure you have installed all the requirements:

```bash
pip install -r ../requirements.txt
pip install pytest mock
```

### Running All Tests

To run all tests:

```bash
python run_tests.py
```

### Running Specific Test Types

To run only unit tests:

```bash
python run_tests.py --test-type unit
```

To run only integration tests:

```bash
python run_tests.py --test-type integration
```

### Test Modes

By default, tests run in "mock mode", which means they use mocked external services (like the Google Calendar API) instead of making real API calls. This is ideal for CI/CD pipelines and quick testing.

To run tests with real service calls (requires actual connections to Google API):

```bash
python run_tests.py --mock-mode False
```

**Note:** When running without mock mode, you need to have:
1. Google OAuth client credentials configured in the app
2. The actual services (IEP3, EEP1) running on their respective ports

## Environment Variables

The tests use these environment variables:

- `IEP3_URL`: URL for the IEP3 service (default: http://localhost:5002)
- `EEP1_URL`: URL for the EEP1 service (default: http://localhost:5000)
- `TEST_MOCK_MODE`: Whether to run in mock mode (default: True)

## Google Calendar API Testing

The tests for the Google Calendar API functions are particularly important since they involve external service calls. These tests ensure:

1. **Authentication Flow**: Tests the OAuth 2.0 flow including generating authorization URLs and exchanging codes for tokens
2. **Calendar Data Retrieval**: Tests fetching calendar events and processing them into a structured format
3. **Event Creation**: Tests creating new events in the user's Google Calendar
4. **Time and Timezone Handling**: Tests proper formatting of dates, times, and timezones

## Continuous Integration

These tests are designed to be run in a CI/CD pipeline. In mock mode, they don't require any external services or API keys, making them suitable for automated testing environments. 