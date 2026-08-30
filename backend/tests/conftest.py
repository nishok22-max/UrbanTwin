"""Pytest fixtures for UrbanTwin backend testing."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import create_app
from app.services import graph_service


@pytest.fixture(scope="session")
def loaded_graph():
    """Ensure the T.Nagar graph is loaded in memory for tests."""
    return graph_service.load_graph()


@pytest.fixture(scope="session")
def intervention_catalog(loaded_graph):
    """Return the intervention catalog."""
    return graph_service.get_intervention_catalog()


@pytest.fixture(scope="session")
def client(loaded_graph):
    """FastAPI TestClient instance with graph loaded."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
