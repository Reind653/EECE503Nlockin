# EEP1 Tests

This directory contains unit and integration tests for the EEP1 (External Event Processor 1) service, which serves as the primary schedule management and coordination service in the Lock-In system.

## Test Structure

The test suite consists of the following files:

- `test_app.py`: Unit tests for the EEP1 Flask application endpoints and helper functions
- `test_integration.py`: Integration tests for EEP1's interactions with other components (IEP1, IEP2, IEP3, IEP4)
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

By default, tests run in "mock mode", which means they use mocked external services instead of making real API calls. This is ideal for CI/CD pipelines and quick testing.

To run tests with real service calls (requires actual connections to services):

```bash
python run_tests.py --mock-mode False
```

**Note:** When running without mock mode, you need to have:
1. All required services (IEP1, IEP2, IEP3, IEP4) running on their respective ports
2. The services must be healthy and responding to API calls

## Environment Variables

The tests use these environment variables:

- `IEP1_URL`: URL for the IEP1 service (default: http://localhost:5001)
- `IEP2_URL`: URL for the IEP2 service (default: http://localhost:5004)
- `IEP3_URL`: URL for the IEP3 service (default: http://localhost:5003)
- `IEP4_URL`: URL for the IEP4 service (default: http://localhost:5005)
- `TEST_MOCK_MODE`: Whether to run in mock mode (default: True)

## Test Coverage

### Unit Tests

The unit tests cover:

1. **API Endpoints**:
   - `/health`: Health check endpoint
   - `/parse-schedule`: Schedule parsing endpoint
   - `/store-schedule`: Schedule storage endpoint
   - `/get-schedule`: Schedule retrieval endpoint
   - `/answer-question`: Missing information handling endpoint
   - `/chat`: Chat interaction endpoint for schedule modifications
   - `/reset-stored-schedule`: Schedule reset endpoint

2. **Helper Functions**:
   - `convert_to_24h`: Time conversion functionality
   - `validate_and_fix_times`: Time validation in schedules
   - `ensure_ids`: ID assignment to schedule items

### Integration Tests

The integration tests cover:

1. **Inter-service Communication**:
   - EEP1 ↔ IEP1: Schedule parsing
   - EEP1 ↔ IEP2: Schedule optimization
   - EEP1 ↔ IEP4: Chat interactions and prompt updates

2. **End-to-End Flows**:
   - Complete schedule management flow:
     - Parsing a schedule from text
     - Optimizing the schedule
     - Modifying the schedule via chat

## Continuous Integration

These tests are designed to be run in a CI/CD pipeline. In mock mode, they don't require any external services, making them suitable for automated testing environments.

## Troubleshooting

If tests are failing, check the following:

1. If running in non-mock mode, ensure all services are running and accessible
2. Check that you have the correct environment variables set
3. Make sure all dependencies are installed
4. For authorization errors, ensure that any required API keys or credentials are set

## Extending the Tests

To add more tests:

1. For new unit tests, add test methods to the `TestEEP1App` class in `test_app.py`
2. For new integration tests, add test methods to the `TestEEP1Integration` class in `test_integration.py`
3. Follow the existing patterns for mocking and assertions 