#!/usr/bin/env python3
import unittest
import os
import sys

def run_basic_tests():
    """
    Run basic tests that don't have dependency issues.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    print("=== Running Basic UI Tests ===")
    
    # Initialize the test loader
    loader = unittest.TestLoader()
    
    # Create a test suite with just the basic tests
    suite = unittest.TestSuite()
    
    # Add the basic tests
    try:
        basic_tests = loader.discover(
            start_dir=os.path.dirname(os.path.abspath(__file__)),
            pattern='basic_test.py'
        )
        suite.addTests(basic_tests)
    except Exception as e:
        print(f"Error loading basic tests: {e}")
        return False
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return True if all tests pass
    return result.wasSuccessful()

if __name__ == "__main__":
    # Run basic tests
    success = run_basic_tests()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 