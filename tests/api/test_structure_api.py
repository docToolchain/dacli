from fastapi.testclient import TestClient
from mcp_server.main import app
from pathlib import Path

# Define the path to the fixtures directory
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

def test_get_structure_endpoint(monkeypatch): # Added monkeypatch
    """
    Tests the /get_structure endpoint to ensure it returns the document hierarchy.
    """
    # Set the environment variable for the test
    monkeypatch.setenv("MCP_DOC_ROOT", str(FIXTURE_DIR))

    # Use TestClient within a 'with' statement to ensure startup/shutdown events are run
    with TestClient(app) as client:
        response = client.get("/get_structure")

        assert response.status_code == 200
        data = response.json()

        # Expected structure from simple.adoc
        # == Level 1 Title
        # === Level 2 Title
        # == Another Level 1 Title
        assert isinstance(data, list)
        assert len(data) == 3 # Expecting 3 sections from simple.adoc and include_main.adoc

        # Check first top-level section (from simple.adoc)
        assert data[0]["title"] == "Level 1 Title"
        assert data[0]["level"] == 2
        assert len(data[0]["subsections"]) == 1
        assert data[0]["subsections"][0]["title"] == "Level 2 Title"
        assert data[0]["subsections"][0]["level"] == 3

        # Check second top-level section (from simple.adoc)
        assert data[1]["title"] == "Another Level 1 Title"
        assert data[1]["level"] == 2
        assert len(data[1]["subsections"]) == 0

        # Check third top-level section (from include_main.adoc)
        assert data[2]["title"] == "Main Document Section"
        assert data[2]["level"] == 2
        assert len(data[2]["subsections"]) == 1 # Corrected: Expect 1 subsection
        assert data[2]["subsections"][0]["title"] == "Included Section" # Added check for subsection
        assert data[2]["subsections"][0]["level"] == 3 # Added check for subsection level

