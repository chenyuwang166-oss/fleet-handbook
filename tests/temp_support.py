"""Temporary directories for tests: created in the system temp folder and removed afterwards."""
from contextlib import contextmanager
import tempfile


@contextmanager
def temporary_directory(prefix='fleet-'):
    with tempfile.TemporaryDirectory(prefix=prefix) as directory:
        yield directory
