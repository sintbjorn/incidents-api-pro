import os
import pytest
from fastapi.testclient import TestClient

# Use SQLite file for tests to persist across app init
os.environ["DATABASE_URL"] = "sqlite:///./test_incidents.db"

from app.entrypoints.api import app  # noqa

@pytest.fixture(scope="session")
def client():
    return TestClient(app)
