import unittest
import sys
import os

# Determine the project root (directory of this script)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def main():
    # Finds and runs all unit tests under `tests/`
    print(f"Starting test discovery in: {PROJECT_ROOT}")

    loader = unittest.TestLoader()

    # Search recursively under /tests for any file named test_*.py
    test_suite = loader.discover(start_dir=os.path.join(PROJECT_ROOT, 'tests'))

    runner = unittest.TextTestRunner(verbosity=2)

    # Run the discovered tests
    result = runner.run(test_suite)

    # Exit code reflects success/failure (for CI workflows, etc.)
    if not result.wasSuccessful():
        print("\n--- SOME TESTS FAILED ---")
        sys.exit(1)
    else:
        print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    main()
