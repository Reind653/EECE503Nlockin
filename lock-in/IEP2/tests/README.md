# IEP2 Tests

This directory contains unit and integration tests for the IEP2 (Intelligent Event Processor 2) service, which serves as a bridge to the Anthropic API.

## Test Structure

- `test_app.py`: Unit tests for the Flask application and Anthropic API bridge functionality
- `test_integration.py`: Integration tests for IEP2's interactions with other components (like EEP1)
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
2. The actual services (IEP2, EEP1) running on their respective ports

## Environment Variables

The tests use these environment variables:

- `ANTHROPIC_API_KEY`: Your Anthropic API key (for non-mock tests)
- `IEP2_URL`: URL for the IEP2 service (default: http://localhost:5004)
- `EEP1_URL`: URL for the EEP1 service (default: http://localhost:5000)
- `TEST_MOCK_MODE`: Whether to run in mock mode (default: True)
- `LLM_MODEL`: The default LLM model to use (default: claude-3-7-sonnet-20250219)

## Continuous Integration

These tests are designed to be run in a CI/CD pipeline. In mock mode, they don't require any external services or API keys, making them suitable for automated testing environments. 