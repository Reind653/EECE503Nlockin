# IEP4 Tests

This directory contains unit and integration tests for the IEP4 (Intelligent Event Processor 4) service, which serves as a chat interface for schedule management using the Anthropic Claude API.

## Test Structure

- `test_app.py`: Unit tests for the Flask application and Anthropic API integration
- `test_integration.py`: Integration tests for IEP4's interactions with other components (like EEP1 and UI)
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

By default, tests run in "mock mode", which means they use mocked external services (like the Anthropic API) instead of making real API calls. This is ideal for CI/CD pipelines and quick testing.

To run tests with real service calls (requires actual connections to Anthropic API):

```bash
python run_tests.py --mock-mode False
```

**Note:** When running without mock mode, you need to have:
1. A valid Anthropic API key in the `ANTHROPIC_API_KEY` environment variable
2. The actual services (IEP4, EEP1, UI) running on their respective ports

## Environment Variables

The tests use these environment variables:

- `ANTHROPIC_API_KEY`: Your Anthropic API key (for non-mock tests)
- `IEP4_URL`: URL for the IEP4 service (default: http://localhost:5005)
- `EEP1_URL`: URL for the EEP1 service (default: http://localhost:5000)
- `UI_URL`: URL for the UI service (default: http://localhost:3000)
- `TEST_MOCK_MODE`: Whether to run in mock mode (default: True)
- `LLM_MODEL`: The default LLM model to use (default: claude-3-7-sonnet-20250219)

## Anthropic API Testing

The tests for the Anthropic API integration are particularly important since they involve external service calls. These tests ensure:

1. **Chat Functionality**: Tests the processing of chat messages and schedule updates
2. **Prompt Management**: Tests the updating of custom prompts based on chat history
3. **Error Handling**: Tests proper handling of API errors and response parsing
4. **JSON Processing**: Tests the complex JSON processing required for schedule management

## Continuous Integration

These tests are designed to be run in a CI/CD pipeline. In mock mode, they don't require any external services or API keys, making them suitable for automated testing environments. 