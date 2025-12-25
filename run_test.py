import sys
import pytest
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath("src"))

# Run pytest
if __name__ == "__main__":
    sys.exit(pytest.main(["tests"]))
