#!/usr/bin/env python3
import unittest
import os
import sys
import argparse

# Add parent directory to path to find the modules to test
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_tests(test_type="all", verbosity=2):
    """
    Run the specified type of tests.
    
    Args:
        test_type (str): Type of tests to run - "unit", "integration", or "all"
        verbosity (int): Verbosity level for test output
    
    Returns:
        bool: True if tests passed, False otherwise
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    if test_type == "unit" or test_type == "all":
        print("Running unit tests...")
        unit_tests = loader.discover(
            os.path.dirname(os.path.abspath(__file__)), 
            pattern='test_app.py'
        )
        suite.addTests(unit_tests)
    
    if test_type == "integration" or test_type == "all":
        print("Running integration tests...")
        integration_tests = loader.discover(
            os.path.dirname(os.path.abspath(__file__)), 
            pattern='test_integration.py'
        )
        suite.addTests(integration_tests)
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return True if tests passed
    return result.wasSuccessful()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests for IEP2")
    parser.add_argument(
        "--test-type", 
        choices=["unit", "integration", "all"], 
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbosity", 
        type=int, 
        choices=[0, 1, 2], 
        default=2,
        help="Verbosity level for test output"
    )
    parser.add_argument(
        "--mock-mode",
        action="store_true",
        help="Run tests in mock mode (default: True)",
        default=True
    )
    
    args = parser.parse_args()
    
    # Set environment variable for mock mode
    os.environ["TEST_MOCK_MODE"] = str(args.mock_mode)
    
    # Run tests
    success = run_tests(args.test_type, args.verbosity)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 