# test imports
import pytest
from pathlib import Path

# SUT import
import documenter

TEST_DIR = Path(__file__).parent / "test_dir"
TEST_LIBS = TEST_DIR / "libraries"


def test_importing_modules():
    """Confirm documenter can import modules."""
    my_directory = documenter.SourceDirectory(TEST_LIBS)
    my_source_files = [f for f in my_directory.source_files]
    print(my_source_files)
    my_modules = [f.name for f in my_directory.source_files]
    print(my_modules)
    assert "my_sub_library" in my_modules
